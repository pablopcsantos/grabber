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
    write_report,
)


class QuietHandler(SimpleHTTPRequestHandler):
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

    def test_generic_links_and_pagination(self):
        result = discover_links(
            self.session,
            [self.url("index.html")],
            DiscoveryOptions(mode="generic", respect_robots=False, delay=0, max_pages=10),
        )
        self.assertTrue(any(x.endswith("/files/a.pdf") for x in result.download_links))
        self.assertTrue(any(x.endswith("/files/b.zip") for x in result.download_links))
        self.assertEqual(len(result.visited_pages), 2)

    def test_internal_crawl_depth(self):
        result = discover_links(
            self.session,
            [self.url("index.html")],
            DiscoveryOptions(mode="generic", respect_robots=False, delay=0, crawl_depth=1, max_pages=10),
        )
        self.assertTrue(any(x.endswith("/files/c.docx") for x in result.download_links))

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
