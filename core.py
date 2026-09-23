from __future__ import annotations

import csv
import mimetypes
import os
import random
import re
import threading
import time
from collections import deque
from concurrent.futures import CancelledError, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import parse_qs, unquote, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from adapters import ExternalAdapter, load_external_adapters


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

NEXT_PAGE_HINTS = (
    "next", "próximo", "proximo", "seguinte", "avançar", "avancar", "mais", "»", "›",
)

DOWNLOAD_TEXT_HINTS = (
    "download", "baixar", "arquivo", "documento", "anexo", "exportar", "salvar",
)

DOWNLOAD_QUERY_HINTS = {
    "download", "file", "arquivo", "attachment", "document", "doc", "media",
}

# Alguns portais não apontam diretamente para o arquivo. Em vez disso, o href
# abre um visualizador HTML e inclui a URL real do documento em um parâmetro.
# Ex.: viewer/index.html?file=https://site/documento.pdf
EMBEDDED_FILE_QUERY_HINTS = {
    "file", "url", "src", "document", "doc", "media", "target", "download",
}

KNOWN_FILE_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
    ".txt", ".csv", ".json", ".xml", ".rtf", ".odt", ".ods", ".odp",
    ".mp3", ".wav", ".ogg", ".mp4", ".mkv", ".avi", ".mov", ".webm",
    ".epub", ".mobi", ".apk", ".exe", ".msi",
}

PAGE_EXTENSIONS = {".html", ".htm", ".php", ".asp", ".aspx", ".jsp", ".jspx"}

EXT_BY_CONTENT_TYPE = {
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/zip": ".zip",
    "application/x-rar-compressed": ".rar",
    "application/x-7z-compressed": ".7z",
    "application/octet-stream": ".bin",
    "text/plain": ".txt",
    "text/csv": ".csv",
    "application/json": ".json",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
    "audio/mpeg": ".mp3",
    "video/mp4": ".mp4",
}


LogFn = Callable[[str], None]
ProgressFn = Callable[[int, int, "DownloadResult | None"], None]


def noop_log(_: str) -> None:
    return


def noop_progress(_: int, __: int, ___: "DownloadResult | None") -> None:
    return


@dataclass
class DiscoveryOptions:
    mode: str = "auto"  # auto | generic | phocadownload | advanced
    max_pages: int = 50
    delay: float = 0.7
    same_domain_only: bool = True
    respect_robots: bool = True
    crawl_depth: int = 0
    css_selector: str = ""
    href_regex: str = ""
    allow_query_downloads: bool = True
    probe_ambiguous: bool = False
    probe_timeout: int = 8
    plugin_dir: str = ""


@dataclass
class DiscoveryResult:
    start_urls: list[str]
    download_links: list[str] = field(default_factory=list)
    visited_pages: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    detected_mode: str = ""
    cancelled: bool = False
    probes_performed: int = 0
    plugins_loaded: list[str] = field(default_factory=list)
    robots_blocked: list[str] = field(default_factory=list)


@dataclass
class DownloadResult:
    url: str
    arquivo: str
    status: str
    tamanho_bytes: int = 0
    erro: str = ""


class RobotsCache:
    def __init__(self, session: requests.Session, log: LogFn = noop_log):
        self.session = session
        self.log = log
        self._cache: dict[str, RobotFileParser | None] = {}

    def allowed(self, url: str, user_agent: str = "*") -> bool:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return True
        root = f"{parsed.scheme}://{parsed.netloc}"
        if root not in self._cache:
            robots_url = urljoin(root, "/robots.txt")
            rp = RobotFileParser()
            rp.set_url(robots_url)
            try:
                resp = self.session.get(robots_url, timeout=12)
                if resp.status_code >= 400:
                    self._cache[root] = None
                else:
                    rp.parse(resp.text.splitlines())
                    self._cache[root] = rp
            except requests.RequestException:
                self._cache[root] = None
        rp = self._cache[root]
        return True if rp is None else rp.can_fetch(user_agent, url)


def make_session(headers: dict[str, str] | None = None) -> requests.Session:
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    if headers:
        session.headers.update(headers)
    return session


def load_links_from_file(path: str | os.PathLike[str]) -> list[str]:
    links: list[str] = []
    with open(path, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                links.append(line)
    return dedupe_preserve_order(links)


def dedupe_preserve_order(items: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def same_site(a: str, b: str) -> bool:
    pa, pb = urlparse(a), urlparse(b)
    return (
        pa.scheme in {"http", "https"}
        and pb.scheme in {"http", "https"}
        and pa.netloc.lower() == pb.netloc.lower()
    )


def normalize_url(base_url: str, href: str) -> str | None:
    href = (href or "").strip()
    if not href or href.startswith(("javascript:", "mailto:", "tel:", "data:")):
        return None
    full = urljoin(base_url, href)
    parsed = urlparse(full)
    if parsed.scheme not in {"http", "https"}:
        return None
    return full


def looks_like_direct_file(url: str) -> bool:
    parsed = urlparse(url)
    ext = Path(unquote(parsed.path)).suffix.lower()
    return ext in KNOWN_FILE_EXTENSIONS


def has_download_query(url: str) -> bool:
    query = parse_qs(urlparse(url).query)
    return any(key.lower() in DOWNLOAD_QUERY_HINTS for key in query)


def unwrap_embedded_file_url(url: str) -> str:
    """Extrai a URL real quando um visualizador HTML a recebe pela query string."""
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    for key, values in query.items():
        if key.lower() not in EMBEDDED_FILE_QUERY_HINTS:
            continue
        for raw in values:
            raw = unquote((raw or "").strip())
            if not raw:
                continue
            nested = normalize_url(url, raw)
            if nested and looks_like_direct_file(nested):
                return nested
    return url


def is_phocadownload_link(url: str) -> bool:
    return "download=" in url.lower()


def anchor_is_download_candidate(anchor, full_url: str, options: DiscoveryOptions) -> bool:
    if anchor.has_attr("download"):
        return True
    if looks_like_direct_file(full_url):
        return True
    if options.allow_query_downloads and has_download_query(full_url):
        return True
    return False


def find_next_page_url(soup: BeautifulSoup, base_url: str) -> str | None:
    a = soup.find("a", rel=lambda value: value and "next" in value)
    if a and a.get("href"):
        return normalize_url(base_url, a["href"])

    for a in soup.find_all("a", href=True):
        text = (a.get_text(" ", strip=True) or "").lower()
        classes = " ".join(a.get("class", [])).lower()
        aria = (a.get("aria-label") or "").lower()
        title = (a.get("title") or "").lower()
        combined = " ".join((text, classes, aria, title))
        if any(hint in combined for hint in NEXT_PAGE_HINTS):
            return normalize_url(base_url, a["href"])
    return None


def _compile_href_regex(pattern: str) -> re.Pattern[str] | None:
    pattern = pattern.strip()
    return re.compile(pattern, re.IGNORECASE) if pattern else None


def _anchors_for_mode(soup: BeautifulSoup, options: DiscoveryOptions):
    if options.mode == "advanced" and options.css_selector.strip():
        anchors = []
        for node in soup.select(options.css_selector.strip()):
            if getattr(node, "name", None) == "a" and node.get("href"):
                anchors.append(node)
            else:
                anchors.extend(node.find_all("a", href=True))
        return anchors
    return soup.find_all("a", href=True)


def _anchor_text(anchor) -> str:
    return " ".join(
        filter(
            None,
            [
                (anchor.get_text(" ", strip=True) or "").lower(),
                (anchor.get("title") or "").lower(),
                (anchor.get("aria-label") or "").lower(),
            ],
        )
    )


def should_probe_ambiguous(anchor, url: str) -> bool:
    parsed = urlparse(url)
    ext = Path(unquote(parsed.path)).suffix.lower()
    if ext in PAGE_EXTENSIONS:
        return False
    text = _anchor_text(anchor)
    return any(hint in text for hint in DOWNLOAD_TEXT_HINTS)


def _response_looks_like_file(resp: requests.Response) -> tuple[bool, str]:
    cd = resp.headers.get("content-disposition", "")
    if "attachment" in cd.lower() or "filename=" in cd.lower() or "filename*=" in cd.lower():
        return True, "Content-Disposition indica anexo"

    content_type = resp.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if not content_type:
        return False, "sem Content-Type"
    if content_type in {"text/html", "application/xhtml+xml"}:
        return False, content_type
    if content_type in EXT_BY_CONTENT_TYPE:
        return True, content_type
    if content_type.startswith(("image/", "audio/", "video/")):
        return True, content_type
    if content_type.startswith("application/") and content_type not in {
        "application/xhtml+xml", "application/xml",
    }:
        return True, content_type
    return False, content_type


def probe_link_is_file(
    session: requests.Session,
    url: str,
    timeout: int = 8,
) -> tuple[bool, str]:
    """Sonda um link ambíguo sem baixar seu corpo quando possível."""
    try:
        resp = session.head(url, allow_redirects=True, timeout=timeout)
        if resp.status_code not in {405, 501}:
            resp.raise_for_status()
            return _response_looks_like_file(resp)
    except requests.RequestException as exc:
        # Alguns servidores rejeitam HEAD mas aceitam GET; tentamos uma leitura sem corpo.
        head_error = friendly_request_error(exc)
    else:
        head_error = "HEAD não suportado"

    try:
        with session.get(url, stream=True, allow_redirects=True, timeout=timeout) as resp:
            resp.raise_for_status()
            ok, reason = _response_looks_like_file(resp)
            return ok, reason
    except requests.RequestException as exc:
        return False, f"{head_error}; GET: {friendly_request_error(exc)}"


def friendly_request_error(exc: Exception) -> str:
    if isinstance(exc, requests.Timeout):
        return "tempo limite excedido"
    if isinstance(exc, requests.ConnectionError):
        return "falha de conexão com o servidor"
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        code = exc.response.status_code
        messages = {
            400: "requisição rejeitada pelo servidor (HTTP 400)",
            401: "autenticação necessária (HTTP 401)",
            403: "acesso negado pelo servidor (HTTP 403)",
            404: "recurso não encontrado (HTTP 404)",
            429: "muitas requisições; o servidor pediu redução do ritmo (HTTP 429)",
            500: "erro interno do servidor (HTTP 500)",
            502: "gateway inválido (HTTP 502)",
            503: "serviço indisponível (HTTP 503)",
            504: "tempo limite do gateway (HTTP 504)",
        }
        return messages.get(code, f"erro HTTP {code}")
    return str(exc) or exc.__class__.__name__


def _plugin_matches(
    adapters: list[ExternalAdapter],
    anchor,
    full_url: str,
    page_url: str,
    warnings: list[str],
    log: LogFn,
) -> str | None:
    for adapter in adapters:
        try:
            if adapter.matches(anchor, full_url, page_url):
                return adapter.name
        except Exception as exc:
            msg = f"Plugin {adapter.name} falhou ao analisar um link: {exc}"
            if msg not in warnings:
                warnings.append(msg)
                log(f"[AVISO] {msg}")
    return None


def discover_links(
    session: requests.Session,
    start_urls: list[str],
    options: DiscoveryOptions | None = None,
    log: LogFn = noop_log,
    cancel_event: threading.Event | None = None,
) -> DiscoveryResult:
    options = options or DiscoveryOptions()
    result = DiscoveryResult(start_urls=start_urls)
    robots = RobotsCache(session, log)
    href_re = _compile_href_regex(options.href_regex)
    adapters, plugin_warnings = load_external_adapters(options.plugin_dir, log=log)
    result.warnings.extend(plugin_warnings)
    result.plugins_loaded = [a.name for a in adapters]

    queue: deque[tuple[str, int, bool]] = deque((u, 0, True) for u in start_urls)
    queued: set[str] = set(start_urls)
    visited: set[str] = set()
    downloads: list[str] = []
    download_seen: set[str] = set()
    detected: set[str] = set()
    probe_cache: dict[str, bool] = {}

    while queue and len(visited) < options.max_pages:
        if cancel_event and cancel_event.is_set():
            result.cancelled = True
            result.warnings.append("Coleta cancelada pelo usuário.")
            break

        url, depth, _is_seed_or_pagination = queue.popleft()
        if url in visited:
            continue
        visited.add(url)
        result.visited_pages.append(url)

        if options.respect_robots and not robots.allowed(url):
            msg = f"robots.txt não permite coletar: {url}"
            result.warnings.append(msg)
            result.robots_blocked.append(url)
            log(f"[IGNORADO] {msg}")
            continue

        log(f"Lendo página {len(visited)}/{options.max_pages}: {url}")
        try:
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as exc:
            msg = f"Falha ao abrir {url}: {friendly_request_error(exc)}"
            result.warnings.append(msg)
            log(f"[AVISO] {msg}")
            continue

        content_type = resp.headers.get("content-type", "").lower()
        if "html" not in content_type and looks_like_direct_file(resp.url):
            if resp.url not in download_seen:
                downloads.append(resp.url)
                download_seen.add(resp.url)
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        anchors = _anchors_for_mode(soup, options)
        new_count = 0

        for anchor in anchors:
            if cancel_event and cancel_event.is_set():
                result.cancelled = True
                break

            raw_full = normalize_url(resp.url, anchor.get("href", ""))
            if not raw_full:
                continue
            full = unwrap_embedded_file_url(raw_full)
            if full != raw_full:
                detected.add("embedded-file")
            if options.same_domain_only and not any(same_site(seed, full) for seed in start_urls):
                continue

            candidate = False
            if options.mode == "phocadownload":
                candidate = is_phocadownload_link(full)
                if candidate:
                    detected.add("phocadownload")
            elif options.mode == "generic":
                candidate = anchor_is_download_candidate(anchor, full, options)
                if candidate:
                    detected.add("generic")
            elif options.mode == "advanced":
                candidate = bool(href_re.search(full)) if href_re else anchor_is_download_candidate(anchor, full, options)
                if candidate:
                    detected.add("advanced")
            else:  # auto
                if is_phocadownload_link(full):
                    candidate = True
                    detected.add("phocadownload")
                elif anchor_is_download_candidate(anchor, full, options):
                    candidate = True
                    detected.add("generic")
                else:
                    plugin_name = _plugin_matches(adapters, anchor, full, resp.url, result.warnings, log)
                    if plugin_name:
                        candidate = True
                        detected.add(f"plugin:{plugin_name}")

            if href_re and options.mode != "advanced":
                candidate = candidate and bool(href_re.search(full))

            if (
                not candidate
                and options.probe_ambiguous
                and should_probe_ambiguous(anchor, full)
            ):
                if full not in probe_cache:
                    result.probes_performed += 1
                    ok, reason = probe_link_is_file(session, full, timeout=max(2, options.probe_timeout))
                    probe_cache[full] = ok
                    log(f"  [SONDAGEM] {'arquivo' if ok else 'não arquivo'}: {full} ({reason})")
                candidate = probe_cache[full]
                if candidate:
                    detected.add("head-probe")

            if candidate and full not in download_seen:
                download_seen.add(full)
                downloads.append(full)
                new_count += 1
                continue

            if options.crawl_depth > depth and not looks_like_direct_file(full):
                if full not in queued and full not in visited:
                    queued.add(full)
                    queue.append((full, depth + 1, False))

        log(f"  -> {new_count} novo(s) arquivo(s) candidato(s); total: {len(downloads)}")

        if result.cancelled:
            break

        next_url = find_next_page_url(soup, resp.url)
        if not next_url and options.mode == "auto" and adapters:
            for adapter in adapters:
                try:
                    raw = adapter.next_page(soup, resp.url)
                    if raw:
                        next_url = normalize_url(resp.url, raw)
                        if next_url:
                            detected.add(f"plugin:{adapter.name}")
                            break
                except Exception as exc:
                    msg = f"Plugin {adapter.name} falhou ao localizar paginação: {exc}"
                    if msg not in result.warnings:
                        result.warnings.append(msg)

        if next_url and next_url not in queued and next_url not in visited:
            if not options.same_domain_only or any(same_site(seed, next_url) for seed in start_urls):
                queued.add(next_url)
                queue.appendleft((next_url, depth, True))

        if options.delay > 0:
            if cancel_event:
                if cancel_event.wait(options.delay):
                    result.cancelled = True
                    result.warnings.append("Coleta cancelada pelo usuário.")
                    break
            else:
                time.sleep(options.delay)

    if queue and len(visited) >= options.max_pages:
        result.warnings.append(f"Coleta interrompida no limite de {options.max_pages} páginas.")

    result.download_links = downloads
    if options.mode == "auto":
        result.detected_mode = "+".join(sorted(detected)) or "nenhum padrão reconhecido"
    else:
        result.detected_mode = options.mode
    return result


def sanitize_filename(name: str) -> str:
    name = unquote(name or "")
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    name = re.sub(r"\s+", " ", name).strip().strip(".")
    return name[:180] if name else "arquivo_sem_nome"


def filename_hint_from_url(url: str, ordinal: int | None = None) -> str:
    parsed = urlparse(url)
    path_name = Path(unquote(parsed.path)).name
    if path_name and Path(path_name).suffix.lower() not in PAGE_EXTENSIONS:
        return sanitize_filename(path_name)

    query = parse_qs(parsed.query)
    for key in DOWNLOAD_QUERY_HINTS:
        values = query.get(key)
        if values:
            raw = values[0].split(":", 1)[-1]
            if raw:
                return sanitize_filename(raw)

    if path_name and path_name not in {"/", "."}:
        return sanitize_filename(path_name)
    return f"arquivo_{ordinal:04d}" if ordinal is not None else "arquivo"


def filename_from_response(resp: requests.Response, url: str, ordinal: int | None = None) -> str:
    cd = resp.headers.get("content-disposition", "")
    match = re.search(r"filename\*?=(?:UTF-8''|utf-8'')?\"?([^\";]+)\"?", cd, re.IGNORECASE)
    if match:
        return sanitize_filename(match.group(1))

    parsed = urlparse(url)
    path_name = Path(unquote(parsed.path)).name
    if path_name and Path(path_name).suffix:
        return sanitize_filename(path_name)

    query = parse_qs(parsed.query)
    raw = ""
    for key in DOWNLOAD_QUERY_HINTS:
        values = query.get(key)
        if values:
            raw = values[0]
            break
    if raw:
        raw = raw.split(":", 1)[-1]

    content_type = resp.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    ext = EXT_BY_CONTENT_TYPE.get(content_type)
    if not ext and content_type:
        ext = mimetypes.guess_extension(content_type)
    ext = ext or ".bin"

    stem = raw or (f"arquivo_{ordinal:04d}" if ordinal is not None else "arquivo")
    if Path(stem).suffix:
        return sanitize_filename(stem)
    return sanitize_filename(stem + ext)


def unique_path(directory: str | os.PathLike[str], filename: str) -> Path:
    directory = Path(directory)
    base = Path(filename).stem
    ext = Path(filename).suffix
    candidate = directory / filename
    i = 1
    while candidate.exists():
        candidate = directory / f"{base} ({i}){ext}"
        i += 1
    return candidate


def download_one(
    session: requests.Session,
    url: str,
    outdir: str | os.PathLike[str],
    ordinal: int,
    retries: int = 3,
    timeout: int = 60,
    cancel_event: threading.Event | None = None,
) -> DownloadResult:
    last_error = ""
    outdir = Path(outdir)
    tmp_path: Path | None = None

    if cancel_event and cancel_event.is_set():
        return DownloadResult(url, "", "CANCELADO", 0, "cancelado pelo usuário")

    for attempt in range(1, retries + 1):
        if cancel_event and cancel_event.is_set():
            return DownloadResult(url, "", "CANCELADO", 0, "cancelado pelo usuário")
        try:
            with session.get(url, stream=True, timeout=timeout, allow_redirects=True) as resp:
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                if content_type.startswith("text/html") and not looks_like_direct_file(resp.url):
                    raise requests.RequestException(
                        "o servidor retornou HTML em vez de um arquivo; pode ser uma página intermediária, login ou bloqueio"
                    )

                filename = filename_from_response(resp, resp.url, ordinal)
                dest_path = outdir / filename
                total_header = resp.headers.get("content-length")

                if dest_path.exists() and total_header:
                    try:
                        if dest_path.stat().st_size == int(total_header):
                            return DownloadResult(url, filename, "JÁ EXISTIA", int(total_header), "")
                    except ValueError:
                        pass

                final_path = dest_path if not dest_path.exists() else unique_path(outdir, filename)
                tmp_path = Path(str(final_path) + ".part")
                size = 0
                with tmp_path.open("wb") as fh:
                    for chunk in resp.iter_content(chunk_size=65536):
                        if cancel_event and cancel_event.is_set():
                            raise InterruptedError("cancelado pelo usuário")
                        if chunk:
                            fh.write(chunk)
                            size += len(chunk)
                os.replace(tmp_path, final_path)
                tmp_path = None
                return DownloadResult(url, final_path.name, "OK", size, "")
        except InterruptedError:
            if tmp_path:
                tmp_path.unlink(missing_ok=True)
            return DownloadResult(url, "", "CANCELADO", 0, "cancelado pelo usuário")
        except requests.RequestException as exc:
            if tmp_path:
                tmp_path.unlink(missing_ok=True)
            last_error = friendly_request_error(exc)
            if attempt < retries and not (cancel_event and cancel_event.is_set()):
                if cancel_event:
                    if cancel_event.wait(1.5 * attempt):
                        return DownloadResult(url, "", "CANCELADO", 0, "cancelado pelo usuário")
                else:
                    time.sleep(1.5 * attempt)
        except OSError as exc:
            if tmp_path:
                tmp_path.unlink(missing_ok=True)
            last_error = str(exc)
            break

    return DownloadResult(url, "", "FALHOU", 0, last_error or "erro desconhecido")


def download_all(
    session: requests.Session,
    links: list[str],
    outdir: str | os.PathLike[str],
    workers: int = 4,
    retries: int = 3,
    timeout: int = 60,
    log: LogFn = noop_log,
    cancel_event: threading.Event | None = None,
    progress: ProgressFn = noop_progress,
) -> list[DownloadResult]:
    Path(outdir).mkdir(parents=True, exist_ok=True)
    total = len(links)
    if total == 0:
        return []

    results_by_ordinal: dict[int, DownloadResult] = {}
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {}
        for ordinal, url in enumerate(links, start=1):
            if cancel_event and cancel_event.is_set():
                results_by_ordinal[ordinal] = DownloadResult(url, "", "CANCELADO", 0, "cancelado pelo usuário")
                continue
            time.sleep(random.uniform(0, 0.12))
            future = pool.submit(
                download_one,
                session,
                url,
                outdir,
                ordinal,
                retries,
                timeout,
                cancel_event,
            )
            futures[future] = (ordinal, url)

        completed = 0
        for ordinal in sorted(results_by_ordinal):
            completed += 1
            progress(completed, total, results_by_ordinal[ordinal])

        for future in as_completed(futures):
            ordinal, url = futures[future]
            try:
                result = future.result()
            except CancelledError:
                result = DownloadResult(url, "", "CANCELADO", 0, "cancelado pelo usuário")
            except Exception as exc:
                result = DownloadResult(url, "", "FALHOU", 0, str(exc))
            results_by_ordinal[ordinal] = result
            completed += 1
            label = result.arquivo or result.url
            log(f"[{completed}/{total}] {result.status:10s} {label}")
            progress(completed, total, result)

            if cancel_event and cancel_event.is_set():
                for pending in futures:
                    if not pending.done():
                        pending.cancel()

    # Garante um registro por URL, inclusive se alguma Future foi cancelada antes de iniciar.
    for ordinal, url in enumerate(links, start=1):
        if ordinal not in results_by_ordinal:
            results_by_ordinal[ordinal] = DownloadResult(url, "", "CANCELADO", 0, "cancelado pelo usuário")

    return [results_by_ordinal[i] for i in range(1, total + 1)]


def write_report(results: list[DownloadResult], outdir: str | os.PathLike[str]) -> Path:
    report_path = Path(outdir) / "_relatorio_download.csv"
    with report_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["url", "arquivo", "status", "tamanho_bytes", "erro"])
        writer.writeheader()
        for item in results:
            writer.writerow({
                "url": item.url,
                "arquivo": item.arquivo,
                "status": item.status,
                "tamanho_bytes": item.tamanho_bytes,
                "erro": item.erro,
            })
    return report_path
