# Assets do Grabber

Esta pasta contém a identidade visual utilizada pela aplicação.

```text
assets/
├── grabber.ico
├── grabber.svg
└── grabber.png
```

## `grabber.ico`

Ícone usado pelo executável Windows e pela janela principal. O arquivo fornecido é multirresolução e contém 16×16, 24×24, 32×32, 48×48, 64×64, 128×128 e 256×256 px.

## `grabber.svg`

Arquivo-fonte vetorial preservado no repositório para organização documental, futuras edições e novas exportações.

## `grabber.png`

Fallback gráfico em 256×256 px, gerado a partir do `.ico`, usado pela GUI quando necessário.

O `build_windows.bat` e o workflow do GitHub Actions incorporam automaticamente o `.ico` ao `Grabber.exe`.
