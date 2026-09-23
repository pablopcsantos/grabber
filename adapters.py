from __future__ import annotations

"""API leve para adaptadores externos do Grabber.

Plugins são módulos Python colocados na pasta ``plugins`` ao lado do executável.
Eles são carregados apenas no modo Automático. Como código Python é executado no
processo do Grabber, use somente plugins de fontes confiáveis.
"""

import importlib.util
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Callable


LogFn = Callable[[str], None]


@dataclass
class ExternalAdapter:
    name: str
    module: ModuleType

    def matches(self, anchor: Any, url: str, page_url: str) -> bool:
        return bool(self.module.match_link(anchor, url, page_url))

    def next_page(self, soup: Any, page_url: str) -> str | None:
        func = getattr(self.module, "find_next_page", None)
        if not callable(func):
            return None
        value = func(soup, page_url)
        return str(value).strip() if value else None


def load_external_adapters(
    plugin_dir: str | Path | None,
    log: LogFn | None = None,
) -> tuple[list[ExternalAdapter], list[str]]:
    """Carrega plugins ``*.py`` que exponham ``match_link``.

    Contrato mínimo de plugin::

        ADAPTER_NAME = "Meu CMS"

        def match_link(anchor, url: str, page_url: str) -> bool:
            ...

    Opcionalmente o plugin pode expor::

        def find_next_page(soup, page_url: str) -> str | None:
            ...
    """

    logger = log or (lambda _msg: None)
    adapters: list[ExternalAdapter] = []
    warnings: list[str] = []
    if not plugin_dir:
        return adapters, warnings

    directory = Path(plugin_dir)
    if not directory.is_dir():
        return adapters, warnings

    for path in sorted(directory.glob("*.py")):
        if path.name.startswith("_"):
            continue
        module_name = f"grabber_plugin_{path.stem}_{abs(hash(path.resolve()))}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec is None or spec.loader is None:
                raise RuntimeError("não foi possível criar o loader")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            matcher = getattr(module, "match_link", None)
            if not callable(matcher):
                raise RuntimeError("o plugin não expõe a função match_link(anchor, url, page_url)")
            name = str(getattr(module, "ADAPTER_NAME", path.stem)).strip() or path.stem
            adapters.append(ExternalAdapter(name=name, module=module))
            logger(f"[PLUGIN] Adaptador carregado: {name}")
        except Exception as exc:
            message = f"Falha ao carregar plugin {path.name}: {exc}"
            warnings.append(message)
            logger(f"[AVISO] {message}")

    return adapters, warnings
