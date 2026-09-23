#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
eb_downloader.py
=================

Ferramenta portátil (Python puro + requests + beautifulsoup4) para:

  1. Varrer (web scrape) uma ou mais páginas de categoria do componente
     Joomla "Phocadownload" (padrão usado pelo site da 12ª RM e por outras
     páginas do Exército Brasileiro), seguindo a paginação automaticamente;
  2. Extrair todos os links de download (links no formato
     ".../category/180-xxx?download=ID:slug");
  3. Baixar todos os arquivos em paralelo (multi-thread), com retentativas,
     nome de arquivo correto (lido do cabeçalho Content-Disposition do
     servidor) e log/relatório final em CSV.

USO BÁSICO
----------
    python eb_downloader.py \
        --url "https://12rm.eb.mil.br/index.php/component/phocadownload/category/180-processo-seletivo-medico-obrigatorio-2025-2026" \
        --output ./downloads

Você pode passar várias categorias de uma vez:

    python eb_downloader.py --url URL1 --url URL2 --url URL3 --output ./downloads

Ou, se você já coletou os links manualmente (um por linha) em um arquivo .txt:

    python eb_downloader.py --link-file meus_links.txt --output ./downloads

Para apenas LISTAR os links encontrados, sem baixar nada (bom para checar
antes de baixar centenas de arquivos):

    python eb_downloader.py --url URL --dry-run

DEPENDÊNCIAS
------------
    pip install -r requirements.txt
    (ou simplesmente: pip install requests beautifulsoup4)

Compatível com Python 3.8+. Funciona em Windows, Linux e macOS.
"""

import argparse
import csv
import mimetypes
import os
import random
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse, parse_qs, unquote

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    sys.stderr.write(
        "\n[ERRO] Dependências não encontradas.\n"
        "Instale com:  pip install requests beautifulsoup4\n\n"
    )
    raise


# --------------------------------------------------------------------------- #
# Configurações gerais
# --------------------------------------------------------------------------- #

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

# Texto/atributos usados para reconhecer o link de "próxima página" em listas Joomla
NEXT_PAGE_HINTS = ("next", "próximo", "proximo", "seguinte", "»", "›")

# Mapeamento simples de content-type -> extensão, usado quando o servidor
# não informa o nome do arquivo via Content-Disposition.
EXT_BY_CONTENT_TYPE = {
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/zip": ".zip",
    "application/x-rar-compressed": ".rar",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# --------------------------------------------------------------------------- #
# Etapa 1: descoberta dos links (web scraping)
# --------------------------------------------------------------------------- #

def make_session():
    s = requests.Session()
    s.headers.update(DEFAULT_HEADERS)
    return s


def is_download_link(href):
    """Reconhece o padrão de link de download do Phocadownload."""
    if not href:
        return False
    return "download=" in href


def find_next_page_url(soup, base_url):
    """Tenta localizar o link de 'próxima página' na paginação do Joomla."""
    # 1) rel="next" é o sinal mais confiável
    a = soup.find("a", rel="next")
    if a and a.get("href"):
        return urljoin(base_url, a["href"])

    # 2) procura por texto/classe que indique "próxima"
    for a in soup.find_all("a", href=True):
        text = (a.get_text() or "").strip().lower()
        classes = " ".join(a.get("class", [])).lower()
        if any(hint in text for hint in NEXT_PAGE_HINTS) or "next" in classes:
            return urljoin(base_url, a["href"])

    return None


def discover_links(session, start_url, max_pages=50, delay=0.5):
    """
    Visita a página de categoria e segue a paginação, coletando todos os
    links de download (?download=...) encontrados. Retorna uma lista de
    URLs absolutas, sem duplicatas, preservando a ordem.
    """
    seen_links = []
    seen_set = set()
    visited_pages = set()

    url = start_url
    page_count = 0

    while url and url not in visited_pages and page_count < max_pages:
        visited_pages.add(url)
        page_count += 1
        log(f"Lendo página {page_count}: {url}")

        try:
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            log(f"  [AVISO] Falha ao abrir a página ({e}). Interrompendo paginação aqui.")
            break

        soup = BeautifulSoup(resp.text, "html.parser")

        new_in_page = 0
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if is_download_link(href):
                full = urljoin(url, href)
                if full not in seen_set:
                    seen_set.add(full)
                    seen_links.append(full)
                    new_in_page += 1

        log(f"  -> {new_in_page} novo(s) link(s) de download nesta página "
            f"(total acumulado: {len(seen_links)})")

        next_url = find_next_page_url(soup, url)
        if next_url == url:
            break
        url = next_url

        if url:
            time.sleep(delay)  # educado com o servidor

    return seen_links


def load_links_from_file(path):
    links = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                links.append(line)
    return links


# --------------------------------------------------------------------------- #
# Etapa 2: download dos arquivos
# --------------------------------------------------------------------------- #

def sanitize_filename(name):
    name = unquote(name)
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    name = name.strip().strip(".")
    return name[:180] if name else "arquivo_sem_nome"


def filename_from_response(resp, url):
    """Descobre o melhor nome de arquivo possível para a resposta HTTP."""
    cd = resp.headers.get("content-disposition", "")
    # filename*=UTF-8''nome.pdf   OU   filename="nome.pdf"
    match = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', cd, re.IGNORECASE)
    if match:
        return sanitize_filename(match.group(1))

    # fallback: usa o parâmetro ?download=ID:slug-do-titulo da própria URL
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    raw = qs.get("download", [""])[0]  # ex: "4651:nota-informativa-n-88..."
    slug = raw.split(":", 1)[1] if ":" in raw else raw
    slug = slug or "arquivo"

    ext = ""
    content_type = resp.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type in EXT_BY_CONTENT_TYPE:
        ext = EXT_BY_CONTENT_TYPE[content_type]
    else:
        guessed = mimetypes.guess_extension(content_type) if content_type else None
        ext = guessed or ".pdf"  # a grande maioria dos boletins é PDF

    return sanitize_filename(slug + ext)


def unique_path(directory, filename):
    """Evita sobrescrever arquivos com nomes repetidos."""
    base, ext = os.path.splitext(filename)
    candidate = filename
    i = 1
    while os.path.exists(os.path.join(directory, candidate)):
        candidate = f"{base} ({i}){ext}"
        i += 1
    return os.path.join(directory, candidate)


def download_one(session, url, outdir, retries=3, timeout=60, min_size_skip_check=True):
    """
    Baixa um único arquivo. Retorna um dict com o resultado, usado para o
    relatório final.
    """
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            with session.get(url, stream=True, timeout=timeout) as resp:
                resp.raise_for_status()
                filename = filename_from_response(resp, url)
                dest_path = os.path.join(outdir, filename)

                # Se já existe um arquivo com mesmo nome e tamanho, considera já baixado
                total_header = resp.headers.get("content-length")
                if (
                    min_size_skip_check
                    and os.path.exists(dest_path)
                    and total_header
                    and os.path.getsize(dest_path) == int(total_header)
                ):
                    return {
                        "url": url, "arquivo": filename, "status": "JÁ EXISTIA",
                        "tamanho_bytes": int(total_header), "erro": "",
                    }

                final_path = dest_path if not os.path.exists(dest_path) else unique_path(outdir, filename)
                tmp_path = final_path + ".part"

                size = 0
                with open(tmp_path, "wb") as fh:
                    for chunk in resp.iter_content(chunk_size=65536):
                        if chunk:
                            fh.write(chunk)
                            size += len(chunk)
                os.replace(tmp_path, final_path)

                return {
                    "url": url,
                    "arquivo": os.path.basename(final_path),
                    "status": "OK",
                    "tamanho_bytes": size,
                    "erro": "",
                }

        except requests.RequestException as e:
            last_error = str(e)
            if attempt < retries:
                time.sleep(1.5 * attempt)  # backoff simples

    return {
        "url": url, "arquivo": "", "status": "FALHOU",
        "tamanho_bytes": 0, "erro": last_error or "erro desconhecido",
    }


def download_all(session, links, outdir, workers=6, retries=3, timeout=60):
    os.makedirs(outdir, exist_ok=True)
    results = []

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {}
        for url in links:
            # pequeno atraso aleatório no envio para não disparar tudo no mesmo instante
            time.sleep(random.uniform(0, 0.15))
            futures[pool.submit(download_one, session, url, outdir, retries, timeout)] = url

        done = 0
        total = len(futures)
        for future in as_completed(futures):
            result = future.result()
            done += 1
            tag = "OK" if result["status"] == "OK" else result["status"]
            log(f"[{done}/{total}] {tag:10s} {result['arquivo'] or result['url']}")
            results.append(result)

    return results


def write_report(results, outdir):
    report_path = os.path.join(outdir, "_relatorio_download.csv")
    with open(report_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["url", "arquivo", "status", "tamanho_bytes", "erro"])
        writer.writeheader()
        writer.writerows(results)
    return report_path


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def parse_args():
    p = argparse.ArgumentParser(
        description="Baixa em massa arquivos de páginas de categoria Joomla/Phocadownload."
    )
    p.add_argument("--url", action="append", default=[],
                    help="URL da página de categoria a varrer. Pode repetir --url várias vezes.")
    p.add_argument("--link-file", default=None,
                    help="Arquivo .txt com links de download já coletados, um por linha.")
    p.add_argument("--output", default="./downloads", help="Pasta onde salvar os arquivos.")
    p.add_argument("--workers", type=int, default=6, help="Downloads simultâneos (padrão: 6).")
    p.add_argument("--retries", type=int, default=3, help="Tentativas por arquivo (padrão: 3).")
    p.add_argument("--timeout", type=int, default=60, help="Timeout por requisição, em segundos.")
    p.add_argument("--max-pages", type=int, default=50,
                    help="Máximo de páginas de listagem a seguir por categoria (paginação).")
    p.add_argument("--delay", type=float, default=0.5,
                    help="Pausa (s) entre o carregamento de páginas de listagem.")
    p.add_argument("--dry-run", action="store_true",
                    help="Apenas lista os links encontrados, sem baixar nada.")
    p.add_argument("--links-out", default=None,
                    help="Se informado, salva a lista de links descobertos neste arquivo .txt.")
    return p.parse_args()


def main():
    args = parse_args()

    if not args.url and not args.link_file:
        sys.exit("Informe ao menos um --url (página de categoria) ou --link-file (lista de links).")

    session = make_session()
    all_links = []

    for cat_url in args.url:
        links = discover_links(session, cat_url, max_pages=args.max_pages, delay=args.delay)
        all_links.extend(links)

    if args.link_file:
        all_links.extend(load_links_from_file(args.link_file))

    # remove duplicatas mantendo a ordem
    seen = set()
    unique_links = []
    for link in all_links:
        if link not in seen:
            seen.add(link)
            unique_links.append(link)

    log(f"\nTotal de links de download únicos encontrados: {len(unique_links)}\n")

    if args.links_out:
        with open(args.links_out, "w", encoding="utf-8") as f:
            f.write("\n".join(unique_links))
        log(f"Lista de links salva em: {args.links_out}")

    if args.dry_run:
        for link in unique_links:
            print(link)
        return

    if not unique_links:
        log("Nenhum link encontrado. Verifique a URL informada ou se o site bloqueou o acesso.")
        return

    results = download_all(
        session, unique_links, args.output,
        workers=args.workers, retries=args.retries, timeout=args.timeout,
    )

    report_path = write_report(results, args.output)

    ok = sum(1 for r in results if r["status"] == "OK")
    existed = sum(1 for r in results if r["status"] == "JÁ EXISTIA")
    failed = sum(1 for r in results if r["status"] == "FALHOU")

    log("\n========== RESUMO ==========")
    log(f"Sucesso .........: {ok}")
    log(f"Já existiam ......: {existed}")
    log(f"Falharam .........: {failed}")
    log(f"Relatório salvo em: {report_path}")
    if failed:
        log("Dica: rode o comando novamente — arquivos já baixados são pulados automaticamente,"
            " e só os que falharam serão tentados de novo (use o mesmo --output).")


if __name__ == "__main__":
    main()
