# Changelog

## 1.0.0 — 2026-11-23
- First release: select an area (Alt+Shift+T, icon or right-click) and translate the text in it, over a temporary screenshot.
- Right-click an image → translate the whole image.
- Local OCR (Tesseract.js 7, 10 bundled languages) and Chrome's on-device Translator API.
- Original/translation toggle, copy, Portuguese and English UI.
- Target-language menu on the result bar.
- Per-paragraph language detection for mixed text (Japanese + English + romaji).
- Vertical Japanese (manga) OCR option.
- Table borders and dashed lines removed before OCR; list items and bullets handled.
- Optional on-page button (corner of the window and/or over images), hideable per site.
- Japanese/Chinese/Korean read in a separate OCR pass, so Latin models don't garble them.
- New icon: grey parrot facing you with its head turned, wine-red background (pixel art, hand-drawn 16 px).
- Bold and size matched to the original; Tesseract no longer logs to the console.
