# Plugins de descoberta do Grabber

O modo **Automático** pode carregar adaptadores externos colocados nesta pasta. Isso permite adicionar regras para um CMS ou website sem editar `core.py`.

> Plugins são código Python executado dentro do Grabber. Use somente arquivos de fontes confiáveis.

## Contrato mínimo

Crie um arquivo `meu_adapter.py` com:

```python
ADAPTER_NAME = "Meu CMS"


def match_link(anchor, url: str, page_url: str) -> bool:
    """Retorne True quando `url` representar um arquivo para download."""
    return "/meu-cms/arquivo/" in url
```

Opcionalmente, o plugin pode reconhecer a paginação:

```python
def find_next_page(soup, page_url: str) -> str | None:
    link = soup.select_one("a.proxima-pagina")
    return link.get("href") if link else None
```

O Grabber resolve URLs relativas retornadas por `find_next_page` em relação à página atual.

## Onde colocar no executável portátil

Crie uma pasta `plugins` ao lado de `Grabber.exe`:

```text
Grabber.exe
plugins/
└── meu_adapter.py
```

Na execução pelo código-fonte, a pasta `plugins/` do próprio projeto é utilizada.
