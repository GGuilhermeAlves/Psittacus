# Chrome Web Store — textos para a publicação

**Nome:** Psittacus
**Categoria:** Ferramentas
**Idioma principal:** Português (Brasil); também tem inglês.

## Descrição curta (até 132 caracteres)
Selecione qualquer área da página e traduza o texto dela na hora, como uma print temporária. Funciona todo no seu computador.

## Descrição longa
Traduza texto que está dentro de imagens, prints, memes, gráficos e quadrinhos sem sair da página.

• Aperte Alt+Shift+T (ou clique no ícone) e arraste sobre o que quer traduzir.
• Ou clique com o botão direito numa imagem → Traduzir esta imagem.
• A tradução aparece no lugar do texto original, com as mesmas cores e tamanho.
• Opcional: botão na página, no canto ou sobre as imagens.
• Alterne entre original e tradução, copie o texto traduzido e feche com Esc.

Privado de verdade: a captura, a leitura do texto (OCR) e a tradução acontecem no seu computador. Nada é enviado para servidores. Usa o tradutor embutido do Chrome (Chrome 138+ no computador).

Idiomas do OCR: inglês, português, espanhol, francês, alemão, italiano, japonês, chinês simplificado, coreano e russo.

## Justificativas das permissões
- **activeTab:** colocar o seletor na aba e capturar a área visível só quando você clica no ícone, usa o atalho ou o menu.
- **scripting:** injetar o seletor e o card de resultado na aba atual depois do clique.
- **offscreen:** rodar o OCR (Tesseract.js) num Web Worker, fora da página.
- **storage:** guardar o idioma de destino e os idiomas do OCR.
- **Acesso a sites (opcional, `<all_urls>`):** só é pedido se você ligar o "Botão na página" nas opções, para mostrar o botão nas páginas. Nada é lido nem capturado até o clique.
- **contextMenus:** os itens "Traduzir uma área" e "Traduzir esta imagem" no botão direito.

**Código remoto:** não. Todo o código e os dados de idiomas estão no pacote.
**Uso de dados:** não coleta nenhum dado. Política: `https://github.com/GGuilhermeAlves/Psittacus/blob/main/PRIVACY.md`

## Imagens necessárias
- Ícone 128×128: `extension/icons/icon128.png`
- Pelo menos uma captura 1280×800 (dá para usar `docs/screenshot-poster.png` como base).
