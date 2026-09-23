# Matriz de testes do Grabber

Este documento separa **testes automatizados locais** de **validação manual em websites públicos reais**. A distinção é importante: uma fixture local confirma a lógica do programa, mas não reproduz todas as particularidades de servidores, proxies, CDNs e CMS reais.

## Testes automatizados locais

A suíte atual usa um servidor HTTP temporário iniciado durante os testes.

| Cenário | Cobertura | Estado |
|---|---|---|
| Links diretos + paginação `rel=next` | Descoberta de PDF/ZIP em duas páginas | ✅ |
| Crawl interno | Arquivo encontrado em página interna com profundidade 1 | ✅ |
| PhocaDownload | URL com `download=` | ✅ |
| API JSON | URLs aninhadas + paginação simples entre dois endpoints JSON | ✅ |
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
| Foco no conteúdo principal | Ignora links de header/footer quando existe região principal e permite desativar o filtro | ✅ |

Execute:

```bash
python -m unittest discover -s tests -v
```

## Validação manual ainda necessária

Antes da versão 1.0, registrar pelo menos seis cenários em websites públicos reais em que a automação seja permitida:

| Classe | Website testado | Resultado | Observações |
|---|---|---|---|
| Joomla/PhocaDownload | Pendente | ⬜ | |
| HTML com links diretos | IADES | ✅ | 4 de 4 links de arquivos identificados no teste manual |
| Paginação tradicional | Pendente | ⬜ | |
| Crawl depth 1/2 | Pendente | ⬜ | |
| Seletor CSS personalizado | Pendente | ⬜ | |
| Regex personalizada | Pendente | ⬜ | |
| API JSON pública | Pendente | ⬜ | Validar um endpoint público permitido com arquivos e, se possível, paginação |
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


| 23/09/2026 | Instituto Americano de Desenvolvimento (IADES) — links diretos em domínio raiz/`www` | ✅ Descoberta completa | O Grabber identificou 4 arquivos, correspondendo aos 4 links de arquivos existentes na página testada. |
| 23/09/2026 | Edudata — portal com seção documental interna | ✅ Descoberta completa | O Grabber identificou 1 arquivo, correspondendo ao único link de arquivo existente na página testada. |
| 23/09/2026 | Strix Educação — página de evento | ❌ Ainda indisponível | O novo teste realizou três tentativas e todas falharam por conexão. Uma verificação independente da mesma URL também retornou HTTP 502, enquanto páginas de listagem do domínio permaneciam acessíveis. O caso continua pendente e não é tratado como falha de reconhecimento de links. |


| 23/09/2026 | FCM/Unicamp — página de processo seletivo com PDFs diretos | ⚠️ Parcial | Foram encontrados vários PDFs relevantes, mas também apareceram documentos aparentemente alheios ao processo seletivo. O caso motivou o filtro opcional de conteúdo principal introduzido em `0.3.5-dev`; reteste pendente. |
| 23/09/2026 | Vunesp — página de concurso | ❌ HTTP 403 | O servidor respondeu com acesso negado antes que o Grabber pudesse analisar o HTML. O projeto não tenta contornar controles de acesso/antibot; compatibilidade permanece pendente. |
| 23/09/2026 | UnirG — Residência Médica | ⚠️ Over-crawling | O Grabber encontrou os documentos esperados da Residência Médica, mas também muitos arquivos institucionais e de outras áreas do portal. A inspeção da página mostrou conteúdo relevante misturado a navegação global; foi adicionado foco opcional na região principal da página em `0.3.5-dev`. Reteste pendente. |
