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
| URL embutida em visualizador | Extrai o arquivo real de parâmetros como `file=` | ✅ |
| robots.txt | Bloqueio é respeitado e registrado no resultado | ✅ |
| Cancelamento de descoberta | `Event` interrompe coleta antes de visitar páginas | ✅ |
| Download + relatório | Download paralelo, callback de progresso e CSV | ✅ |
| Cancelamento de downloads | Itens são registrados como `CANCELADO` | ✅ |
| Domínio raiz + `www` | A restrição de mesmo site aceita as duas variantes do mesmo host | ✅ |
| Navegação documental inteligente | Modo Automático segue uma seção “Edital” mesmo com profundidade 0 | ✅ |
| Retentativa de página | Servidor retorna 503 duas vezes e a terceira tentativa é processada | ✅ |

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


## Testes manuais em websites reais

| Data | Website/classe | Resultado | Observações |
|---|---|---|---|
| 23/09/2026 | Fundação Carlos Chagas (FCC) — HTML com links de documentos e visualizador intermediário | Parcial | Com `robots.txt` habilitado, a página `concursos/alems125/index.html` foi corretamente ignorada porque a política do site não permitiu a coleta. A estrutura pública da página utiliza, em alguns documentos, um visualizador com a URL real do PDF no parâmetro `file=`. O suporte a esse padrão foi adicionado em `0.3.1-dev`. Não contabilizado ainda como teste real concluído de download. |


| 23/09/2026 | Instituto Americano de Desenvolvimento (IADES) — links diretos em domínio raiz/`www` | Diagnóstico/correção | A página contém PDFs em `www.iades.com.br`, enquanto a URL testada usa `iades.com.br`. A equivalência raiz/`www` foi implementada em `0.3.2-dev`. Pendente reteste manual. |
| 23/09/2026 | Edudata — portal com seção documental interna | Diagnóstico/correção | O portal inicial possui link interno **Edital**; o PDF aparece nessa subpágina. A navegação automática de uma etapa para seções documentais foi implementada em `0.3.2-dev`. Pendente reteste manual. |
| 23/09/2026 | Strix Educação — página de evento | Parcial | A URL falhou por conexão no Grabber e uma verificação independente também encontrou erro de gateway. Foram adicionadas retentativas automáticas para falhas transitórias. Pendente reteste. |
