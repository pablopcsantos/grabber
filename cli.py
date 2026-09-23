from __future__ import annotations

import argparse
from pathlib import Path

from core import (
    DiscoveryOptions,
    dedupe_preserve_order,
    discover_links,
    download_all,
    load_links_from_file,
    make_session,
    write_report,
)


def parse_args():
    p = argparse.ArgumentParser(description="Descobre e baixa arquivos públicos a partir de páginas web ou listas de URLs.")
    p.add_argument("--url", action="append", default=[], help="Página inicial. Pode repetir.")
    p.add_argument("--link-file", help="TXT com URLs diretas, uma por linha.")
    p.add_argument("--output", default="./downloads")
    p.add_argument("--mode", choices=["auto", "generic", "phocadownload", "api-json", "advanced"], default="auto")
    p.add_argument("--css-selector", default="")
    p.add_argument("--href-regex", default="")
    p.add_argument("--crawl-depth", type=int, default=0)
    p.add_argument("--max-pages", type=int, default=50)
    p.add_argument("--delay", type=float, default=0.7)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--retries", type=int, default=3)
    p.add_argument("--timeout", type=int, default=60)
    p.add_argument("--allow-external", action="store_true")
    p.add_argument("--ignore-robots", action="store_true")
    p.add_argument("--probe-ambiguous", action="store_true", help="Sonda links ambíguos com HEAD/Content-Type.")
    p.add_argument(
        "--scan-whole-page",
        action="store_true",
        help="No modo auto, desativa o foco na região principal e analisa menus/rodapés também.",
    )
    p.add_argument("--plugins-dir", default="./plugins", help="Pasta de adaptadores Python externos usados no modo auto.")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--links-out")
    return p.parse_args()


def log(msg: str):
    print(msg, flush=True)


def main() -> int:
    args = parse_args()
    if not args.url and not args.link_file:
        raise SystemExit("Informe --url ou --link-file.")

    session = make_session()
    links: list[str] = []
    if args.url:
        options = DiscoveryOptions(
            mode=args.mode,
            max_pages=max(1, args.max_pages),
            delay=max(0.0, args.delay),
            same_domain_only=not args.allow_external,
            respect_robots=not args.ignore_robots,
            crawl_depth=max(0, args.crawl_depth),
            css_selector=args.css_selector,
            href_regex=args.href_regex,
            probe_ambiguous=bool(args.probe_ambiguous),
            probe_timeout=min(max(2, args.timeout), 30),
            prefer_main_content=not args.scan_whole_page,
            plugin_dir=args.plugins_dir,
        )
        result = discover_links(session, args.url, options, log=log)
        links.extend(result.download_links)
        log(f"Modo detectado/usado: {result.detected_mode}")
        if result.plugins_loaded:
            log("Plugins carregados: " + ", ".join(result.plugins_loaded))
        if result.probes_performed:
            log(f"Sondagens realizadas: {result.probes_performed}")
        for warning in result.warnings:
            log(f"AVISO: {warning}")

    if args.link_file:
        links.extend(load_links_from_file(args.link_file))

    links = dedupe_preserve_order(links)
    log(f"Links únicos encontrados: {len(links)}")

    if args.links_out:
        Path(args.links_out).write_text("\n".join(links) + ("\n" if links else ""), encoding="utf-8")
        log(f"Lista salva em: {args.links_out}")

    if args.dry_run:
        print("\n".join(links))
        return 0

    if not links:
        log("Nenhum arquivo candidato encontrado.")
        return 2

    results = download_all(
        session, links, args.output, workers=args.workers, retries=args.retries,
        timeout=args.timeout, log=log,
    )
    report = write_report(results, args.output)
    ok = sum(r.status == "OK" for r in results)
    existed = sum(r.status == "JÁ EXISTIA" for r in results)
    failed = sum(r.status == "FALHOU" for r in results)
    cancelled = sum(r.status == "CANCELADO" for r in results)
    log(f"Concluído: {ok} novos, {existed} já existentes, {failed} falhas, {cancelled} cancelados.")
    log(f"Relatório: {report}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
