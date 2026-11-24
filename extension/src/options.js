import { OCR_LANGS, TARGET_LANGS, getSettings } from './settings.js';

const names = new Intl.DisplayNames([chrome.i18n.getUILanguage()], { type: 'language' });
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);

document.querySelectorAll('[data-i18n]').forEach((el) => {
  el.textContent = chrome.i18n.getMessage(el.dataset.i18n);
});
document.title = chrome.i18n.getMessage('optionsTitle');

const s = await getSettings();

const target = document.getElementById('target');
for (const code of TARGET_LANGS) {
  const o = new Option(cap(names.of(code)), code);
  target.add(o);
}
target.value = s.targetLang;
target.onchange = () => save({ targetLang: target.value });

const box = document.getElementById('langs');
for (const { code, bcp, label } of OCR_LANGS) {
  const l = document.createElement('label');
  const c = document.createElement('input');
  c.type = 'checkbox';
  c.value = code;
  c.checked = s.ocrLangs.includes(code);
  if (code === 'jpn_vert') l.title = chrome.i18n.getMessage('langJpnVertHint');
  c.onchange = () => {
    const picked = [...box.querySelectorAll('input:checked')].map((i) => i.value);
    if (!picked.length) {
      c.checked = true;
      return;
    }
    save({ ocrLangs: picked });
  };
  l.append(c, label ? chrome.i18n.getMessage(label) : cap(names.of(bcp === 'zh' ? 'zh-Hans' : bcp)));
  box.append(l);
}

let timer;
async function save(patch) {
  await chrome.storage.sync.set(patch);
  const el = document.getElementById('saved');
  el.hidden = false;
  clearTimeout(timer);
  timer = setTimeout(() => (el.hidden = true), 1200);
}

// ---------- On-page button ----------
const launcher = document.getElementById('launcher');
const corner = document.getElementById('corner');
const cornerRow = document.getElementById('cornerRow');
const permHint = document.getElementById('permHint');
const hiddenRow = document.getElementById('hiddenRow');
const hiddenText = document.getElementById('hiddenText');
launcher.value = s.launcher;
corner.value = s.launcherCorner;
const refresh = (hidden = s.hiddenSites) => {
  cornerRow.hidden = !['corner', 'both'].includes(launcher.value);
  permHint.hidden = launcher.value === 'off';
  hiddenRow.hidden = launcher.value === 'off' || !hidden.length;
  hiddenText.textContent = chrome.i18n.getMessage('hiddenOn').replace('{n}', hidden.length);
};
refresh();
launcher.onchange = async () => {
  const value = launcher.value;
  if (value !== 'off') {
    // Must be called straight from the user's change, before any other await.
    const ok = await chrome.permissions.request({ origins: ['<all_urls>'] });
    if (!ok) {
      launcher.value = 'off';
      permHint.hidden = false;
      permHint.textContent = chrome.i18n.getMessage('permDenied');
      permHint.classList.add('error');
      refresh();
      return;
    }
  }
  permHint.textContent = chrome.i18n.getMessage('optLauncherPerm');
  permHint.classList.remove('error');
  await save({ launcher: value });
  refresh();
};
corner.onchange = () => save({ launcherCorner: corner.value });
document.getElementById('showAll').onclick = async () => {
  await save({ hiddenSites: [] });
  refresh([]);
};
chrome.storage.onChanged.addListener((ch) => ch.hiddenSites && refresh(ch.hiddenSites.newValue || []));
