// Shared settings (background + options page).

export const OCR_LANGS = [
  { code: 'eng', bcp: 'en' },
  { code: 'por', bcp: 'pt' },
  { code: 'spa', bcp: 'es' },
  { code: 'fra', bcp: 'fr' },
  { code: 'deu', bcp: 'de' },
  { code: 'ita', bcp: 'it' },
  { code: 'jpn', bcp: 'ja' },
  { code: 'jpn_vert', bcp: 'ja', label: 'langJpnVert' },
  { code: 'chi_sim', bcp: 'zh' },
  { code: 'kor', bcp: 'ko' },
  { code: 'rus', bcp: 'ru' }
];

export const TARGET_LANGS = ['pt', 'en', 'es', 'fr', 'de', 'it', 'ja', 'zh', 'ko', 'ru'];

export function defaultTarget() {
  const ui = (chrome.i18n.getUILanguage() || 'en').toLowerCase().split('-')[0];
  return TARGET_LANGS.includes(ui) ? ui : 'en';
}

export async function getSettings() {
  const s = await chrome.storage.sync.get({ targetLang: null, ocrLangs: ['eng', 'spa'], launcher: 'off', launcherCorner: 'br', hiddenSites: [] });
  if (!s.targetLang) s.targetLang = defaultTarget();
  if (!Array.isArray(s.ocrLangs) || !s.ocrLangs.length) s.ocrLangs = ['eng'];
  // Vertical Japanese works best together with the horizontal model, and
  // Tesseract wants the languages in a stable order.
  if (s.ocrLangs.includes('jpn_vert') && !s.ocrLangs.includes('jpn')) s.ocrLangs.push('jpn');
  const order = OCR_LANGS.map((l) => l.code);
  s.ocrLangs = s.ocrLangs.filter((c) => order.includes(c)).sort((a, b) => order.indexOf(a) - order.indexOf(b));
  return s;
}
