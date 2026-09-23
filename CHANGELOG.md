# Changelog

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
