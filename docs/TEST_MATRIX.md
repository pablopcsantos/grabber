# Matriz de testes do Grabber

Este documento separa **testes automatizados locais** de **validação manual em websites públicos reais**. A distinção é importante: uma fixture local confirma a lógica do programa, mas não reproduz todas as particularidades de servidores, proxies, CDNs e CMS reais.

## Testes automatizados locais

A suíte atual usa um servidor HTTP temporário iniciado durante os testes.

| Cenário | Cobertura | Estado |
|---|---|---|
| Links diretos + paginação `rel=next` | Descoberta de PDF/ZIP em duas páginas | ✅ |
| Crawl interno | Arquivo encontrado em página interna com profundidade 1 | ✅ |
| PhocaDownload | URL com `download=` | ✅ |
| CSS + regex | Restrição a contêiner e padrão de URL | ✅ |
| HEAD/Content-Type | Link sem extensão identificado como PDF por sondagem | ✅ |
| Plugin externo | Adaptador Python carregado da pasta de plugins | ✅ |
| Cancelamento de descoberta | `Event` interrompe coleta antes de visitar páginas | ✅ |
| Download + relatório | Download paralelo, callback de progresso e CSV | ✅ |
| Cancelamento de downloads | Itens são registrados como `CANCELADO` | ✅ |

Execute:

```bash
python -m unittest discover -s tests -v
```

## Validação manual ainda necessária

Antes da versão 1.0, registrar pelo menos seis cenários em websites públicos reais em que a automação seja permitida:

| Classe | Website testado | Resultado | Observações |
|---|---|---|---|
| Joomla/PhocaDownload | Pendente | ⬜ | |
| HTML com links diretos | Pendente | ⬜ | |
| Paginação tradicional | Pendente | ⬜ | |
| Crawl depth 1/2 | Pendente | ⬜ | |
| Seletor CSS personalizado | Pendente | ⬜ | |
| Regex personalizada | Pendente | ⬜ | |
| Lista manual de URLs | Localmente coberto | ✅ | Não depende do scraper |

## Portabilidade

Também permanecem pendentes testes do executável produzido pelo PyInstaller:

| Ambiente | Estado |
|---|---|
| Windows 10 | ⬜ |
| Windows 11 | ⬜ |
| Máquina sem Python | ⬜ |
| Execução a partir de pendrive | ⬜ |
