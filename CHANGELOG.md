# Changelog

## 0.3.2-dev

- domínio raiz e variante `www.` passam a ser tratados como o mesmo site na restrição de domínio;
- modo Automático ganha navegação conservadora de um nível para seções documentais como Edital, Documentos, Arquivos, Resultados, Gabaritos e Cronograma;
- descoberta passa a repetir falhas transitórias de conexão, timeout, HTTP 429 e HTTP 500/502/503/504;
- mensagens de falha agora informam quantas tentativas foram realizadas;
- novos testes de regressão para equivalência `www`, navegação documental automática e retentativa após HTTP 503;
- documentação dos testes reais/diagnósticos em IADES, Edudata e Strix Educação.

## 0.3.1-dev

- mensagem específica na GUI quando uma coleta é bloqueada por `robots.txt`;
- rótulo da opção alterado para **Respeitar robots.txt (recomendado)**;
- registro explícito das URLs bloqueadas por `robots.txt` no resultado da descoberta;
- suporte a links de visualizadores que carregam o arquivo real em parâmetros como `file=`/`url=`;
- teste automatizado para URL de arquivo embutida em visualizador;
- teste automatizado para bloqueio por `robots.txt`;
- documentação do teste manual com a Fundação Carlos Chagas (FCC).

## 0.3.0-dev

### Adicionado

- tabela de revisão dos arquivos descobertos antes do download;
- seleção individual, selecionar todos, desmarcar todos e inverter seleção;
- cancelamento cooperativo da descoberta e dos downloads;
- progresso determinístico dos downloads;
- histórico opcional da última sessão;
- sondagem opcional de links ambíguos por `HEAD`/`Content-Type`;
- fallback controlado para `GET` quando `HEAD` não é aceito;
- infraestrutura de plugins externos para descoberta e paginação;
- documentação da API de plugins;
- mensagens mais compreensíveis para erros HTTP/rede comuns;
- matriz de testes separando fixtures locais de validação real.

### Alterado

- GUI reorganizada em abas **Configuração**, **Arquivos encontrados** e **Atividade**;
- download passa a usar apenas os itens selecionados;
- exportação da lista usa a seleção atual;
- README, arquitetura, compatibilidade e roadmap atualizados.

### Testes

- suíte ampliada de 5 para 9 testes de integração locais.

## 0.2.1-dev

- adoção do nome **Grabber**;
- incorporação do ícone próprio;
- modos claro e escuro;
- descoberta genérica, PhocaDownload, CSS/regex e crawl por profundidade;
- preparação para build portátil no Windows.
