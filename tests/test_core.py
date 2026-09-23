from __future__ import annotations

import tempfile
import threading
import unittest
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from core import (
    DiscoveryOptions,
    discover_links,
    download_all,
    make_session,
    same_site,
    write_report,
)


class QuietHandler(SimpleHTTPRequestHandler):
    flaky_count = 0

    def log_message(self, format, *args):
        pass

    def do_HEAD(self):
        if urlparse(self.path).path == "/ambiguous":
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Length", "7")
            self.end_headers()
            return
        super().do_HEAD()

    def do_GET(self):
        if urlparse(self.path).path == "/flaky.html":
            type(self).flaky_count += 1
            if type(self).flaky_count <= 2:
                body = b"temporarily unavailable"
                self.send_response(503)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
        if urlparse(self.path).path == "/robots.txt":
            body = b"User-agent: *\nDisallow: /blocked.html\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if urlparse(self.path).path == "/ambiguous":
            body = b"pdfdata"
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()


class CoreIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.root = root
        (root / "files").mkdir()
        (root / "nested").mkdir()
        (root / "plugins").mkdir()
        (root / "files" / "a.pdf").write_bytes(b"pdfdata")
        (root / "files" / "b.zip").write_bytes(b"zipdata")
        (root / "files" / "c.docx").write_bytes(b"docdata")
        (root / "index.html").write_text(
            '<a href="files/a.pdf">A</a><a href="page2.html" rel="next">Next</a><a href="nested/list.html">Nested</a>',
            encoding="utf-8",
        )
        (root / "page2.html").write_text('<a href="files/b.zip">B</a>', encoding="utf-8")
        (root / "nested" / "list.html").write_text('<div class="docs"><a href="../files/c.docx">C</a></div>', encoding="utf-8")
        (root / "phoca.html").write_text('<a href="index.php?download=42:arquivo">Phoca</a>', encoding="utf-8")
        (root / "advanced.html").write_text('<div id="docs"><a href="files/a.pdf?token=1">A</a></div><a href="files/b.zip">B</a>', encoding="utf-8")
        (root / "ambiguous.html").write_text('<a href="ambiguous?id=123">Baixar documento</a>', encoding="utf-8")
        (root / "plugin.html").write_text('<a href="asset.special">Arquivo especial</a>', encoding="utf-8")
        (root / "wrapped.html").write_text(
            '<a href="viewer/index.html?file=%2Ffiles%2Fa.pdf">Abrir PDF no visualizador</a>',
            encoding="utf-8",
        )
        (root / "blocked.html").write_text('<a href="files/a.pdf">PDF bloqueado pelo robots</a>', encoding="utf-8")
        (root / "hub.html").write_text('<a href="edit.html">Edital</a>', encoding="utf-8")
        (root / "edit.html").write_text('<a href="files/a.pdf">Baixar edital</a>', encoding="utf-8")
        (root / "flaky.html").write_text('<a href="files/a.pdf">PDF</a>', encoding="utf-8")
        (root / "api1.json").write_text(
            '{"results":[{"file":"files/a.pdf"},{"nested":{"download":"files/b.zip"}}],"next":"api2.json"}',
            encoding="utf-8",
        )
        (root / "api2.json").write_text(
            '{"items":[{"url":"files/c.docx"}]}',
            encoding="utf-8",
        )
        (root / "focused.html").write_text(
            '<header><a href="files/b.zip">Arquivo global do menu</a></header>'
            '<main><h1>Processo seletivo</h1><a href="files/a.pdf">Edital relacionado</a></main>'
            '<footer><a href="files/c.docx">Arquivo global do rodapé</a></footer>',
            encoding="utf-8",
        )
        (root / "plugins" / "special.py").write_text(
            'ADAPTER_NAME = "SpecialTest"\n\n'
            'def match_link(anchor, url, page_url):\n'
            '    return url.endswith("asset.special")\n',
            encoding="utf-8",
        )

        handler = partial(QuietHandler, directory=root)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.session = make_session()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}/{path}"

    def test_same_site_treats_www_as_same_host(self):
        self.assertTrue(
            same_site(
                "https://iades.com.br/inscricao/processo",
                "https://www.iades.com.br/inscricao/upload/arquivo.pdf",
            )
        )
        self.assertTrue(
            same_site(
                "https://www.exemplo.org/a",
                "https://exemplo.org/b",
            )
        )
        self.assertFalse(
            same_site(
                "https://exemplo.org/a",
                "https://arquivos.exemplo.org/b",
            )
        )

    def test_auto_primary_content_focus_avoids_global_links(self):
        focused = discover_links(
            self.session,
            [self.url("focused.html")],
            DiscoveryOptions(mode="auto", respect_robots=False, delay=0),
        )
        self.assertEqual(len(focused.download_links), 1)
        self.assertTrue(focused.download_links[0].endswith("/files/a.pdf"))
        self.assertIn("main-content", focused.detected_mode)

        whole_page = discover_links(
            self.session,
            [self.url("focused.html")],
            DiscoveryOptions(
                mode="auto",
                respect_robots=False,
                delay=0,
                prefer_main_content=False,
            ),
        )
        self.assertEqual(len(whole_page.download_links), 3)

    def test_generic_links_and_pagination(self):
        result = discover_links(
            self.session,
            [self.url("index.html")],
            DiscoveryOptions(mode="generic", respect_robots=False, delay=0, max_pages=10),
        )
        self.assertTrue(any(x.endswith("/files/a.pdf") for x in result.download_links))
        self.assertTrue(any(x.endswith("/files/b.zip") for x in result.download_links))
        self.assertEqual(len(result.visited_pages), 2)

    def test_auto_follows_likely_document_section_at_depth_zero(self):
        result = discover_links(
            self.session,
            [self.url("hub.html")],
            DiscoveryOptions(mode="auto", respect_robots=False, delay=0, crawl_depth=0, max_pages=10),
        )
        self.assertTrue(any(x.endswith("/files/a.pdf") for x in result.download_links))
        self.assertTrue(any(x.endswith("/edit.html") for x in result.visited_pages))
        self.assertIn("smart-section", result.detected_mode)

    def test_page_fetch_retries_transient_503(self):
        QuietHandler.flaky_count = 0
        result = discover_links(
            self.session,
            [self.url("flaky.html")],
            DiscoveryOptions(
                mode="generic",
                respect_robots=False,
                delay=0,
                page_retries=2,
                page_timeout=5,
            ),
        )
        self.assertEqual(QuietHandler.flaky_count, 3)
        self.assertTrue(any(x.endswith("/files/a.pdf") for x in result.download_links))

    def test_internal_crawl_depth(self):
        result = discover_links(
            self.session,
            [self.url("index.html")],
            DiscoveryOptions(mode="generic", respect_robots=False, delay=0, crawl_depth=1, max_pages=10),
        )
        self.assertTrue(any(x.endswith("/files/c.docx") for x in result.download_links))

    def test_json_api_recursive_links_and_pagination(self):
        result = discover_links(
            self.session,
            [self.url("api1.json")],
            DiscoveryOptions(mode="api-json", respect_robots=False, delay=0, max_pages=10),
        )
        self.assertEqual(len(result.download_links), 3)
        self.assertTrue(any(x.endswith("/files/a.pdf") for x in result.download_links))
        self.assertTrue(any(x.endswith("/files/b.zip") for x in result.download_links))
        self.assertTrue(any(x.endswith("/files/c.docx") for x in result.download_links))
        self.assertEqual(len(result.visited_pages), 2)
        self.assertIn("api-json", result.detected_mode)

    def test_phocadownload_adapter(self):
        result = discover_links(
            self.session,
            [self.url("phoca.html")],
            DiscoveryOptions(mode="phocadownload", respect_robots=False, delay=0),
        )
        self.assertEqual(len(result.download_links), 1)
        self.assertIn("download=42:arquivo", result.download_links[0])

    def test_advanced_selector_and_regex(self):
        result = discover_links(
            self.session,
            [self.url("advanced.html")],
            DiscoveryOptions(
                mode="advanced",
                css_selector="#docs",
                href_regex=r"\.pdf(?:\?.*)?$",
                respect_robots=False,
                delay=0,
            ),
        )
        self.assertEqual(len(result.download_links), 1)
        self.assertIn("a.pdf?token=1", result.download_links[0])

    def test_head_probe_for_ambiguous_link(self):
        result = discover_links(
            self.session,
            [self.url("ambiguous.html")],
            DiscoveryOptions(
                mode="auto",
                respect_robots=False,
                delay=0,
                probe_ambiguous=True,
            ),
        )
        self.assertEqual(result.probes_performed, 1)
        self.assertEqual(len(result.download_links), 1)
        self.assertIn("/ambiguous?id=123", result.download_links[0])
        self.assertIn("head-probe", result.detected_mode)

    def test_external_plugin_adapter(self):
        result = discover_links(
            self.session,
            [self.url("plugin.html")],
            DiscoveryOptions(
                mode="auto",
                respect_robots=False,
                delay=0,
                plugin_dir=str(self.root / "plugins"),
            ),
        )
        self.assertEqual(len(result.download_links), 1)
        self.assertTrue(result.download_links[0].endswith("asset.special"))
        self.assertIn("SpecialTest", result.plugins_loaded)
        self.assertIn("plugin:SpecialTest", result.detected_mode)

    def test_embedded_file_url_is_unwrapped(self):
        result = discover_links(
            self.session,
            [self.url("wrapped.html")],
            DiscoveryOptions(mode="auto", respect_robots=False, delay=0),
        )
        self.assertEqual(len(result.download_links), 1)
        self.assertTrue(result.download_links[0].endswith("/files/a.pdf"))
        self.assertIn("embedded-file", result.detected_mode)

    def test_robots_disallow_is_reported(self):
        result = discover_links(
            self.session,
            [self.url("blocked.html")],
            DiscoveryOptions(mode="generic", respect_robots=True, delay=0),
        )
        self.assertEqual(result.download_links, [])
        self.assertEqual(result.robots_blocked, [self.url("blocked.html")])
        self.assertTrue(any("robots.txt não permite coletar" in w for w in result.warnings))

        result_allowed = discover_links(
            self.session,
            [self.url("blocked.html")],
            DiscoveryOptions(mode="generic", respect_robots=False, delay=0),
        )
        self.assertEqual(len(result_allowed.download_links), 1)

    def test_discovery_can_be_cancelled(self):
        event = threading.Event()
        event.set()
        result = discover_links(
            self.session,
            [self.url("index.html")],
            DiscoveryOptions(mode="generic", respect_robots=False, delay=0),
            cancel_event=event,
        )
        self.assertTrue(result.cancelled)
        self.assertEqual(result.visited_pages, [])

    def test_download_and_report(self):
        progress_calls = []
        with tempfile.TemporaryDirectory() as out:
            results = download_all(
                self.session,
                [self.url("files/a.pdf"), self.url("files/b.zip")],
                out,
                workers=2,
                retries=1,
                timeout=5,
                progress=lambda done, total, result: progress_calls.append((done, total, result.status)),
            )
            self.assertTrue(all(r.status == "OK" for r in results))
            self.assertEqual(progress_calls[-1][0:2], (2, 2))
            self.assertEqual([x[0] for x in progress_calls], [1, 2])
            report = write_report(results, out)
            self.assertTrue(report.exists())

    def test_download_cancellation(self):
        event = threading.Event()
        event.set()
        with tempfile.TemporaryDirectory() as out:
            results = download_all(
                self.session,
                [self.url("files/a.pdf"), self.url("files/b.zip")],
                out,
                workers=2,
                retries=1,
                timeout=5,
                cancel_event=event,
            )
            self.assertEqual([r.status for r in results], ["CANCELADO", "CANCELADO"])


if __name__ == "__main__":
    unittest.main()
