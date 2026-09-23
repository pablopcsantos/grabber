# Compatibilidade com websites

O Grabber é um **crawler/downloader de arquivos**, não um navegador completo. Sua utilidade depende da forma como cada website expõe os arquivos.

## Excelente compatibilidade

### Páginas HTML com links diretos

Exemplos conceituais:

```html
<a href="/documentos/edital.pdf">Edital</a>
<a href="/downloads/planilha.xlsx">Planilha</a>
```

Esses casos costumam funcionar diretamente no modo **Automático** ou **HTML genérico / links diretos**.

### Joomla / PhocaDownload

O comportamento do antigo EB Downloader foi preservado como regra nativa. Links com `?download=...` são reconhecidos e a paginação comum do Joomla também é tratada.

### Sites estáticos com links dentro de uma área específica

Se apenas determinada seção contém os arquivos, o modo avançado aceita um seletor CSS, por exemplo:

```text
#downloads
.document-list
main article
```

### Sites estáticos com padrão reconhecível na URL

Uma regex pode filtrar os `href`, por exemplo:

```regex
/downloads/.*\.pdf(?:\?.*)?$
```

### APIs JSON públicas

O modo **API JSON** pode localizar arquivos em endpoints públicos que retornem URLs em objetos ou listas JSON. A busca é recursiva e não depende do nome exato do campo.

Também há suporte inicial a paginação simples por campos como:

```text
next
next_url
next_page
```

Esse modo funciona melhor quando os valores retornados já contêm URLs diretas ou caminhos relativos para arquivos reconhecíveis.

### Lista pronta de URLs

Quando os links diretos já são conhecidos, o scraper pode ser ignorado completamente. Um TXT com uma URL por linha utiliza apenas o motor genérico de download.

---

## Compatibilidade intermediária

### Links de download sem extensão

Quando um botão visivelmente representa um download, mas a URL não possui extensão ou parâmetro conhecido, o usuário pode habilitar:

```text
Sondar links ambíguos (HEAD/Content-Type)
```

O Grabber tenta primeiro `HEAD`. Se o servidor não aceitar esse método, pode realizar um `GET` em modo `stream` apenas para inspecionar cabeçalhos. Essa opção gera tráfego adicional e por isso fica desabilitada por padrão.

### Sites com páginas internas antes do arquivo

É possível aumentar a **profundidade de rastreamento** para seguir páginas internas no mesmo domínio. Deve-se usar limites conservadores de páginas para evitar percorrer áreas desnecessárias do site.

### Foco no conteúdo principal

No modo **Automático**, o Grabber tenta priorizar regiões semânticas como `<main>`, `<article>` e contêineres de conteúdo comuns. O objetivo é evitar que arquivos presentes em menus, rodapés e áreas globais do portal sejam misturados aos documentos da página consultada.

A opção **Priorizar conteúdo principal** fica habilitada por padrão. Se um site realmente mantiver os arquivos fora da região central, ela pode ser desativada. Na CLI, use `--scan-whole-page`.

### Paginações incomuns

A ferramenta reconhece `rel="next"` e vários rótulos comuns. Se um CMS tiver regras próprias, um plugin externo pode acrescentar `find_next_page` sem alterar o núcleo.

### CMS ou sites com padrão próprio

A pasta `plugins/` permite carregar adaptadores Python no modo Automático. Um plugin pode reconhecer links específicos e, opcionalmente, paginação.

> Plugins executam código no processo do Grabber. Use somente plugins de fontes confiáveis.

---

## Baixa compatibilidade ou necessidade de outro adaptador

### Websites renderizados principalmente por JavaScript

Se os links só aparecem depois da execução de JavaScript no navegador, `requests + BeautifulSoup` pode receber HTML incompleto.

Possíveis evoluções futuras:

- Playwright;
- Selenium;
- identificação da API JSON usada pelo próprio site.

Esses recursos ainda não fazem parte do núcleo atual.

### APIs JSON complexas ou autenticadas

O suporte genérico atual cobre endpoints públicos com URLs de arquivos em objetos/listas e paginação simples. APIs que exigem autenticação, tokens, cabeçalhos proprietários, GraphQL, POST obrigatório ou esquemas de paginação específicos ainda podem exigir um adaptador dedicado.

### Websites com login

O projeto atual não implementa um fluxo genérico de autenticação. Sites que exigem sessão, SSO, token, CSRF ou cookies específicos necessitam integração própria e autorização de acesso.

### URLs assinadas/temporárias

Sites que geram links com validade curta podem exigir que a URL seja obtida imediatamente antes do download.

### CAPTCHA e proteção antibot

O projeto **não foi concebido para contornar** CAPTCHA, desafios de navegador, WAF ou outros mecanismos de proteção. Caso a automação não seja permitida ou seja bloqueada, o usuário deve utilizar os mecanismos fornecidos pelo próprio site.

---

## Princípios de uso responsável

- utilize apenas recursos que você tenha permissão para acessar;
- respeite termos de uso e políticas do website;
- mantenha `robots.txt` habilitado quando aplicável;
- use poucos downloads simultâneos em servidores pequenos;
- evite rastreamento profundo sem necessidade;
- habilite a sondagem HEAD apenas quando ela for necessária;
- não utilize a ferramenta para contornar autenticação ou controles de acesso;
- downloads em massa podem gerar carga significativa: ajuste `delay`, `workers` e limites de páginas.

---

## Estado da validação

A lógica dessas classes possui testes automatizados locais. Testes em websites públicos reais e os resultados específicos de cada classe serão registrados em [`TEST_MATRIX.md`](TEST_MATRIX.md) antes da versão 1.0.


---

## Caso real observado: Fundação Carlos Chagas (FCC)

Em um teste manual realizado em **23/09/2026** com a página:

```text
https://www.concursosfcc.com.br/concursos/alems125/index.html
```

o Grabber, com a configuração padrão, interrompeu a coleta porque o `robots.txt` do site não autorizou aquela URL. Esse comportamento é esperado quando **Respeitar robots.txt (recomendado)** está habilitado.

A página possui uma seção pública de **Links e Arquivos**, mas vários documentos são apresentados por um visualizador intermediário. Um padrão observado é conceitualmente semelhante a:

```text
/rybena/web/index.html?file=https://www.concursosfcc.com.br/.../documento.pdf
```

A partir da versão `0.3.1-dev`, o Grabber reconhece esse padrão de URL embutida e extrai o endereço direto do documento quando ele possui extensão de arquivo conhecida.

**Estado do teste:** parcial. A estrutura da página e o bloqueio por `robots.txt` foram observados, mas não foi registrado como teste de download bem-sucedido porque, com a política padrão, a coleta foi corretamente interrompida.


---

## Casos reais observados: IADES, Edudata e Strix

### IADES

Teste informado em **23/09/2026**:

```text
https://iades.com.br/inscricao/ProcessoSeletivo.aspx?id=a4918d948c
```

A página expõe documentos em PDF, mas os links utilizam a variante `www.iades.com.br` enquanto a URL inicial pode ser aberta em `iades.com.br`.

Antes da versão `0.3.2-dev`, a opção de mesmo domínio tratava essas duas formas como hosts diferentes e podia descartar os PDFs.

A partir de `0.3.2-dev`, o Grabber considera o domínio raiz e sua variante `www.` equivalentes para a restrição de mesmo site.

**Estado:** descoberta manual completa no teste mais recente: 4 arquivos encontrados, correspondendo aos 4 links de arquivo existentes na página testada.

### Edudata

Teste informado em **23/09/2026**:

```text
https://www.edudata.com.br/sabara27/sabara27_portal.asp
```

A página inicial funciona como portal e não apresenta necessariamente o PDF diretamente. A seção **Edital** fica em uma página interna, por exemplo:

```text
sabara27_portal.asp?p=edit
```

e nela existe o link para o edital em PDF.

A partir de `0.3.2-dev`, o modo Automático pode seguir, mesmo com profundidade `0`, um único nível de links que pareçam claramente seções documentais, como **Edital**, **Documentos**, **Arquivos**, **Resultados**, **Gabaritos** e **Cronograma**.

**Estado:** descoberta manual completa no teste mais recente: 1 arquivo encontrado, correspondendo ao único link de arquivo existente na página testada.

### Strix Educação

Teste informado em **23/09/2026**:

```text
https://strixeducacao.com.br/evento/unit-processo-seletivo-unificado-de-medicina-2027-1-aracaju-se-e-goiana-pe/
```

O Grabber recebeu falha de conexão ao abrir a página. Uma verificação independente da mesma URL também encontrou falha de gateway, enquanto páginas de listagem do mesmo domínio e eventos anteriores estavam acessíveis.

Isso sugere que o problema pode ser transitório ou específico da infraestrutura/rota dessa página, e não necessariamente uma falha da descoberta HTML.

A partir de `0.3.2-dev`, a descoberta repete automaticamente falhas de conexão, timeout, HTTP 429 e erros HTTP 500/502/503/504 com pequeno intervalo progressivo.

**Estado:** no novo teste, as três tentativas do Grabber falharam por conexão. Uma verificação independente da URL específica também retornou HTTP 502, embora páginas de listagem do domínio continuassem acessíveis. A compatibilidade desse evento permanece pendente; o projeto não tenta contornar WAF, CAPTCHA ou mecanismos antibot.


---

## Casos reais observados: Unicamp, Vunesp e UnirG

### FCM/Unicamp

Teste informado em **23/09/2026**:

```text
https://portal.fcm.unicamp.br/residencias-em-saude/residencia-medica/processo-seletivo-2027/
```

O Grabber encontrou diversos PDFs ligados ao processo seletivo, mas também alguns documentos aparentemente externos ao contexto imediato da página. Esse resultado mostrou que, em portais grandes, varrer todas as âncoras do HTML pode incluir arquivos de áreas globais.

**Estado:** descoberta funcional, porém com excesso de candidatos. A versão `0.3.5-dev` adicionou foco automático na região principal da página. Reteste pendente.

### Vunesp

Teste informado em **23/09/2026**:

```text
https://www.vunesp.com.br/FMJU2602
```

O servidor respondeu com **HTTP 403 (acesso negado)** nas tentativas do Grabber, antes da etapa de análise dos links.

**Estado:** não compatível pelo método HTTP atual nesse teste. O Grabber não tenta contornar autenticação, WAF, CAPTCHA ou mecanismos antibot.

### UnirG

Teste informado em **23/09/2026**:

```text
https://www.unirg.edu.br/residencia-medica
```

O Grabber encontrou os documentos diretamente relacionados à Residência Médica, mas também uma grande quantidade de arquivos de Pesquisa, Reitoria, documentos institucionais e outras áreas do portal.

A página possui uma área central específica de Residência Médica e, ao mesmo tempo, extensa navegação global do site. A versão `0.3.5-dev` passou a priorizar automaticamente a região principal quando ela pode ser identificada semanticamente, reduzindo a chance de coletar arquivos globais não relacionados.

**Estado:** melhoria implementada; reteste manual necessário para medir a redução dos falsos positivos.
