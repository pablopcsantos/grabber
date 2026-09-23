# Arquitetura

## Visão geral

O Grabber é separado em camadas para que regras de um website não contaminem o motor de download:

```text
GUI / CLI
   │
   ├── descoberta de links
   │    ├── automático
   │    ├── HTML genérico
   │    ├── Joomla/PhocaDownload
   │    ├── avançado (CSS/regex)
   │    ├── sondagem HEAD/Content-Type
   │    └── plugins externos confiáveis
   │
   ├── revisão dos links
   │    └── seleção/desmarcação antes do download
   │
   └── motor de download HTTP
        ├── retentativas
        ├── concorrência
        ├── cancelamento cooperativo
        ├── progresso determinístico
        ├── nomes de arquivos
        ├── arquivos .part
        └── relatório CSV
```

## `core.py`

Contém o código que não depende da GUI:

- sessão HTTP;
- regras de descoberta;
- crawler por profundidade;
- paginação;
- `robots.txt`;
- normalização de URLs;
- sondagem opcional de links ambíguos;
- integração com adaptadores externos;
- download e cancelamento;
- nomes de arquivos;
- mensagens amigáveis para erros HTTP/rede conhecidos;
- relatório CSV.

## `adapters.py`

Implementa a infraestrutura de plugins. O núcleo procura módulos Python em `plugins/` e exige uma função mínima `match_link(anchor, url, page_url)`.

Plugins podem opcionalmente implementar `find_next_page(soup, page_url)`.

A API está documentada em [`../plugins/README.md`](../plugins/README.md).

> Plugins executam código Python no processo do Grabber. O usuário deve carregar somente plugins confiáveis.

## `app.py`

Interface Tkinter. Coordena:

- configuração;
- descoberta;
- tabela de revisão dos arquivos encontrados;
- seleção do que será baixado;
- cancelamento;
- progresso;
- histórico opcional da última sessão;
- painel de atividade.

A GUI não contém regras específicas de scraping.

## `cli.py`

Expõe as capacidades principais no terminal, incluindo sondagem opcional e carregamento de plugins.

## `plugins/`

Pasta extensível. Em uma instalação portátil, pode existir ao lado de `Grabber.exe`.

## `legacy/eb_downloader.py`

Cópia preservada do script que originou o projeto. Serve apenas como histórico/referência e não é o núcleo da nova aplicação.
