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
- adaptadores Python confiáveis presentes na pasta `plugins/`.

O usuário também pode habilitar uma **sondagem opcional por `HEAD`/`Content-Type`** para botões de download cuja URL não possui extensão ou parâmetro reconhecido. A sondagem fica desativada por padrão porque gera requisições adicionais.

### HTML genérico / links diretos

Procura arquivos em âncoras HTML convencionais, como:

```html
<a href="/documentos/edital.pdf">Baixar edital</a>
```

### Joomla / PhocaDownload

Preserva a compatibilidade com o caso de uso que originou o projeto, reconhecendo links com `?download=...` e paginação comum do Joomla.

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

---

## Rastreamento por profundidade

Por padrão, a ferramenta analisa apenas a página inicial e paginações reconhecidas.

A opção **Profundidade** permite seguir páginas internas no mesmo domínio:

- `0`: somente a página fornecida e sua paginação;
- `1`: também analisa links internos encontrados nela;
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
- APIs JSON ainda sem adaptador;
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

### Histórico opcional

Por padrão, o Grabber não precisa preservar URLs da sessão anterior. Se desejar retomar rapidamente a configuração e a lista descoberta, habilite:

```text
Configurações → Lembrar última sessão
```

Essa opção é voluntária. O histórico pode ser apagado pelo mesmo menu e fica armazenado em `grabber_settings.json` ao lado do executável.

Se nenhum arquivo for encontrado:

1. tente o modo **HTML genérico / links diretos**;
2. aumente a profundidade para `1`;
3. procure no HTML um contêiner apropriado e informe um seletor CSS;
4. utilize uma regex para o padrão das URLs;
5. se os links só surgirem depois de JavaScript, a versão atual provavelmente não é adequada para aquele site.

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

---

## Identidade visual e ícone

O projeto utiliza um ícone próprio. Os arquivos ficam versionados em `assets/`:

```text
assets/
├── grabber.ico
├── grabber.svg
└── grabber.png
```

- `grabber.ico`: usado no executável Windows e na janela do programa;
- `grabber.svg`: arquivo-fonte vetorial preservado no repositório para organização documental e futuras edições;
- `grabber.png`: fallback gráfico de 256×256 px para ambientes em que o `.ico` não seja suportado diretamente pela GUI.

O `.ico` fornecido contém as resoluções 16, 24, 32, 48, 64, 128 e 256 px.

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

O núcleo possui testes de integração locais, sem depender de websites externos. Eles cobrem atualmente **9 cenários**:

- links diretos + paginação;
- rastreamento interno por profundidade;
- adaptador PhocaDownload;
- seletor CSS + regex;
- sondagem `HEAD`/`Content-Type` de link ambíguo;
- plugin externo carregável;
- cancelamento da descoberta;
- download, relatório CSV e callback de progresso;
- cancelamento dos downloads.

Execute com:

```bash
python -m unittest discover -s tests -v
```

O workflow `tests.yml` executa a suíte em Windows e Linux com Python 3.11 e 3.12. A separação entre testes locais e validação manual real está registrada em [`docs/TEST_MATRIX.md`](docs/TEST_MATRIX.md).


---

## Nome do projeto

**Grabber** é o nome definitivo adotado para o projeto.
