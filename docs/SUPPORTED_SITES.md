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

### APIs JSON

Se uma página obtém seus documentos exclusivamente por API, o motor de download continua reaproveitável, mas a descoberta deve ganhar um adaptador para aquela API.

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
