from __future__ import annotations

"""
Grabber

GUI portátil para descoberta e download em massa de arquivos públicos em websites.
A aplicação separa descoberta, revisão dos links e download, com estratégias para
HTML genérico, Joomla/PhocaDownload, regras CSS/regex, sondagem HTTP opcional e
adaptadores externos carregáveis.
"""

import json
import os
import queue
import subprocess
import sys
import threading
import traceback
from pathlib import Path
from typing import Any

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from core import (
    DiscoveryOptions,
    DiscoveryResult,
    dedupe_preserve_order,
    discover_links,
    download_all,
    filename_hint_from_url,
    load_links_from_file,
    make_session,
    write_report,
)


APP_NAME = "Grabber"
APP_VERSION = "0.3.5-dev"

THEMES = {
    "dark": {
        "bg": "#0B1220", "surface": "#111A2C", "surface2": "#18243A",
        "text": "#EEF4FB", "muted": "#94A3B8", "border": "#2B3B55",
        "accent": "#3B82F6", "accent_hover": "#2563EB", "success": "#22C55E",
        "danger": "#EF4444", "warning": "#F59E0B", "entry": "#0E1728",
        "log_bg": "#08101D", "log_fg": "#D7E1EF", "selection": "#1D4ED8",
    },
    "light": {
        "bg": "#F4F7FB", "surface": "#FFFFFF", "surface2": "#EEF3F8",
        "text": "#172033", "muted": "#66758A", "border": "#D7E0EA",
        "accent": "#2563EB", "accent_hover": "#1D4ED8", "success": "#16A34A",
        "danger": "#DC2626", "warning": "#D97706", "entry": "#FFFFFF",
        "log_bg": "#F8FAFC", "log_fg": "#1E293B", "selection": "#BFDBFE",
    },
}

MODE_LABEL_TO_KEY = {
    "Automático (recomendado)": "auto",
    "HTML genérico / links diretos": "generic",
    "Joomla / PhocaDownload": "phocadownload",
    "API JSON": "api-json",
    "Avançado: seletor CSS / regex": "advanced",
}


def app_directory() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def settings_path() -> Path:
    # Deliberadamente ao lado do executável: tema e histórico podem acompanhar o pendrive.
    return app_directory() / "grabber_settings.json"


def plugin_directory() -> Path:
    return app_directory() / "plugins"


def resource_path(relative: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative


def apply_app_icon(window: tk.Misc) -> None:
    ico = resource_path("assets/grabber.ico")
    png = resource_path("assets/grabber.png")
    try:
        if sys.platform.startswith("win") and ico.exists():
            window.wm_iconbitmap(str(ico))
            return
    except Exception:
        pass
    try:
        if png.exists():
            image = tk.PhotoImage(file=str(png))
            window.wm_iconphoto(True, image)
            setattr(window, "_grabber_icon", image)
    except Exception:
        pass


def load_settings() -> dict[str, Any]:
    try:
        data = json.loads(settings_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_settings(changes: dict[str, Any]) -> None:
    """Mescla alterações para não apagar tema/histórico ao salvar outra preferência."""
    try:
        data = load_settings()
        data.update(changes)
        settings_path().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def open_path(path: Path) -> None:
    path = path.resolve()
    if sys.platform.startswith("win"):
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry("1180x860")
        self.minsize(920, 700)
        apply_app_icon(self)

        stored = load_settings()
        self.theme_name = stored.get("theme") if stored.get("theme") in THEMES else "dark"
        self.theme_var = tk.StringVar(value=self.theme_name)
        self.remember_session_var = tk.BooleanVar(value=bool(stored.get("remember_last_session", False)))

        self.log_queue: queue.Queue[str] = queue.Queue()
        self.ui_queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.running = False
        self.operation_kind = ""
        self.cancel_event = threading.Event()
        self.session = make_session()
        self.discovery_result: DiscoveryResult | None = None
        self.links: list[str] = []
        self.link_selection: dict[str, bool] = {}
        self.tree_url_by_iid: dict[str, str] = {}

        self.source_type = tk.StringVar(value="Página web")
        self.url_var = tk.StringVar()
        self.link_file_var = tk.StringVar()
        self.output_var = tk.StringVar(value=str(app_directory() / "downloads"))
        self.mode_var = tk.StringVar(value="Automático (recomendado)")
        self.max_pages_var = tk.IntVar(value=50)
        self.delay_var = tk.DoubleVar(value=0.7)
        self.crawl_depth_var = tk.IntVar(value=0)
        self.same_domain_var = tk.BooleanVar(value=True)
        self.robots_var = tk.BooleanVar(value=True)
        self.probe_var = tk.BooleanVar(value=False)
        self.main_content_var = tk.BooleanVar(value=True)
        self.selector_var = tk.StringVar()
        self.regex_var = tk.StringVar()
        self.workers_var = tk.IntVar(value=4)
        self.retries_var = tk.IntVar(value=3)
        self.timeout_var = tk.IntVar(value=60)

        self.count_links_var = tk.StringVar(value="0")
        self.count_selected_var = tk.StringVar(value="0")
        self.count_pages_var = tk.StringVar(value="0")
        self.detected_var = tk.StringVar(value="—")
        self.download_summary_var = tk.StringVar(value="Ainda não executado")
        self.progress_text_var = tk.StringVar(value="Pronto")

        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        self._build_menu()
        self._build_ui()
        self._apply_theme()
        self._refresh_source_state()

        if self.remember_session_var.get():
            self._restore_last_session(silent=True)

        self.after(100, self._consume_queues)

    @property
    def colors(self) -> dict[str, str]:
        return THEMES[self.theme_name]

    # ---------- menus / settings ----------
    def _build_menu(self) -> None:
        menu = tk.Menu(self, tearoff=False)
        config = tk.Menu(menu, tearoff=False)
        appearance = tk.Menu(config, tearoff=False)
        appearance.add_radiobutton(
            label="Modo escuro", variable=self.theme_var, value="dark",
            command=lambda: self._set_theme("dark"),
        )
        appearance.add_radiobutton(
            label="Modo claro", variable=self.theme_var, value="light",
            command=lambda: self._set_theme("light"),
        )
        config.add_cascade(label="Aparência", menu=appearance)
        config.add_separator()
        config.add_checkbutton(
            label="Lembrar última sessão",
            variable=self.remember_session_var,
            command=self._toggle_remember_session,
        )
        config.add_command(label="Restaurar última sessão", command=lambda: self._restore_last_session(silent=False))
        config.add_command(label="Limpar histórico da sessão", command=self._clear_history)
        config.add_separator()
        config.add_command(label="Restaurar configurações padrão", command=self._reset_defaults)
        menu.add_cascade(label="Configurações", menu=config)

        help_menu = tk.Menu(menu, tearoff=False)
        help_menu.add_command(label="Sobre", command=self._show_about)
        menu.add_cascade(label="Ajuda", menu=help_menu)

        self.config(menu=menu)
        self._menus = [menu, config, appearance, help_menu]

    def _toggle_remember_session(self) -> None:
        enabled = bool(self.remember_session_var.get())
        save_settings({"remember_last_session": enabled})
        if enabled:
            self._save_last_session()
        else:
            data = load_settings()
            data.pop("last_session", None)
            try:
                settings_path().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            except OSError:
                pass

    def _session_snapshot(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type.get(),
            "url": self.url_var.get(),
            "link_file": self.link_file_var.get(),
            "output": self.output_var.get(),
            "mode": self.mode_var.get(),
            "max_pages": int(self.max_pages_var.get()),
            "delay": float(self.delay_var.get()),
            "crawl_depth": int(self.crawl_depth_var.get()),
            "same_domain": bool(self.same_domain_var.get()),
            "robots": bool(self.robots_var.get()),
            "probe": bool(self.probe_var.get()),
            "main_content": bool(self.main_content_var.get()),
            "selector": self.selector_var.get(),
            "regex": self.regex_var.get(),
            "workers": int(self.workers_var.get()),
            "retries": int(self.retries_var.get()),
            "timeout": int(self.timeout_var.get()),
            "links": self.links[:5000],
            "selected": [u for u in self.links if self.link_selection.get(u, True)][:5000],
        }

    def _save_last_session(self) -> None:
        if self.remember_session_var.get():
            save_settings({"remember_last_session": True, "last_session": self._session_snapshot()})

    def _restore_last_session(self, silent: bool = False) -> None:
        data = load_settings().get("last_session")
        if not isinstance(data, dict):
            if not silent:
                messagebox.showinfo("Histórico", "Nenhuma sessão anterior foi armazenada.")
            return
        try:
            self.source_type.set(data.get("source_type", "Página web"))
            self.url_var.set(data.get("url", ""))
            self.link_file_var.set(data.get("link_file", ""))
            self.output_var.set(data.get("output", str(app_directory() / "downloads")))
            mode = data.get("mode", "Automático (recomendado)")
            self.mode_var.set(mode if mode in MODE_LABEL_TO_KEY else "Automático (recomendado)")
            self.max_pages_var.set(int(data.get("max_pages", 50)))
            self.delay_var.set(float(data.get("delay", 0.7)))
            self.crawl_depth_var.set(int(data.get("crawl_depth", 0)))
            self.same_domain_var.set(bool(data.get("same_domain", True)))
            self.robots_var.set(bool(data.get("robots", True)))
            self.probe_var.set(bool(data.get("probe", False)))
            self.main_content_var.set(bool(data.get("main_content", True)))
            self.selector_var.set(data.get("selector", ""))
            self.regex_var.set(data.get("regex", ""))
            self.workers_var.set(int(data.get("workers", 4)))
            self.retries_var.set(int(data.get("retries", 3)))
            self.timeout_var.set(int(data.get("timeout", 60)))
            links = [str(x) for x in data.get("links", []) if str(x).startswith(("http://", "https://"))]
            selected = set(str(x) for x in data.get("selected", []))
            self.links = dedupe_preserve_order(links)
            self.link_selection = {u: (u in selected if selected else True) for u in self.links}
            self._populate_link_table(preserve_selection=True)
            self.count_links_var.set(str(len(self.links)))
            self._refresh_source_state()
            self.download_btn.configure(state="normal" if self._selected_links() else "disabled")
            if not silent:
                messagebox.showinfo("Histórico", "A última sessão armazenada foi restaurada.")
        except Exception as exc:
            if not silent:
                messagebox.showerror("Histórico", f"Não foi possível restaurar a sessão:\n{exc}")

    def _clear_history(self) -> None:
        data = load_settings()
        if "last_session" not in data:
            messagebox.showinfo("Histórico", "Não há histórico de sessão armazenado.")
            return
        if not messagebox.askyesno("Limpar histórico", "Apagar os dados da última sessão armazenada?"):
            return
        data.pop("last_session", None)
        try:
            settings_path().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass
        messagebox.showinfo("Histórico", "O histórico da última sessão foi apagado.")

    # ---------- UI ----------
    def _build_ui(self) -> None:
        root = ttk.Frame(self, style="Root.TFrame", padding=(24, 20))
        root.pack(fill="both", expand=True)

        top = ttk.Frame(root, style="Root.TFrame")
        top.pack(fill="x", pady=(0, 14))
        title_row = ttk.Frame(top, style="Root.TFrame")
        title_row.pack(fill="x")
        ttk.Label(title_row, text=APP_NAME, style="Title.TLabel").pack(side="left")
        ttk.Label(title_row, text=f"v{APP_VERSION}", style="Badge.TLabel").pack(side="left", padx=(12, 0))
        ttk.Label(
            top,
            text="Descoberta, revisão e download em massa de arquivos públicos em websites",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True)
        config_tab = ttk.Frame(self.notebook, style="Root.TFrame", padding=14)
        files_tab = ttk.Frame(self.notebook, style="Root.TFrame", padding=14)
        activity_tab = ttk.Frame(self.notebook, style="Root.TFrame", padding=14)
        self.notebook.add(config_tab, text="Configuração")
        self.notebook.add(files_tab, text="Arquivos encontrados")
        self.notebook.add(activity_tab, text="Atividade")
        self.files_tab = files_tab
        self.activity_tab = activity_tab

        self._build_config_tab(config_tab)
        self._build_files_tab(files_tab)
        self._build_activity_tab(activity_tab)

    def _build_config_tab(self, root: ttk.Frame) -> None:
        source = self._card(root)
        source.pack(fill="x", pady=(0, 12))
        ttk.Label(source, text="1 · Origem", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w", columnspan=4)
        ttk.Label(
            source,
            text="Use uma página web para descobrir arquivos ou forneça uma lista de URLs diretas.",
            style="CardMuted.TLabel",
        ).grid(row=1, column=0, sticky="w", columnspan=4, pady=(3, 12))

        ttk.Label(source, text="Tipo", style="Card.TLabel").grid(row=2, column=0, sticky="w", padx=(0, 8))
        source_combo = ttk.Combobox(
            source, textvariable=self.source_type, values=("Página web", "Arquivo de links"), state="readonly", width=20,
        )
        source_combo.grid(row=2, column=1, sticky="w")
        source_combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_source_state())

        ttk.Label(source, text="URL", style="Card.TLabel").grid(row=3, column=0, sticky="w", pady=(10, 0), padx=(0, 8))
        self.url_entry = ttk.Entry(source, textvariable=self.url_var, style="Modern.TEntry")
        self.url_entry.grid(row=3, column=1, columnspan=3, sticky="ew", pady=(10, 0))

        ttk.Label(source, text="Lista TXT", style="Card.TLabel").grid(row=4, column=0, sticky="w", pady=(8, 0), padx=(0, 8))
        self.link_entry = ttk.Entry(source, textvariable=self.link_file_var, style="Modern.TEntry")
        self.link_entry.grid(row=4, column=1, columnspan=2, sticky="ew", pady=(8, 0))
        self.link_button = ttk.Button(source, text="Selecionar", style="Modern.TButton", command=self._choose_link_file)
        self.link_button.grid(row=4, column=3, sticky="e", pady=(8, 0), padx=(8, 0))
        source.columnconfigure(1, weight=1)
        source.columnconfigure(2, weight=1)

        strategy = self._card(root)
        strategy.pack(fill="x", pady=(0, 12))
        ttk.Label(strategy, text="2 · Estratégia de descoberta", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w", columnspan=6)
        ttk.Label(
            strategy,
            text="O modo automático combina regras nativas e plugins confiáveis presentes na pasta plugins/.",
            style="CardMuted.TLabel", wraplength=980,
        ).grid(row=1, column=0, sticky="w", columnspan=6, pady=(3, 12))

        self._field_label(
            strategy, "Modo", "Modo de descoberta",
            "Automático (recomendado): combina as regras nativas, navegação documental e plugins confiáveis.\n\n"
            "HTML genérico: procura links diretos em páginas HTML convencionais.\n\n"
            "Joomla / PhocaDownload: prioriza o padrão ?download= usado por esse componente.\n\n"
            "API JSON: lê uma resposta JSON e procura recursivamente URLs de arquivos, incluindo paginação simples por campos como next/next_url.\n\n"
            "Avançado: permite restringir a descoberta com seletor CSS e/ou regex."
        ).grid(row=2, column=0, sticky="w")
        ttk.Combobox(strategy, textvariable=self.mode_var, values=tuple(MODE_LABEL_TO_KEY), state="readonly", width=32).grid(
            row=2, column=1, sticky="w", padx=(8, 16)
        )
        self._field_label(
            strategy, "Profundidade", "Profundidade de rastreamento",
            "Define quantos níveis de páginas internas o Grabber pode seguir.\n\n"
            "0: permanece na página inicial, na paginação e, no modo Automático, pode abrir uma seção claramente documental como 'Edital' ou 'Resultados'.\n"
            "1: também visita os demais links internos encontrados na primeira página.\n"
            "2 ou mais: continua aprofundando o rastreamento.\n\n"
            "Valores maiores aumentam o tempo e a quantidade de páginas acessadas."
        ).grid(row=2, column=2, sticky="w")
        ttk.Spinbox(strategy, from_=0, to=5, textvariable=self.crawl_depth_var, width=6).grid(row=2, column=3, sticky="w", padx=(8, 16))
        self._field_label(
            strategy, "Máx. páginas", "Limite de páginas",
            "Número máximo de páginas HTML que a coleta poderá abrir nesta execução.\n\n"
            "Serve como limite de segurança para impedir que um crawler entre em uma navegação muito extensa. "
            "O padrão de 50 costuma ser suficiente para páginas de documentos e pequenos portais."
        ).grid(row=2, column=4, sticky="w")
        ttk.Spinbox(strategy, from_=1, to=1000, textvariable=self.max_pages_var, width=8).grid(row=2, column=5, sticky="w", padx=(8, 0))

        self._help_check(
            strategy, "Restringir ao mesmo domínio", self.same_domain_var,
            "Restrição de domínio",
            "Quando habilitado, o Grabber evita seguir páginas pertencentes a outros sites. "
            "A variante com e sem 'www.' é tratada como o mesmo domínio.\n\n"
            "É recomendável manter esta opção ligada para evitar que a coleta se espalhe para sites externos."
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 0))
        self._help_check(
            strategy, "Respeitar robots.txt (recomendado)", self.robots_var,
            "robots.txt",
            "robots.txt é um arquivo publicado pelo próprio site que pode indicar quais áreas não devem ser acessadas por robôs/crawlers.\n\n"
            "Com esta opção ligada, o Grabber deixa de coletar URLs proibidas por essa política. "
            "Desative apenas quando você tiver autorização ou uma razão legítima para automatizar aquele conteúdo."
        ).grid(row=3, column=2, columnspan=2, sticky="w", pady=(10, 0))
        self._help_check(
            strategy, "Sondar links ambíguos (HEAD/Content-Type)", self.probe_var,
            "Sondagem de links ambíguos",
            "Alguns botões de download não possuem .pdf, .zip ou outra extensão na URL.\n\n"
            "Ao habilitar esta opção, o Grabber envia uma requisição HEAD (ou um GET de fallback) para verificar os cabeçalhos e descobrir se o endereço realmente entrega um arquivo.\n\n"
            "Use quando a coleta normal não reconhece botões de download. Gera requisições extras."
        ).grid(row=3, column=4, columnspan=2, sticky="w", pady=(10, 0))

        self._help_check(
            strategy, "Priorizar conteúdo principal", self.main_content_var,
            "Foco no conteúdo principal",
            "No modo Automático, o Grabber tenta analisar primeiro a região central da página "
            "(por exemplo <main>, <article> ou áreas de conteúdo comuns), ignorando links globais de menus e rodapés.\n\n"
            "Isso reduz arquivos irrelevantes em portais grandes. Desative se os arquivos esperados estiverem fora da área principal."
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(10, 0))

        self._field_label(
            strategy, "Pausa entre páginas (s)", "Pausa entre páginas",
            "Intervalo, em segundos, entre a leitura de páginas durante a descoberta.\n\n"
            "Uma pausa reduz a carga no servidor. O padrão é conservador; aumente-o em sites pequenos ou quando houver respostas HTTP 429."
        ).grid(row=5, column=0, sticky="w", pady=(10, 0))
        ttk.Spinbox(strategy, from_=0, to=10, increment=0.1, textvariable=self.delay_var, width=8).grid(row=5, column=1, sticky="w", padx=(8, 16), pady=(10, 0))
        self._field_label(
            strategy, "Seletor CSS", "Seletor CSS",
            "Campo avançado. Use um seletor CSS para limitar a análise a uma região da página.\n\n"
            "Exemplos: #downloads, .documentos, main article\n\n"
            "Normalmente deixe em branco. É mais útil no modo Avançado quando a página possui muitos links não relacionados."
        ).grid(row=5, column=2, sticky="w", pady=(10, 0))
        ttk.Entry(strategy, textvariable=self.selector_var, style="Modern.TEntry").grid(row=5, column=3, sticky="ew", padx=(8, 16), pady=(10, 0))
        self._field_label(
            strategy, "Regex do href", "Regex do href",
            "Campo avançado. Expressão regular usada para filtrar as URLs encontradas.\n\n"
            "Exemplo para PDFs: \\.pdf(?:\\?.*)?$\n\n"
            "Deixe em branco se não souber qual padrão usar. Uma regex incorreta pode ocultar arquivos válidos."
        ).grid(row=5, column=4, sticky="w", pady=(10, 0))
        ttk.Entry(strategy, textvariable=self.regex_var, style="Modern.TEntry").grid(row=5, column=5, sticky="ew", padx=(8, 0), pady=(10, 0))
        strategy.columnconfigure(3, weight=1)
        strategy.columnconfigure(5, weight=1)

        ttk.Label(
            strategy,
            text="A sondagem é opcional porque cria requisições extras. Ela é útil quando o botão diz 'Baixar', mas a URL não possui extensão nem parâmetro reconhecido.",
            style="CardMuted.TLabel", wraplength=980,
        ).grid(row=6, column=0, columnspan=6, sticky="w", pady=(8, 0))

        output = self._card(root)
        output.pack(fill="x", pady=(0, 12))
        ttk.Label(output, text="3 · Saída e downloads", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w", columnspan=7)
        ttk.Label(output, text="Pasta de saída", style="Card.TLabel").grid(row=1, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(output, textvariable=self.output_var, style="Modern.TEntry").grid(row=1, column=1, columnspan=4, sticky="ew", padx=(8, 8), pady=(10, 0))
        ttk.Button(output, text="Selecionar pasta", style="Modern.TButton", command=self._choose_output).grid(row=1, column=5, sticky="e", pady=(10, 0))
        output.columnconfigure(4, weight=1)
        self._field_label(
            output, "Downloads simultâneos", "Downloads simultâneos",
            "Quantidade máxima de arquivos que podem ser baixados ao mesmo tempo.\n\n"
            "Valores maiores podem acelerar a transferência, mas também aumentam a carga sobre o servidor e sua conexão. "
            "O padrão de 4 é uma escolha moderada."
        ).grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Spinbox(output, from_=1, to=24, textvariable=self.workers_var, width=7).grid(row=2, column=1, sticky="w", padx=(8, 18), pady=(10, 0))
        self._field_label(
            output, "Tentativas", "Tentativas de download",
            "Número de tentativas usadas para baixar cada arquivo quando ocorre uma falha.\n\n"
            "Aumentar esse valor pode ajudar em conexões instáveis, mas também torna falhas permanentes mais demoradas."
        ).grid(row=2, column=2, sticky="w", pady=(10, 0))
        ttk.Spinbox(output, from_=1, to=10, textvariable=self.retries_var, width=7).grid(row=2, column=3, sticky="w", padx=(8, 18), pady=(10, 0))
        self._field_label(
            output, "Timeout (s)", "Tempo limite",
            "Tempo máximo, em segundos, que uma operação de rede pode aguardar antes de ser considerada sem resposta.\n\n"
            "Aumente em servidores lentos ou arquivos grandes; diminua apenas se quiser detectar falhas mais rapidamente."
        ).grid(row=2, column=4, sticky="w", pady=(10, 0))
        ttk.Spinbox(output, from_=5, to=600, textvariable=self.timeout_var, width=8).grid(row=2, column=5, sticky="w", padx=(8, 0), pady=(10, 0))

        actions = ttk.Frame(root, style="Root.TFrame")
        actions.pack(fill="x", pady=(0, 12))
        self.discover_btn = ttk.Button(actions, text="1. Descobrir arquivos", style="Primary.TButton", command=self._start_discovery)
        self.discover_btn.pack(side="left")
        self.download_btn = ttk.Button(actions, text="2. Baixar selecionados", style="Success.TButton", command=self._start_download, state="disabled")
        self.download_btn.pack(side="left", padx=(8, 0))
        self.cancel_btn = ttk.Button(actions, text="Cancelar operação", style="Danger.TButton", command=self._cancel_operation, state="disabled")
        self.cancel_btn.pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Abrir pasta de saída", style="Modern.TButton", command=self._open_output).pack(side="right")

        dashboard = ttk.Frame(root, style="Root.TFrame")
        dashboard.pack(fill="x", pady=(0, 12))
        self._stat(dashboard, "Encontrados", self.count_links_var).pack(side="left", fill="x", expand=True, padx=(0, 5))
        self._stat(dashboard, "Selecionados", self.count_selected_var).pack(side="left", fill="x", expand=True, padx=5)
        self._stat(dashboard, "Páginas", self.count_pages_var).pack(side="left", fill="x", expand=True, padx=5)
        self._stat(dashboard, "Estratégia", self.detected_var).pack(side="left", fill="x", expand=True, padx=5)
        self._stat(dashboard, "Downloads", self.download_summary_var).pack(side="left", fill="x", expand=True, padx=(5, 0))

        ttk.Label(
            root,
            text="Use somente em conteúdo que você tem permissão para acessar e automatizar. O Grabber não foi projetado para contornar login, CAPTCHA ou controles de acesso.",
            style="Muted.TLabel", wraplength=1060,
        ).pack(anchor="w", pady=(2, 0))

    def _build_files_tab(self, root: ttk.Frame) -> None:
        card = self._card(root)
        card.pack(fill="both", expand=True)
        toolbar = ttk.Frame(card, style="Card.TFrame")
        toolbar.pack(fill="x", pady=(0, 10))
        ttk.Label(toolbar, text="Revise o que será baixado", style="CardTitle.TLabel").pack(side="left")
        ttk.Button(toolbar, text="Selecionar todos", style="Modern.TButton", command=lambda: self._set_all_selection(True)).pack(side="right")
        ttk.Button(toolbar, text="Desmarcar todos", style="Modern.TButton", command=lambda: self._set_all_selection(False)).pack(side="right", padx=(0, 6))
        ttk.Button(toolbar, text="Inverter", style="Modern.TButton", command=self._invert_selection).pack(side="right", padx=(0, 6))

        ttk.Label(
            card,
            text="Clique na coluna 'Baixar?' para incluir ou excluir um item. A lista permanece disponível antes do download.",
            style="CardMuted.TLabel",
        ).pack(anchor="w", pady=(0, 10))

        table_frame = ttk.Frame(card, style="Card.TFrame")
        table_frame.pack(fill="both", expand=True)
        columns = ("selected", "name", "url")
        self.link_tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        self.link_tree.heading("selected", text="Baixar?")
        self.link_tree.heading("name", text="Nome provável")
        self.link_tree.heading("url", text="URL")
        self.link_tree.column("selected", width=78, minwidth=70, anchor="center", stretch=False)
        self.link_tree.column("name", width=260, minwidth=160, anchor="w")
        self.link_tree.column("url", width=680, minwidth=320, anchor="w")
        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.link_tree.yview)
        xscroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.link_tree.xview)
        self.link_tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.link_tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        self.link_tree.bind("<ButtonRelease-1>", self._tree_click)

        bottom = ttk.Frame(card, style="Card.TFrame")
        bottom.pack(fill="x", pady=(10, 0))
        ttk.Label(bottom, textvariable=self.count_selected_var, style="Badge.TLabel").pack(side="left")
        ttk.Label(bottom, text=" arquivo(s) selecionado(s)", style="CardMuted.TLabel").pack(side="left", padx=(4, 0))
        ttk.Button(bottom, text="Exportar seleção", style="Modern.TButton", command=self._export_links).pack(side="right")
        ttk.Button(bottom, text="Baixar selecionados", style="Success.TButton", command=self._start_download).pack(side="right", padx=(0, 8))

    def _build_activity_tab(self, root: ttk.Frame) -> None:
        card = self._card(root)
        card.pack(fill="both", expand=True)
        bar = ttk.Frame(card, style="Card.TFrame")
        bar.pack(fill="x", pady=(0, 10))
        ttk.Label(bar, text="Progresso e mensagens", style="CardTitle.TLabel").pack(side="left")
        ttk.Label(bar, textvariable=self.progress_text_var, style="CardMuted.TLabel").pack(side="right", padx=(0, 10))
        self.progress = ttk.Progressbar(bar, mode="indeterminate", style="Modern.Horizontal.TProgressbar", length=280)
        self.progress.pack(side="right")
        self.log = ScrolledText(card, height=24, wrap="word", font=("Cascadia Mono", 9), relief="flat", borderwidth=0)
        self.log.pack(fill="both", expand=True)
        self.log.configure(state="disabled")

    def _show_field_help(self, title: str, message: str) -> None:
        messagebox.showinfo(title, message, parent=self)

    def _field_label(self, parent, text: str, help_title: str, help_text: str) -> ttk.Frame:
        frame = ttk.Frame(parent, style="Card.TFrame")
        ttk.Label(frame, text=text, style="Card.TLabel").pack(side="left")
        ttk.Button(
            frame,
            text="?",
            width=2,
            style="Help.TButton",
            command=lambda: self._show_field_help(help_title, help_text),
        ).pack(side="left", padx=(5, 0))
        return frame

    def _help_check(self, parent, text: str, variable: tk.Variable, help_title: str, help_text: str) -> ttk.Frame:
        frame = ttk.Frame(parent, style="Card.TFrame")
        ttk.Checkbutton(frame, text=text, variable=variable).pack(side="left")
        ttk.Button(
            frame,
            text="?",
            width=2,
            style="Help.TButton",
            command=lambda: self._show_field_help(help_title, help_text),
        ).pack(side="left", padx=(5, 0))
        return frame

    def _card(self, parent) -> ttk.Frame:
        return ttk.Frame(parent, style="Card.TFrame", padding=16)

    def _stat(self, parent, title: str, variable: tk.StringVar) -> ttk.Frame:
        frame = ttk.Frame(parent, style="Card.TFrame", padding=(12, 9))
        ttk.Label(frame, text=title, style="CardMuted.TLabel").pack(anchor="w")
        ttk.Label(frame, textvariable=variable, style="Stat.TLabel").pack(anchor="w", pady=(3, 0))
        return frame

    # ---------- theme ----------
    def _set_theme(self, name: str) -> None:
        self.theme_name = name
        self.theme_var.set(name)
        save_settings({"theme": name})
        self._apply_theme()

    def _apply_theme(self) -> None:
        c = self.colors
        self.configure(bg=c["bg"])
        self.style.configure("Root.TFrame", background=c["bg"])
        self.style.configure("Card.TFrame", background=c["surface"])
        self.style.configure("TFrame", background=c["bg"])
        self.style.configure("TLabel", background=c["bg"], foreground=c["text"], font=("Segoe UI", 10))
        self.style.configure("Card.TLabel", background=c["surface"], foreground=c["text"])
        self.style.configure("Title.TLabel", background=c["bg"], foreground=c["text"], font=("Segoe UI Variable Display", 24, "bold"))
        self.style.configure("Muted.TLabel", background=c["bg"], foreground=c["muted"], font=("Segoe UI", 9))
        self.style.configure("CardTitle.TLabel", background=c["surface"], foreground=c["text"], font=("Segoe UI", 11, "bold"))
        self.style.configure("CardMuted.TLabel", background=c["surface"], foreground=c["muted"], font=("Segoe UI", 9))
        self.style.configure("Stat.TLabel", background=c["surface"], foreground=c["text"], font=("Segoe UI", 13, "bold"))
        self.style.configure("Badge.TLabel", background=c["surface2"], foreground=c["accent"], padding=(8, 3), font=("Segoe UI", 9, "bold"))
        self.style.configure("Modern.TEntry", fieldbackground=c["entry"], foreground=c["text"], insertcolor=c["text"], bordercolor=c["border"], padding=8)
        self.style.configure("TCombobox", fieldbackground=c["entry"], background=c["surface2"], foreground=c["text"], arrowcolor=c["text"], bordercolor=c["border"])
        self.style.map("TCombobox", fieldbackground=[("readonly", c["entry"])], foreground=[("readonly", c["text"])])
        self.style.configure("TSpinbox", fieldbackground=c["entry"], foreground=c["text"], arrowcolor=c["text"], bordercolor=c["border"])
        self.style.configure("TCheckbutton", background=c["surface"], foreground=c["text"])
        self.style.map("TCheckbutton", background=[("active", c["surface"])])
        self._button_style("Modern.TButton", c["surface2"], c["text"])
        self._button_style("Help.TButton", c["surface2"], c["accent"])
        self.style.configure("Help.TButton", padding=(4, 1), font=("Segoe UI", 8, "bold"))
        self._button_style("Primary.TButton", c["accent"], "#FFFFFF")
        self._button_style("Success.TButton", c["success"], "#FFFFFF")
        self._button_style("Danger.TButton", c["danger"], "#FFFFFF")
        self.style.configure("Modern.Horizontal.TProgressbar", troughcolor=c["surface2"], background=c["accent"], thickness=8)
        self.style.configure("TNotebook", background=c["bg"], borderwidth=0)
        self.style.configure("TNotebook.Tab", background=c["surface2"], foreground=c["text"], padding=(14, 8))
        self.style.map("TNotebook.Tab", background=[("selected", c["surface"]), ("active", c["surface2"])], foreground=[("selected", c["accent"])])
        self.style.configure("Treeview", background=c["entry"], fieldbackground=c["entry"], foreground=c["text"], rowheight=28, bordercolor=c["border"])
        self.style.configure("Treeview.Heading", background=c["surface2"], foreground=c["text"], relief="flat", font=("Segoe UI", 9, "bold"))
        self.style.map("Treeview", background=[("selected", c["selection"])], foreground=[("selected", "#FFFFFF")])
        self.style.map("Treeview.Heading", background=[("active", c["surface2"])])

        self.log.configure(
            bg=c["log_bg"], fg=c["log_fg"], insertbackground=c["text"],
            selectbackground=c["selection"], selectforeground="#FFFFFF",
            highlightthickness=1, highlightbackground=c["border"], highlightcolor=c["accent"],
        )
        for menu in getattr(self, "_menus", []):
            try:
                menu.configure(bg=c["surface"], fg=c["text"], activebackground=c["accent"], activeforeground="#FFFFFF", bd=0)
            except tk.TclError:
                pass

    def _button_style(self, name: str, bg: str, fg: str) -> None:
        c = self.colors
        self.style.configure(name, background=bg, foreground=fg, bordercolor=bg, relief="flat", padding=(13, 8), font=("Segoe UI", 9, "bold"))
        self.style.map(name, background=[("active", c["accent_hover"]), ("disabled", c["surface2"])], foreground=[("disabled", c["muted"])])

    # ---------- table selection ----------
    def _populate_link_table(self, preserve_selection: bool = False) -> None:
        old = dict(self.link_selection) if preserve_selection else {}
        self.link_tree.delete(*self.link_tree.get_children())
        self.tree_url_by_iid.clear()
        self.link_selection = {}
        for index, url in enumerate(self.links, start=1):
            selected = old.get(url, True)
            self.link_selection[url] = selected
            iid = str(index)
            self.tree_url_by_iid[iid] = url
            self.link_tree.insert("", "end", iid=iid, values=("✓" if selected else "—", filename_hint_from_url(url, index), url))
        self._update_selected_count()

    def _tree_click(self, event) -> None:
        if self.running:
            return
        region = self.link_tree.identify_region(event.x, event.y)
        column = self.link_tree.identify_column(event.x)
        iid = self.link_tree.identify_row(event.y)
        if region == "cell" and column == "#1" and iid:
            url = self.tree_url_by_iid.get(iid)
            if url:
                self.link_selection[url] = not self.link_selection.get(url, True)
                values = list(self.link_tree.item(iid, "values"))
                values[0] = "✓" if self.link_selection[url] else "—"
                self.link_tree.item(iid, values=values)
                self._update_selected_count()
                self._save_last_session()

    def _set_all_selection(self, selected: bool) -> None:
        if self.running:
            return
        for iid, url in self.tree_url_by_iid.items():
            self.link_selection[url] = selected
            values = list(self.link_tree.item(iid, "values"))
            values[0] = "✓" if selected else "—"
            self.link_tree.item(iid, values=values)
        self._update_selected_count()
        self._save_last_session()

    def _invert_selection(self) -> None:
        if self.running:
            return
        for iid, url in self.tree_url_by_iid.items():
            self.link_selection[url] = not self.link_selection.get(url, True)
            values = list(self.link_tree.item(iid, "values"))
            values[0] = "✓" if self.link_selection[url] else "—"
            self.link_tree.item(iid, values=values)
        self._update_selected_count()
        self._save_last_session()

    def _selected_links(self) -> list[str]:
        return [url for url in self.links if self.link_selection.get(url, True)]

    def _update_selected_count(self) -> None:
        count = len(self._selected_links())
        self.count_selected_var.set(str(count))
        if hasattr(self, "download_btn"):
            self.download_btn.configure(state="normal" if (count and not self.running) else "disabled")

    # ---------- inputs ----------
    def _refresh_source_state(self) -> None:
        web = self.source_type.get() == "Página web"
        self.url_entry.configure(state="normal" if web else "disabled")
        self.link_entry.configure(state="disabled" if web else "normal")
        self.link_button.configure(state="disabled" if web else "normal")

    def _choose_link_file(self) -> None:
        path = filedialog.askopenfilename(title="Selecione a lista de links", filetypes=[("Arquivos de texto", "*.txt"), ("Todos", "*.*")])
        if path:
            self.link_file_var.set(path)

    def _choose_output(self) -> None:
        path = filedialog.askdirectory(title="Selecione a pasta de saída")
        if path:
            self.output_var.set(path)

    def _validate_discovery(self) -> tuple[str, str] | None:
        if self.source_type.get() == "Página web":
            url = self.url_var.get().strip()
            if not url.lower().startswith(("http://", "https://")):
                messagebox.showerror("URL inválida", "Informe uma URL começando por http:// ou https://.")
                return None
            return "web", url
        path = self.link_file_var.get().strip()
        if not Path(path).is_file():
            messagebox.showerror("Arquivo inválido", "Selecione um arquivo TXT existente.")
            return None
        return "file", path

    # ---------- discovery/download ----------
    def _start_discovery(self) -> None:
        if self.running:
            return
        valid = self._validate_discovery()
        if not valid:
            return
        source_kind, source = valid
        self.cancel_event.clear()
        self._set_running(True, "discovery")
        self._clear_log()
        self.discovery_result = None
        self.links = []
        self.link_selection = {}
        self._populate_link_table()
        self.count_links_var.set("0")
        self.count_pages_var.set("0")
        self.detected_var.set("—")
        self.download_summary_var.set("Ainda não executado")
        self.notebook.select(self.activity_tab)

        if source_kind == "web":
            options = DiscoveryOptions(
                mode=MODE_LABEL_TO_KEY[self.mode_var.get()],
                max_pages=max(1, int(self.max_pages_var.get())),
                delay=max(0.0, float(self.delay_var.get())),
                same_domain_only=bool(self.same_domain_var.get()),
                respect_robots=bool(self.robots_var.get()),
                crawl_depth=max(0, int(self.crawl_depth_var.get())),
                css_selector=self.selector_var.get().strip(),
                href_regex=self.regex_var.get().strip(),
                probe_ambiguous=bool(self.probe_var.get()),
                probe_timeout=min(max(2, int(self.timeout_var.get())), 30),
                prefer_main_content=bool(self.main_content_var.get()),
                plugin_dir=str(plugin_directory()),
            )
        else:
            options = None

        def worker() -> None:
            try:
                if source_kind == "file":
                    if self.cancel_event.is_set():
                        result = DiscoveryResult(start_urls=[], detected_mode="lista de URLs", cancelled=True)
                    else:
                        links = load_links_from_file(source)
                        result = DiscoveryResult(start_urls=[], download_links=links, visited_pages=[], detected_mode="lista de URLs")
                else:
                    result = discover_links(
                        self.session, [source], options, log=self._qlog, cancel_event=self.cancel_event,
                    )
                self.ui_queue.put(("discovery_done", result))
            except Exception:
                self._qlog(traceback.format_exc())
                self.ui_queue.put(("failed", "Não foi possível concluir a descoberta."))

        threading.Thread(target=worker, daemon=True).start()

    def _discovery_done(self, result: DiscoveryResult) -> None:
        self.discovery_result = result
        self.links = dedupe_preserve_order(result.download_links)
        self.link_selection = {u: True for u in self.links}
        self._populate_link_table(preserve_selection=True)
        self.count_links_var.set(str(len(self.links)))
        self.count_pages_var.set(str(len(result.visited_pages)))
        self.detected_var.set(result.detected_mode or "—")
        self._set_running(False)
        self._save_last_session()
        if result.warnings:
            self._qlog("\nAvisos:\n" + "\n".join(f"- {w}" for w in result.warnings))
        if result.plugins_loaded:
            self._qlog("Plugins carregados: " + ", ".join(result.plugins_loaded))
        if result.probes_performed:
            self._qlog(f"Sondagens HEAD/Content-Type realizadas: {result.probes_performed}")

        if result.cancelled:
            self._qlog(f"\nColeta cancelada. {len(self.links)} arquivo(s) haviam sido encontrados até o cancelamento.")
            if self.links:
                self.notebook.select(self.files_tab)
                messagebox.showinfo("Coleta cancelada", f"A coleta foi cancelada.\n\n{len(self.links)} arquivo(s) encontrados até esse momento foram preservados para revisão.")
            else:
                messagebox.showinfo("Coleta cancelada", "A coleta foi cancelada antes de encontrar arquivos.")
            return

        if self.links:
            self._qlog(f"\nDescoberta concluída: {len(self.links)} arquivo(s) candidato(s).")
            self.notebook.select(self.files_tab)
            messagebox.showinfo(
                "Descoberta concluída",
                f"Foram encontrados {len(self.links)} arquivo(s) candidato(s).\n\nRevise a tabela e desmarque o que não deseja baixar.",
            )
        else:
            if result.robots_blocked:
                messagebox.showwarning(
                    "Coleta não permitida pelo robots.txt",
                    (
                        "O Grabber não analisou a página porque o robots.txt do site "
                        "não autoriza a coleta automática dessa URL.\n\n"
                        "Isso é uma política publicada pelo próprio site, não um erro do programa. "
                        "A opção 'Respeitar robots.txt' permanece habilitada por padrão.\n\n"
                        "Se você tiver autorização ou uma razão legítima para fazer a coleta mesmo assim, "
                        "pode desabilitar manualmente essa opção na aba Configuração e executar novamente."
                    ),
                )
            else:
                messagebox.showwarning(
                    "Nenhum arquivo encontrado",
                    "Nenhum link de arquivo foi reconhecido com a estratégia atual. Tente outro modo, aumente a profundidade, habilite a sondagem ou use um seletor CSS/regex.",
                )

    def _start_download(self) -> None:
        if self.running:
            return
        selected = self._selected_links()
        if not selected:
            messagebox.showinfo("Nenhum arquivo selecionado", "Selecione pelo menos um arquivo na tabela antes de iniciar o download.")
            return
        out_text = self.output_var.get().strip()
        if not out_text:
            messagebox.showerror("Pasta de saída", "Escolha a pasta de saída.")
            return
        out = Path(out_text)
        if not messagebox.askyesno("Iniciar downloads", f"Baixar {len(selected)} arquivo(s) selecionado(s) para:\n{out}\n\nDeseja continuar?"):
            return

        workers = max(1, int(self.workers_var.get()))
        retries = max(1, int(self.retries_var.get()))
        timeout = max(5, int(self.timeout_var.get()))
        self.cancel_event.clear()
        self._set_running(True, "download", total=len(selected))
        self.notebook.select(self.activity_tab)

        def progress(done: int, total: int, result) -> None:
            self.ui_queue.put(("download_progress", (done, total, result)))

        def worker() -> None:
            try:
                results = download_all(
                    self.session, selected, out, workers=workers, retries=retries, timeout=timeout,
                    log=self._qlog, cancel_event=self.cancel_event, progress=progress,
                )
                report = write_report(results, out)
                self.ui_queue.put(("download_done", (results, report)))
            except Exception:
                self._qlog(traceback.format_exc())
                self.ui_queue.put(("failed", "Não foi possível concluir os downloads."))

        threading.Thread(target=worker, daemon=True).start()

    def _download_progress(self, payload) -> None:
        done, total, result = payload
        self.progress.configure(value=done, maximum=max(1, total))
        suffix = f" · {result.status}" if result is not None else ""
        self.progress_text_var.set(f"{done}/{total}{suffix}")

    def _download_done(self, results, report: Path) -> None:
        ok = sum(r.status == "OK" for r in results)
        existed = sum(r.status == "JÁ EXISTIA" for r in results)
        failed = sum(r.status == "FALHOU" for r in results)
        cancelled = sum(r.status == "CANCELADO" for r in results)
        self.download_summary_var.set(f"{ok} novos · {failed} falhas · {cancelled} cancelados")
        self._set_running(False)
        self._save_last_session()
        self._qlog(f"\nRelatório: {report}")
        title = "Downloads cancelados" if cancelled else "Downloads concluídos"
        messagebox.showinfo(
            title,
            f"Novos: {ok}\nJá existiam: {existed}\nFalhas: {failed}\nCancelados: {cancelled}\n\nRelatório: {report}",
        )

    def _cancel_operation(self) -> None:
        if not self.running:
            return
        self.cancel_event.set()
        self.cancel_btn.configure(state="disabled")
        self.progress_text_var.set("Cancelando…")
        self._qlog("[CANCELAMENTO] Solicitação recebida. Aguardando operações em curso encerrarem com segurança…")

    def _operation_failed(self, message: str) -> None:
        self._set_running(False)
        messagebox.showerror("Erro", message + "\nConsulte a aba Atividade para detalhes.")

    # ---------- utility actions ----------
    def _export_links(self) -> None:
        selected = self._selected_links()
        if not selected:
            messagebox.showinfo("Seleção vazia", "Não há arquivos selecionados para exportar.")
            return
        path = filedialog.asksaveasfilename(title="Salvar lista de links", defaultextension=".txt", filetypes=[("Texto", "*.txt")])
        if path:
            Path(path).write_text("\n".join(selected) + "\n", encoding="utf-8")
            messagebox.showinfo("Lista exportada", f"{len(selected)} link(s) salvo(s) em:\n{path}")

    def _open_output(self) -> None:
        path = Path(self.output_var.get().strip())
        path.mkdir(parents=True, exist_ok=True)
        try:
            open_path(path)
        except Exception as exc:
            messagebox.showerror("Erro", f"Não foi possível abrir a pasta:\n{exc}")

    def _set_running(self, active: bool, kind: str = "", total: int = 0) -> None:
        self.running = active
        self.operation_kind = kind if active else ""
        self.discover_btn.configure(state="disabled" if active else "normal")
        self.cancel_btn.configure(state="normal" if active else "disabled")
        self._update_selected_count()

        if active and kind == "download":
            self.progress.stop()
            self.progress.configure(mode="determinate", maximum=max(1, total), value=0)
            self.progress_text_var.set(f"0/{total}")
        elif active:
            self.progress.configure(mode="indeterminate", value=0)
            self.progress.start(10)
            self.progress_text_var.set("Coletando…")
        else:
            self.progress.stop()
            self.progress.configure(mode="determinate", value=0)
            self.progress_text_var.set("Pronto")
            self.cancel_btn.configure(state="disabled")
            self._update_selected_count()

    def _qlog(self, message: str) -> None:
        self.log_queue.put(str(message).rstrip() + "\n")

    def _consume_queues(self) -> None:
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log.configure(state="normal")
                self.log.insert("end", msg)
                self.log.see("end")
                self.log.configure(state="disabled")
        except queue.Empty:
            pass

        try:
            while True:
                kind, payload = self.ui_queue.get_nowait()
                if kind == "discovery_done":
                    self._discovery_done(payload)
                elif kind == "download_progress":
                    self._download_progress(payload)
                elif kind == "download_done":
                    self._download_done(*payload)
                elif kind == "failed":
                    self._operation_failed(str(payload))
        except queue.Empty:
            pass
        self.after(100, self._consume_queues)

    def _clear_log(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def _reset_defaults(self) -> None:
        if not messagebox.askyesno("Restaurar configurações", "Restaurar os parâmetros da interface aos valores padrão?"):
            return
        self.mode_var.set("Automático (recomendado)")
        self.max_pages_var.set(50)
        self.delay_var.set(0.7)
        self.crawl_depth_var.set(0)
        self.same_domain_var.set(True)
        self.robots_var.set(True)
        self.probe_var.set(False)
        self.main_content_var.set(True)
        self.selector_var.set("")
        self.regex_var.set("")
        self.workers_var.set(4)
        self.retries_var.set(3)
        self.timeout_var.set(60)
        self._set_theme("dark")

    def _show_about(self) -> None:
        messagebox.showinfo(
            "Sobre",
            f"{APP_NAME} {APP_VERSION}\n\n"
            "Crawler e downloader portátil para descobrir, revisar e baixar arquivos públicos em massa a partir de diferentes tipos de websites e listas de URLs.\n\n"
            "O modo Automático pode ser ampliado por adaptadores Python confiáveis colocados na pasta plugins/.\n\n"
            "O projeto não tem como objetivo contornar autenticação, CAPTCHA ou mecanismos antibot.",
        )


def main() -> int:
    app = App()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
