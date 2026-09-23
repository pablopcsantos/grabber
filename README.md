# Grabber

Aplicação desktop portátil para **descobrir e baixar arquivos públicos em massa a partir de websites**, com suporte a diferentes estratégias de descoberta de links e possibilidade de uso por pessoas sem familiaridade com linha de comando.

O projeto nasceu da generalização de um downloader originalmente desenvolvido para páginas Joomla/PhocaDownload. O novo núcleo não depende de um domínio específico e foi reorganizado para funcionar como um **web crawler + bulk file downloader**, usando scraping HTML apenas como uma das formas de localizar os arquivos.

> **Estado atual:** versão de desenvolvimento. O roadmap e os critérios para uma futura versão 1.0 estão em [`ROADMAP.md`](ROADMAP.md).

---

## Objetivo

O programa pretende oferecer uma ferramenta flexível para situações em que um website disponibiliza muitos documentos, imagens, planilhas, arquivos compactados ou outros recursos e o usuário precisa:

- localizar os links automaticamente;
- revisar quantos arquivos foram encontrados;
- salvar a lista de URLs;
- baixar os arquivos em lote;
- retomar downloads sem sobrescrever silenciosamente arquivos já existentes;
- gerar um relatório das transferências.

A ferramenta foi projetada principalmente para **conteúdo público acessível sem login**.

---

## Interface gráfica

A GUI foi desenvolvida em Tkinter com estilo próprio e organização em painéis, evitando depender da aparência clássica padrão do Windows.

Características atuais:

- **modo escuro como padrão**;
- pequenos botões **?** ao lado das configurações menos intuitivas, abrindo explicações contextuais sem sair da tela;
- modo claro selecionável em `Configurações → Aparência`;
- preferência visual salva junto ao executável, para acompanhar o usuário em um pendrive;
- seleção de página web ou arquivo TXT com URLs;
- escolha da estratégia de descoberta;
- configurações de profundidade, limites, domínio e `robots.txt`;
- parâmetros de concorrência, retentativas e timeout;
- descoberta separada do download;
- tabela visual para revisar e desmarcar arquivos antes do download;
- seleção em massa, desmarcação e inversão da seleção;
- cancelamento de coleta e downloads;
- progresso determinístico durante os downloads;
- painel de atividade;
- resumo de links, seleção, páginas e downloads;
- exportação apenas dos links selecionados;
- histórico opcional da última sessão;
- abertura da pasta de saída.

---

## Estratégias de descoberta

### Automático

Modo recomendado para a maioria dos casos. Atualmente combina:

- reconhecimento de Joomla/PhocaDownload;
- links diretos por extensão;
- atributo HTML `download`;
- parâmetros comuns como `download=`, `file=`, `arquivo=`, `attachment=` e semelhantes;
- URLs de arquivos embutidas em visualizadores HTML, quando aparecem em parâmetros como `file=` ou `url=`;
- adaptadores Python confiáveis presentes na pasta `plugins/`.

O modo automático também trata algumas diferenças comuns entre sites reais:

- considera o domínio raiz e sua variante `www.` como o mesmo website para a restrição de domínio;
- pode seguir automaticamente **um nível** de links que parecem levar a seções documentais, como “Edital”, “Documentos”, “Arquivos”, “Resultados”, “Gabaritos” ou “Cronograma”, mesmo quando a profundidade geral está em `0`;
- repete automaticamente a abertura de páginas em falhas transitórias de conexão e em respostas HTTP como 429, 500, 502, 503 e 504.

O usuário também pode habilitar uma **sondagem opcional por `HEAD`/`Content-Type`** para botões de download cuja URL não possui extensão ou parâmetro reconhecido. A sondagem fica desativada por padrão porque gera requisições adicionais.

### HTML genérico / links diretos

Procura arquivos em âncoras HTML convencionais, como:

```html
<a href="/documentos/edital.pdf">Baixar edital</a>
```

### Joomla / PhocaDownload

Preserva a compatibilidade com o caso de uso que originou o projeto, reconhecendo links com `?download=...` e paginação comum do Joomla.

### API JSON

Lê endpoints que retornam JSON e procura recursivamente URLs de arquivos dentro de objetos e listas.

Exemplo conceitual:

```json
{
  "results": [
    {"file": "/documentos/edital.pdf"},
    {"download": "https://exemplo.org/planilhas/dados.xlsx"}
  ],
  "next": "/api/documentos?page=2"
}
```

O Grabber reconhece links diretos por extensão ou parâmetros de download e também trata paginação simples por campos comuns como `next`, `next_url` e `next_page`.

No modo **Automático**, uma resposta cujo `Content-Type` indique JSON também é analisada dessa forma. Para uma URL que você já sabe ser uma API, escolha explicitamente **API JSON**.

> Este suporte é genérico e não substitui integrações específicas quando a API exige autenticação, cabeçalhos proprietários, tokens ou uma estrutura de paginação incomum.

### Avançado: seletor CSS / regex

Permite adaptar sites HTML estáticos sem alterar o código.

Exemplos:

```text
Seletor CSS: #downloads
```

```text
Regex do href: /documentos/.*\.pdf(?:\?.*)?$
```

---

## Plugins de descoberta

O Grabber possui uma infraestrutura de adaptadores externos para sites ou CMS que precisem de uma regra própria.

Na execução pelo código-fonte, os plugins ficam em:

```text
plugins/
```

Na versão portátil, crie a mesma pasta ao lado de `Grabber.exe`.

Um plugin pode reconhecer links de arquivo e, opcionalmente, uma regra de paginação. A API está documentada em [`plugins/README.md`](plugins/README.md).

> **Segurança:** plugins são módulos Python executados no mesmo processo do Grabber. Use somente plugins de fontes confiáveis.

### Integrações externas recomendadas

No momento, **não existe um plugin de terceiros para a API específica do Grabber que tenha sido validado pelo projeto**. Por isso, o README não recomenda baixar adaptadores aleatórios da internet e executá-los como plugins.

A integração externa mais interessante e confiável para uma futura extensão é o **Playwright for Python**, mantido pela Microsoft:

- documentação oficial: https://playwright.dev/python/
- repositório oficial: https://github.com/microsoft/playwright-python

O Playwright automatiza navegadores Chromium, Firefox e WebKit e seria útil para sites em que os links só aparecem após a execução de JavaScript. Ele **não é atualmente um plugin drop-in do Grabber** e ainda não vem incluído no executável portátil, porque exige dependências e binários de navegador adicionais. A intenção é avaliá-lo futuramente como um adaptador opcional, sem aumentar desnecessariamente o tamanho da versão básica do programa.

---

## Rastreamento por profundidade

Por padrão, a ferramenta analisa apenas a página inicial e paginações reconhecidas.

A opção **Profundidade** permite seguir páginas internas no mesmo domínio:

- `0`: a página fornecida, paginações reconhecidas e, no modo Automático, uma navegação conservadora de um nível para seções claramente documentais;
- `1`: também analisa os demais links internos encontrados nela;
- `2+`: continua aprofundando o rastreamento.

Use profundidades maiores com cautela e mantenha um limite de páginas apropriado.

---

## Tipos de website em que tende a funcionar bem

A documentação detalhada está em [`docs/SUPPORTED_SITES.md`](docs/SUPPORTED_SITES.md).

Em resumo, o programa tende a ser útil em:

- páginas HTML com links diretos para arquivos;
- Joomla/PhocaDownload;
- diretórios e páginas de documentos com paginação tradicional;
- sites estáticos em que os arquivos possam ser identificados por seletor CSS;
- sites estáticos em que os links sigam um padrão tratável por regex;
- qualquer caso em que o usuário já possua uma lista TXT de URLs diretas.

---

## Casos em que a ferramenta atual tem pouca utilidade

A versão atual **não é um navegador automatizado completo**.

Pode não funcionar adequadamente em:

- websites cujo conteúdo só aparece após execução de JavaScript;
- páginas que dependem de React/Vue/Angular e não entregam os links no HTML inicial;
- sites com login obrigatório;
- SSO, CSRF, sessões ou cookies especiais;
- URLs assinadas e temporárias;
- sites protegidos por CAPTCHA;
- WAFs ou mecanismos antibot que bloqueiem requisições automatizadas.

O projeto não tem como objetivo contornar autenticação, CAPTCHA ou mecanismos de proteção.

Futuras versões poderão adicionar um navegador automatizado opcional e adaptadores de API.

---

## Uso responsável

A ferramenta deve ser utilizada somente quando o usuário tiver permissão para acessar e automatizar o conteúdo.

Por padrão:

- o rastreamento fica restrito ao mesmo domínio;
- a consulta a `robots.txt` fica habilitada;
- existe uma pausa entre páginas;
- são usados apenas quatro downloads simultâneos.

Quando o `robots.txt` proíbe a coleta de determinada página, o Grabber **não a acessa** enquanto essa opção estiver ativa e apresenta uma mensagem específica explicando o motivo. O usuário pode desabilitar manualmente a opção **Respeitar robots.txt (recomendado)**, mas deve fazê-lo apenas quando tiver autorização ou uma razão legítima para automatizar aquele conteúdo.

O usuário pode ajustar esses valores, mas deve evitar sobrecarregar servidores.

---

## Como executar pelo código-fonte

Recomenda-se Python 3.11 ou superior.

Crie um ambiente virtual:

```bash
python -m venv .venv
```

No Windows:

```bat
.venv\Scripts\activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Execute:

```bash
python app.py
```

---

## Uso básico da GUI

A interface é organizada em três abas: **Configuração**, **Arquivos encontrados** e **Atividade**.

1. Escolha **Página web** ou **Arquivo de links**.
2. Informe a URL inicial ou selecione o TXT.
3. Mantenha **Automático (recomendado)** inicialmente.
4. Escolha a pasta de saída.
5. Clique em **1. Descobrir arquivos**.
6. Acompanhe a coleta na aba **Atividade**.
7. Ao concluir, revise a tabela em **Arquivos encontrados**.
8. Desmarque os itens que não deseja baixar; também é possível selecionar todos, desmarcar todos ou inverter a seleção.
9. Opcionalmente, exporte apenas a seleção atual para TXT.
10. Clique em **2. Baixar selecionados**.
11. A barra de progresso mostra quantos downloads foram concluídos.
12. Se necessário, use **Cancelar operação**; downloads incompletos `.part` são descartados com segurança.
13. Confira `_relatorio_download.csv` na pasta de saída.

### Ajuda contextual na tela

Os campos mais técnicos da aba **Configuração** possuem um pequeno botão **?** ao lado do nome. Clique nele para abrir uma explicação curta sobre:

- modo de descoberta;
- profundidade;
- limite máximo de páginas;
- restrição ao mesmo domínio;
- `robots.txt`;
- sondagem `HEAD`/`Content-Type`;
- pausa entre páginas;
- seletor CSS;
- regex do `href`;
- downloads simultâneos;
- tentativas;
- timeout.

Essas janelas também indicam valores usuais, situações em que o campo deve ser alterado e quando é melhor deixar o valor padrão.

### Histórico opcional

Por padrão, o Grabber não precisa preservar URLs da sessão anterior. Se desejar retomar rapidamente a configuração e a lista descoberta, habilite:

```text
Configurações → Lembrar última sessão
```

Essa opção é voluntária. O histórico pode ser apagado pelo mesmo menu e fica armazenado em `grabber_settings.json` ao lado do executável.

Se nenhum arquivo for encontrado:

1. confira o painel **Atividade** para saber se houve bloqueio por `robots.txt`, falha de conexão ou resposta HTTP;
2. tente o modo **HTML genérico / links diretos**;
3. aumente a profundidade para `1`;
4. procure no HTML um contêiner apropriado e informe um seletor CSS;
5. utilize uma regex para o padrão das URLs;
6. habilite a sondagem de links ambíguos quando houver botões de download sem extensão;
7. se os links só surgirem depois de JavaScript, a versão atual provavelmente não é adequada para aquele site.

---

## Lista manual de URLs

Também é possível ignorar totalmente o web scraper.

Crie um arquivo, por exemplo `links.txt`:

```text
https://exemplo.org/documentos/a.pdf
https://exemplo.org/documentos/b.zip
https://outro.exemplo.org/arquivo.xlsx
```

Na GUI, selecione **Arquivo de links**.

Esse modo usa apenas o motor genérico de download.

---

## Arquivos gerados

Os downloads são armazenados na pasta escolhida pelo usuário.

O relatório:

```text
_relatorio_download.csv
```

contém:

- URL;
- nome do arquivo;
- status;
- tamanho em bytes;
- mensagem de erro, quando houver.

Downloads incompletos utilizam temporariamente a extensão:

```text
.part
```

O arquivo temporário só é renomeado para o nome final depois da conclusão da transferência.

---

## Nomes de arquivos

A ferramenta tenta descobrir o nome nesta ordem geral:

1. cabeçalho HTTP `Content-Disposition`;
2. nome existente no caminho da URL;
3. parâmetros comuns da query string;
4. nome genérico numerado + extensão inferida pelo `Content-Type`.

Diferentemente da versão original específica para documentos do Exército, o fallback atual **não presume que todo arquivo seja PDF**.

Alguns sites abrem documentos por meio de uma página visualizadora, por exemplo:

```text
/viewer/index.html?file=https%3A%2F%2Fsite.exemplo%2Fdocumento.pdf
```

Quando o parâmetro contém uma URL que aponta claramente para um tipo de arquivo reconhecido, o Grabber usa a URL direta do documento em vez da página do visualizador.

---

## Retomada e arquivos repetidos

Se um arquivo com o mesmo nome já existir e o servidor informar o mesmo `Content-Length`, o download é marcado como:

```text
JÁ EXISTIA
```

Se o nome já estiver ocupado mas o tamanho não corresponder, é criado um nome único:

```text
arquivo.pdf
arquivo (1).pdf
arquivo (2).pdf
```

---

## CLI

O projeto preserva uma interface por terminal para automação e diagnóstico.

Exemplo:

```bash
python cli.py --url "https://exemplo.org/documentos" --output ./downloads
```

Modo específico PhocaDownload:

```bash
python cli.py --url "URL" --mode phocadownload
```

Crawler interno com profundidade 1:

```bash
python cli.py --url "URL" --crawl-depth 1 --max-pages 100
```

Seletor CSS e regex:

```bash
python cli.py \
  --url "URL" \
  --mode advanced \
  --css-selector ".documentos" \
  --href-regex "\\.pdf(?:\\?.*)?$"
```

Sondagem de links ambíguos:

```bash
python cli.py --url "URL" --probe-ambiguous --dry-run
```

Plugins externos no modo automático:

```bash
python cli.py --url "URL" --plugins-dir ./plugins --dry-run
```

Endpoint de API JSON:

```bash
python cli.py --url "https://exemplo.org/api/documentos" --mode api-json --dry-run
```

---

## Versão portátil para pendrive

O projeto está preparado para gerar um único executável Windows com PyInstaller:

```text
Grabber.exe
```

Na máquina de desenvolvimento, execute:

```text
build_windows.bat
```

O resultado será criado em:

```text
dist\Grabber.exe
```

O executável pode ser copiado para um pendrive e executado sem instalação de Python na máquina de destino.

As preferências simples da interface, como o tema, são armazenadas no arquivo:

```text
grabber_settings.json
```

junto ao executável. Isso foi escolhido deliberadamente para preservar o comportamento portátil.

O repositório também contém um workflow do GitHub Actions para compilar o executável em Windows.

---

## Estrutura do projeto

```text
Grabber/
├── .github/
│   └── workflows/
│       ├── build-windows.yml
│       └── tests.yml
├── assets/
│   ├── grabber.ico
│   ├── grabber.svg
│   ├── grabber.png
│   └── README.md
├── plugins/
│   ├── README.md
│   └── example_adapter.py.example
├── tests/
│   └── test_core.py
├── docs/
│   ├── ARCHITECTURE.md
│   ├── SUPPORTED_SITES.md
│   └── TEST_MATRIX.md
├── legacy/
│   └── eb_downloader.py
├── app.py
├── adapters.py
├── core.py
├── cli.py
├── ROADMAP.md
├── CHANGELOG.md
├── README.md
├── requirements.txt
├── requirements-build.txt
├── build_windows.bat
└── .gitignore
```

---

## Arquitetura

A separação principal é:

- `core.py`: descoberta, sondagem, cancelamento e download;
- `adapters.py`: carregamento seguro da API estrutural de plugins (a confiança no código do plugin continua sendo responsabilidade do usuário);
- `app.py`: GUI, revisão da seleção, progresso e histórico opcional;
- `cli.py`: terminal;
- `legacy/eb_downloader.py`: script original preservado apenas para referência histórica.

Detalhes estão em [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Roadmap

Os marcos de desenvolvimento e critérios objetivos para considerar a versão 1.0 pronta estão documentados em:

[`ROADMAP.md`](ROADMAP.md)

As funcionalidades planejadas para os Marcos 1, 2 e 3 já estão implementadas. Os itens que mais pesam para a versão 1.0 agora são de **validação externa**:

- testes documentados em websites públicos reais de diferentes classes;
- testes do executável em Windows 10 e Windows 11;
- execução em máquina sem Python instalado;
- execução a partir de pendrive;
- correções que surgirem a partir desses testes.

Recursos como Playwright, APIs JSON, autenticação e URLs assinadas permanecem planejados para versões posteriores e não bloqueiam a 1.0.

---

## Tecnologias

- Python 3;
- Tkinter / ttk;
- Requests;
- Beautiful Soup 4;
- PyInstaller;
- GitHub Actions.

---

## Testes automatizados

O núcleo possui testes de integração locais, sem depender de websites externos. Eles cobrem atualmente **15 cenários**:

- links diretos + paginação;
- equivalência entre domínio raiz e variante `www.`;
- navegação automática para uma seção documental em profundidade `0`;
- repetição de abertura após falhas HTTP transitórias;
- rastreamento interno por profundidade;
- adaptador PhocaDownload;
- descoberta recursiva e paginação simples em API JSON;
- seletor CSS + regex;
- sondagem `HEAD`/`Content-Type` de link ambíguo;
- plugin externo carregável;
- URL de arquivo embutida em visualizador;
- respeito e registro de bloqueio por `robots.txt`;
- cancelamento da descoberta;
- download, relatório CSV e callback de progresso;
- cancelamento dos downloads.

Execute com:

```bash
python -m unittest discover -s tests -v
```

O workflow `tests.yml` executa a suíte em Windows e Linux com Python 3.11 e 3.12. A separação entre testes locais e validação manual real está registrada em [`docs/TEST_MATRIX.md`](docs/TEST_MATRIX.md).
