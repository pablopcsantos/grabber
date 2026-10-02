# Grabber - Web Crawler & Bulk Downloader

*Leia isto em outros idiomas: [Português](README.md)*

---

Portable desktop application for **discovering and downloading public files in bulk from websites**, with support for different link-discovery strategies and usability designed for people who are not familiar with the command line.

The project originated from the generalization of a downloader originally developed for Joomla/PhocaDownload pages. The new core is no longer tied to a specific domain and has been reorganized to work as a **web crawler + bulk file downloader**, using HTML scraping as only one of the available ways to locate files.

> **Current status:** development version. The roadmap and criteria for a future 1.0 release are available in [`ROADMAP.md`](ROADMAP.md).

---

## Purpose

The program is intended to provide a flexible tool for situations in which a website offers many documents, images, spreadsheets, compressed files, or other resources and the user needs to:

- locate links automatically;
- review how many files were found;
- save the list of URLs;
- download files in bulk;
- resume downloads without silently overwriting existing files;
- generate a transfer report.

The tool is designed primarily for **public content accessible without login**.

---

## Graphical interface

The GUI was developed with Tkinter using a custom style and panel-based layout, avoiding reliance on the classic default Windows appearance.

Current characteristics:

- **dark mode by default**;
- small **?** buttons next to less intuitive settings, opening contextual explanations without leaving the screen;
- **Prioritize main content** option to reduce irrelevant files from menus, footers, and global site areas;
- light mode selectable under `Settings → Appearance`;
- visual preference saved next to the executable so it follows the user on a USB drive;
- selection of a web page or TXT file containing URLs;
- choice of discovery strategy;
- settings for depth, limits, domain, and `robots.txt`;
- concurrency, retry, and timeout parameters;
- discovery separated from downloading;
- visual table for reviewing and unchecking files before download;
- bulk selection, deselection, and inversion;
- cancellation of crawling and downloads;
- deterministic progress during downloads;
- activity panel;
- summary of links, selection, pages, and downloads;
- export of selected links only;
- optional history of the latest session;
- opening of the output folder.

---

## Discovery strategies

### Automatic

Recommended mode for most cases. It currently combines:

- Joomla/PhocaDownload recognition;
- direct links by extension;
- HTML `download` attribute;
- common parameters such as `download=`, `file=`, `arquivo=`, `attachment=`, and similar ones;
- file URLs embedded in HTML viewers when they appear in parameters such as `file=` or `url=`;
- trusted Python adapters available in the `plugins/` directory.

Automatic mode also handles several common differences found on real websites:

- whenever possible, it prioritizes the semantic main region of the page (`<main>`, `<article>`, and known content containers), reducing global links from menus and footers; this preference can be disabled;
- it treats the root domain and its `www.` variant as the same website for domain restriction purposes;
- it can automatically follow **one level** of links that appear to lead to document sections such as “Edital”, “Documentos”, “Arquivos”, “Resultados”, “Gabaritos”, or “Cronograma”, even when the general depth is set to `0`;
- it automatically retries page requests after transient connection failures and HTTP responses such as 429, 500, 502, 503, and 504.

The user can also enable an **optional `HEAD`/`Content-Type` probe** for download buttons whose URL does not contain a recognized extension or parameter. Probing is disabled by default because it generates additional requests.

### Generic HTML / direct links

Looks for files in conventional HTML anchors, such as:

```html
<a href="/documentos/edital.pdf">Baixar edital</a>
```

### Joomla / PhocaDownload

Preserves compatibility with the use case that originated the project, recognizing links with `?download=...` and common Joomla pagination.

### JSON API

Reads endpoints that return JSON and recursively searches for file URLs inside objects and lists.

Conceptual example:

```json
{
  "results": [
    {"file": "/documentos/edital.pdf"},
    {"download": "https://exemplo.org/planilhas/dados.xlsx"}
  ],
  "next": "/api/documentos?page=2"
}
```

Grabber recognizes direct links by extension or download parameters and also handles simple pagination through common fields such as `next`, `next_url`, and `next_page`.

In **Automatic** mode, a response whose `Content-Type` indicates JSON is also analyzed this way. For a URL you already know is an API, explicitly choose **JSON API**.

> This support is generic and does not replace specific integrations when the API requires authentication, proprietary headers, tokens, or an unusual pagination structure.

### Advanced: CSS selector / regex

Allows static HTML websites to be adapted without changing the code.

Examples:

```text
CSS selector: #downloads
```

```text
Href regex: /documentos/.*\.pdf(?:\?.*)?$
```

---

## Discovery plugins

Grabber includes an external adapter infrastructure for websites or CMS platforms that require custom rules.

When running from source, plugins are stored in:

```text
plugins/
```

In the portable version, create the same directory next to `Grabber.exe`.

A plugin can recognize file links and optionally provide a pagination rule. The API is documented in [`plugins/README.md`](plugins/README.md).

> **Security:** plugins are Python modules executed in the same process as Grabber. Use plugins only from trusted sources.

### Recommended external integrations

At present, **there is no third-party plugin for Grabber's specific API that has been validated by the project**. For this reason, the README does not recommend downloading random adapters from the internet and executing them as plugins.

The most interesting and reliable external integration for a future extension is **Playwright for Python**, maintained by Microsoft:

- official documentation: https://playwright.dev/python/
- official repository: https://github.com/microsoft/playwright-python

Playwright automates Chromium, Firefox, and WebKit browsers and would be useful for websites where links only appear after JavaScript execution. It is **not currently a drop-in Grabber plugin** and is not yet included in the portable executable because it requires additional dependencies and browser binaries. The intention is to evaluate it in the future as an optional adapter without unnecessarily increasing the size of the basic program.

---

## Depth-based crawling

By default, the tool analyzes only the initial page and recognized pagination.

The **Depth** option allows internal pages on the same domain to be followed:

- `0`: the supplied page, recognized pagination, and, in Automatic mode, conservative one-level navigation to clearly document-related sections;
- `1`: also analyzes the other internal links found on that page;
- `2+`: continues crawling deeper.

Use greater depths cautiously and keep an appropriate page limit.

---

## Website types where it tends to work well

Detailed documentation is available in [`docs/SUPPORTED_SITES.md`](docs/SUPPORTED_SITES.md).

In summary, the program tends to be useful for:

- HTML pages with direct file links;
- Joomla/PhocaDownload;
- directories and document pages with traditional pagination;
- static websites where files can be identified by CSS selector;
- static websites where links follow a pattern that can be handled with regex;
- any case where the user already has a TXT list of direct URLs.

---

## Cases where the current tool has limited usefulness

The current version **is not a complete automated browser**.

It may not work properly on:

- websites whose content appears only after JavaScript execution;
- pages that depend on React/Vue/Angular and do not provide links in the initial HTML;
- sites requiring login;
- SSO, CSRF, sessions, or special cookies;
- signed and temporary URLs;
- sites protected by CAPTCHA;
- WAFs or antibot mechanisms that block automated requests.

The project is not intended to bypass authentication, CAPTCHA, or protection mechanisms.

Future versions may add an optional automated browser and API adapters.

---

## Responsible use

The tool should only be used when the user has permission to access and automate the content.

By default:

- crawling is restricted to the same domain;
- `robots.txt` checking is enabled;
- there is a pause between pages;
- only four downloads run simultaneously.

When `robots.txt` prohibits crawling a certain page, Grabber **does not access it** while this option is active and shows a specific message explaining why. The user may manually disable **Respect robots.txt (recommended)**, but should do so only when authorized or when there is a legitimate reason to automate that content.

The user can adjust these values, but should avoid overloading servers.

---

## Running from source

Python 3.11 or later is recommended.

Create a virtual environment:

```bash
python -m venv .venv
```

On Windows:

```bat
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run:

```bash
python app.py
```

---

## Basic GUI usage

The interface is organized into three tabs: **Configuration**, **Files found**, and **Activity**.

1. Choose **Web page** or **Link file**.
2. Enter the initial URL or select the TXT file.
3. Keep **Automatic (recommended)** selected initially.
4. Choose the output folder.
5. Click **1. Discover files**.
6. Follow the crawl in the **Activity** tab.
7. When finished, review the table under **Files found**.
8. Uncheck the items you do not want to download; you can also select all, deselect all, or invert the selection.
9. Optionally export only the current selection to TXT.
10. Click **2. Download selected**.
11. The progress bar shows how many downloads have been completed.
12. If necessary, use **Cancel operation**; incomplete `.part` downloads are safely discarded.
13. Check `_relatorio_download.csv` in the output folder.

### Contextual help on screen

The more technical fields in the **Configuration** tab have a small **?** button next to their names. Click it to open a short explanation of:

- discovery mode;
- depth;
- maximum page limit;
- same-domain restriction;
- `robots.txt`;
- `HEAD`/`Content-Type` probing;
- focus on the main page content;
- pause between pages;
- CSS selector;
- `href` regex;
- simultaneous downloads;
- retries;
- timeout.

These dialogs also indicate typical values, situations in which the field should be changed, and when it is best to keep the default value.

### Optional history

By default, Grabber does not need to preserve URLs from the previous session. To quickly restore the configuration and discovered list, enable:

```text
Configurações → Lembrar última sessão
```

This option is voluntary. The history can be cleared from the same menu and is stored in `grabber_settings.json` next to the executable.

If no file is found:

1. check the **Activity** panel to see whether there was a `robots.txt` block, connection failure, or HTTP response;
2. try **Generic HTML / direct links** mode;
3. increase the depth to `1`;
4. inspect the HTML for an appropriate container and provide a CSS selector;
5. use a regex for the URL pattern;
6. enable probing of ambiguous links when download buttons have no extension;
7. if links appear only after JavaScript execution, the current version is probably not suitable for that website.

---

## Manual URL list

You can also bypass the web scraper entirely.

Create a file, for example `links.txt`:

```text
https://exemplo.org/documentos/a.pdf
https://exemplo.org/documentos/b.zip
https://outro.exemplo.org/arquivo.xlsx
```

In the GUI, select **Link file**.

This mode uses only the generic download engine.

---

## Generated files

Downloads are stored in the folder selected by the user.

The report:

```text
_relatorio_download.csv
```

contains:

- URL;
- file name;
- status;
- size in bytes;
- error message, when applicable.

Incomplete downloads temporarily use the extension:

```text
.part
```

The temporary file is renamed to its final name only after the transfer is complete.

---

## File names

The tool tries to determine the file name in this general order:

1. HTTP `Content-Disposition` header;
2. existing name in the URL path;
3. common query-string parameters;
4. numbered generic name + extension inferred from `Content-Type`.

Unlike the original version specifically designed for Brazilian Army documents, the current fallback **does not assume that every file is a PDF**.

Some websites open documents through a viewer page, for example:

```text
/viewer/index.html?file=https%3A%2F%2Fsite.exemplo%2Fdocumento.pdf
```

When the parameter contains a URL that clearly points to a recognized file type, Grabber uses the direct document URL instead of the viewer page.

---

## Resuming and duplicate files

If a file with the same name already exists and the server reports the same `Content-Length`, the download is marked as:

```text
JÁ EXISTIA
```

If the name is already taken but the size does not match, a unique name is created:

```text
arquivo.pdf
arquivo (1).pdf
arquivo (2).pdf
```

---

## CLI

The project preserves a terminal interface for automation and diagnostics.

Example:

```bash
python cli.py --url "https://exemplo.org/documentos" --output ./downloads
```

Specific PhocaDownload mode:

```bash
python cli.py --url "URL" --mode phocadownload
```

Internal crawler with depth 1:

```bash
python cli.py --url "URL" --crawl-depth 1 --max-pages 100
```

CSS selector and regex:

```bash
python cli.py \
  --url "URL" \
  --mode advanced \
  --css-selector ".documentos" \
  --href-regex "\\.pdf(?:\\?.*)?$"
```

Ambiguous-link probing:

```bash
python cli.py --url "URL" --probe-ambiguous --dry-run
```

External plugins in Automatic mode:

```bash
python cli.py --url "URL" --plugins-dir ./plugins --dry-run
```

JSON API endpoint:

```bash
python cli.py --url "https://exemplo.org/api/documentos" --mode api-json --dry-run
```

Disable focus on main content and also scan menus/footers:

```bash
python cli.py --url "URL" --scan-whole-page --dry-run
```

---

## Portable version for USB drives

The project is prepared to generate a single Windows executable with PyInstaller:

```text
Grabber.exe
```

On the development machine, run:

```text
build_windows.bat
```

The result will be created at:

```text
dist\Grabber.exe
```

The executable can be copied to a USB drive and run without Python installed on the target machine.

Simple interface preferences, such as the theme, are stored in:

```text
grabber_settings.json
```

next to the executable. This was deliberately chosen to preserve portable behavior.

The repository also contains a GitHub Actions workflow for building the executable on Windows.

---

## Project structure

```text
Grabber/
├── .github/
│   └── workflows/
│       ├── build-windows.yml
│       └── tests.yml
├── assets/
│   ├── grabber.ico
│   ├── grabber.svg
│   ├── grabber.png
│   └── README.md
├── plugins/
│   ├── README.md
│   └── example_adapter.py.example
├── tests/
│   └── test_core.py
├── docs/
│   ├── ARCHITECTURE.md
│   ├── SUPPORTED_SITES.md
│   └── TEST_MATRIX.md
├── legacy/
│   └── eb_downloader.py
├── app.py
├── adapters.py
├── core.py
├── cli.py
├── ROADMAP.md
├── CHANGELOG.md
├── README.md
├── requirements.txt
├── requirements-build.txt
├── build_windows.bat
└── .gitignore
```

---

## Architecture

The main separation is:

- `core.py`: discovery, probing, cancellation, and downloading;
- `adapters.py`: safe loading of the structural plugin API (trust in plugin code remains the user's responsibility);
- `app.py`: GUI, selection review, progress, and optional history;
- `cli.py`: terminal interface;
- `legacy/eb_downloader.py`: original script preserved for historical reference only.

Details are available in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Roadmap

Development milestones and objective criteria for considering version 1.0 ready are documented in:

[`ROADMAP.md`](ROADMAP.md)

The features planned for Milestones 1, 2, and 3 are already implemented. The items that currently matter most for version 1.0 are related to **external validation**:

- documented tests on real public websites from different categories;
- executable tests on Windows 10 and Windows 11;
- execution on a machine without Python installed;
- execution from a USB drive;
- fixes resulting from those tests.

Features such as Playwright, generic authentication, signed URLs, and integrations with complex APIs remain planned for later versions and do not block 1.0. Initial generic JSON API support is already implemented.

---

## Technologies

- Python 3;
- Tkinter / ttk;
- Requests;
- Beautiful Soup 4;
- PyInstaller;
- GitHub Actions.

---

## Automated tests

The core includes local integration tests that do not depend on external websites. They currently cover **16 scenarios**:

- direct links + pagination;
- equivalence between the root domain and its `www.` variant;
- automatic navigation to a document section at depth `0`;
- retrying page requests after transient HTTP failures;
- automatic focus on the main page region, with the option to scan the entire page;
- internal depth-based crawling;
- PhocaDownload adapter;
- recursive discovery and simple pagination in JSON APIs;
- CSS selector + regex;
- `HEAD`/`Content-Type` probing of an ambiguous link;
- loadable external plugin;
- file URL embedded in a viewer;
- respecting and logging `robots.txt` blocking;
- discovery cancellation;
- download, CSV report, and progress callback;
- download cancellation.

Run with:

```bash
python -m unittest discover -s tests -v
```

The `tests.yml` workflow runs the suite on Windows and Linux with Python 3.11 and 3.12. The distinction between local tests and real-world manual validation is documented in [`docs/TEST_MATRIX.md`](docs/TEST_MATRIX.md).

---

## 👤 Authorship and development

**Grabber** is a portable desktop application for web crawling and bulk downloading of public files, independently developed by **Pablo Phillipe Cândido dos Santos**. The project is intended for discovering, reviewing, and transferring files in bulk from websites and JSON APIs, with configurable collection strategies, prior link selection, and download report generation.

Generative artificial intelligence tools were used as auxiliary resources during development, while responsibility for the project's conception, implementation, integration, and verification remained with the author.

Lattes CV: [http://lattes.cnpq.br/9500873674712528](http://lattes.cnpq.br/9500873674712528)
