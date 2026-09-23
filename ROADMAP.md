# Roadmap e critérios de conclusão

Este arquivo registra os objetivos práticos do **Grabber**. Ele serve para evitar que o desenvolvimento se torne uma sequência indefinida de funcionalidades sem um critério claro de maturidade.

## Objetivo geral

Construir uma aplicação desktop portátil capaz de **descobrir, revisar e baixar arquivos públicos em massa** a partir de diferentes tipos de websites, sem ficar acoplada a um domínio ou CMS específico.

A ferramenta deve continuar simples para usuários leigos, mas oferecer opções avançadas para sites HTML que exijam regras próprias de descoberta.

---

## Marco 1 — Núcleo genérico de download ✅

Critérios:

- [x] downloads HTTP/HTTPS com `requests`;
- [x] downloads paralelos;
- [x] retentativas e timeout configuráveis;
- [x] nomes por `Content-Disposition` quando disponíveis;
- [x] fallback por URL e `Content-Type`;
- [x] arquivos temporários `.part` antes da conclusão;
- [x] não sobrescrever silenciosamente arquivos existentes;
- [x] relatório CSV final;
- [x] lista de URLs em TXT como fonte independente do scraper;
- [x] cancelamento cooperativo de downloads em andamento;
- [x] erros HTTP comuns apresentados com mensagens mais compreensíveis.

**Estado:** funcional.

---

## Marco 2 — Descoberta flexível de arquivos ✅

Critérios:

- [x] modo automático;
- [x] adaptador Joomla/PhocaDownload;
- [x] reconhecimento de links diretos por extensão;
- [x] reconhecimento de atributo HTML `download`;
- [x] reconhecimento de parâmetros comuns de download na query string;
- [x] seletor CSS configurável;
- [x] regex configurável para `href`;
- [x] paginação por `rel="next"` e rótulos comuns;
- [x] rastreamento interno por profundidade configurável;
- [x] opção de limitar ao mesmo domínio;
- [x] opção de respeitar `robots.txt`;
- [x] sondagem opcional de links ambíguos por `HEAD`/`Content-Type`, com fallback controlado para `GET` quando `HEAD` não é aceito;
- [x] sistema formal de adaptadores/plugins carregáveis no modo Automático;
- [x] equivalência entre domínio raiz e variante `www.` na restrição de mesmo site;
- [x] navegação automática conservadora para seções documentais em profundidade `0`;
- [x] novas tentativas automáticas para falhas transitórias de conexão/HTTP durante a descoberta.

**Estado:** concluído para a meta da versão 1.0 em websites HTML estáticos.

Os plugins ficam na pasta `plugins/` e possuem uma API mínima documentada em [`plugins/README.md`](plugins/README.md). Plugins são código Python e devem ser usados somente quando forem confiáveis.

---

## Marco 3 — GUI portátil ✅

Critérios:

- [x] GUI desktop;
- [x] design moderno baseado em painéis, abas e espaçamento consistente;
- [x] modo escuro como padrão;
- [x] modo claro selecionável pelo menu;
- [x] preferência de tema salva junto ao executável para acompanhar o pendrive;
- [x] descoberta separada do download;
- [x] painel de atividade/log;
- [x] resumo de páginas, links e downloads;
- [x] exportação da lista de URLs descobertas;
- [x] configurações básicas e avançadas pela interface;
- [x] tabela visual dos arquivos antes do download, com possibilidade de desmarcar itens;
- [x] botão de cancelar uma coleta/download em andamento;
- [x] indicador de progresso determinístico durante downloads;
- [x] histórico opcional da última sessão.

**Estado:** funcionalidades planejadas para a GUI 1.0 implementadas. Ainda requer testes de usabilidade em Windows real.

### Observações sobre histórico

O histórico da última sessão é **opt-in**. O usuário pode habilitar `Configurações → Lembrar última sessão`. Quando desabilitado, a sessão anterior não é mantida. Como o Grabber é portátil, o arquivo de preferências fica ao lado do executável.

---

## Marco 4 — Portabilidade Windows ✅ / pendente de validação em máquinas reais

Critérios:

- [x] configuração para PyInstaller `--onefile --windowed`;
- [x] `build_windows.bat`;
- [x] workflow GitHub Actions em Windows;
- [x] configurações armazenadas ao lado do executável, adequadas ao uso em pendrive;
- [x] nome definitivo **Grabber** e ícone próprio do programa;
- [ ] execução testada em Windows 10;
- [ ] execução testada em Windows 11;
- [ ] teste a partir de pendrive/unidade removível;
- [ ] verificar comportamento sem Python instalado na máquina de destino.

**Observação:** esses quatro itens exigem execução em ambientes Windows reais e não são considerados concluídos apenas por testes de código em Linux/CI.

---

## Marco 5 — Compatibilidade por classes de websites

Antes da primeira versão estável, o projeto deve ser testado em websites públicos reais representativos de:

- [ ] Joomla/PhocaDownload;
- [ ] página HTML com links diretos para PDF/DOC/ZIP — FCC analisada parcialmente; `robots.txt` bloqueou a coleta padrão, portanto ainda não conta como cenário concluído;
- [ ] site com paginação tradicional;
- [ ] site em que arquivos aparecem em páginas internas (`crawl depth` 1 ou 2);
- [ ] site que exige seletor CSS personalizado;
- [ ] site que exige regex personalizada;
- [x] lista manual de URLs — comportamento coberto por testes locais e pelo motor independente do scraper.

### Cobertura automatizada local já existente

Os cenários abaixo possuem testes de integração locais e não dependem de websites externos:

- [x] HTML genérico + paginação;
- [x] crawl por profundidade;
- [x] PhocaDownload;
- [x] seletor CSS + regex;
- [x] sondagem HEAD/Content-Type de URL ambígua;
- [x] plugin externo carregável;
- [x] cancelamento de descoberta;
- [x] download + relatório + progresso determinístico;
- [x] cancelamento de downloads;
- [x] equivalência de domínio raiz/`www`;
- [x] navegação automática para seção documental;
- [x] repetição de página em falha transitória.

Os resultados estão resumidos em [`docs/TEST_MATRIX.md`](docs/TEST_MATRIX.md).

**Importante:** os testes locais acima não substituem os testes manuais em websites públicos reais previstos para a versão 1.0.

---

## Marco 6 — Casos modernos/difíceis

Estes recursos não são necessários para a primeira versão estável, mas definem o caminho para versões posteriores:

- [ ] websites renderizados por JavaScript com navegador automatizado opcional (ex.: Playwright);
- [ ] adaptadores nativos para APIs JSON;
- [ ] autenticação/cookies importados de forma explícita pelo usuário;
- [ ] URLs assinadas ou temporárias;
- [ ] filas e perfis de coleta reutilizáveis;
- [x] plugins externos por site/CMS — infraestrutura inicial disponível; plugins específicos serão adicionados conforme necessidade.

**Não é meta:** contornar CAPTCHA, mecanismos antibot ou controles de acesso.

---

## Critérios para considerar a versão 1.0 pronta

A versão 1.0 poderá ser considerada concluída quando:

1. [x] os Marcos 1 e 2 estiverem completos para websites HTML estáticos;
2. [x] a GUI permitir selecionar, revisar e baixar os arquivos sem terminal;
3. [x] o usuário puder cancelar operações em andamento;
4. [ ] o executável portátil tiver sido testado em Windows 10/11 e em unidade removível;
5. [ ] pelo menos seis cenários de website do Marco 5 tiverem testes **reais** documentados;
6. [x] README e documentação técnica estiverem atualizados para as funcionalidades já implementadas;
7. [x] erros comuns de HTTP/rede e respostas HTML inesperadas forem convertidos em mensagens compreensíveis sempre que o motor conseguir identificá-los;
8. [x] o projeto não depender de regras específicas do site do Exército Brasileiro para funcionar.

A integração com sites JavaScript-heavy, login ou APIs específicas poderá ficar para versões posteriores sem impedir a versão 1.0.

---

## Próxima etapa recomendada

O desenvolvimento funcional necessário à primeira versão estável está próximo de concluir-se. As próximas atividades devem privilegiar **validação externa**, não a adição indiscriminada de recursos:

1. gerar `Grabber.exe` em Windows;
2. testar Windows 10 e Windows 11 sem Python instalado;
3. executar a partir de pendrive;
4. selecionar websites públicos permitidos que representem as classes do Marco 5;
5. registrar os resultados e eventuais ajustes em `docs/SUPPORTED_SITES.md` e `docs/TEST_MATRIX.md`.
