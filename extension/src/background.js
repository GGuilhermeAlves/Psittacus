// Psittacus — service worker.
// Click the icon / Alt+Shift+T / context menu → inject the selector into the tab.
// The content script sends back the selected rectangle; we capture the visible
// tab, hand the picture to the offscreen document (OCR), and return the result.
// The capture lives only in memory and is never stored or sent anywhere.

import { getSettings } from './settings.js';

const OFFSCREEN_URL = 'src/offscreen.html';

// ---------- Optional on-page buttons ----------
// Registered as a content script only while the user has them on and has
// granted access to sites (optional permission, asked in the options page).
const LAUNCHER_ID = 'psit-launcher';
async function syncLauncher() {
  const s = await getSettings();
  const granted = await chrome.permissions.contains({ origins: ['<all_urls>'] });
  const want = s.launcher !== 'off' && granted;
  const reg = await chrome.scripting.getRegisteredContentScripts({ ids: [LAUNCHER_ID] });
  if (want && !reg.length) {
    await chrome.scripting.registerContentScripts([
      { id: LAUNCHER_ID, js: ['src/launcher.js'], matches: ['<all_urls>'], runAt: 'document_idle', allFrames: false }
    ]);
  } else if (!want && reg.length) {
    await chrome.scripting.unregisterContentScripts({ ids: [LAUNCHER_ID] });
  }
}
chrome.runtime.onStartup.addListener(() => syncLauncher().catch(() => {}));
chrome.storage.onChanged.addListener((ch, area) => {
  if (area === 'sync' && ch.launcher) syncLauncher().catch(() => {});
});
chrome.permissions.onAdded.addListener(() => syncLauncher().catch(() => {}));
chrome.permissions.onRemoved.addListener(() => syncLauncher().catch(() => {}));

chrome.runtime.onInstalled.addListener(() => {
  syncLauncher().catch(() => {});
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({
      id: 'psit-area',
      title: chrome.i18n.getMessage('menuArea'),
      contexts: ['page', 'selection', 'link', 'video']
    });
    chrome.contextMenus.create({
      id: 'psit-image',
      title: chrome.i18n.getMessage('menuImage'),
      contexts: ['image']
    });
  });
});

chrome.action.onClicked.addListener((tab) => start(tab, { mode: 'select' }));

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (!tab) return;
  if (info.menuItemId === 'psit-image') start(tab, { mode: 'image', srcUrl: info.srcUrl });
  else start(tab, { mode: 'select' });
});

async function start(tab, opts) {
  if (!tab?.id) return;
  try {
    await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ['src/content.js'] });
    await chrome.tabs.sendMessage(tab.id, { type: 'psit:start', ...opts });
  } catch (e) {
    // chrome://, the Web Store and similar pages refuse scripts.
    flashBadge(tab.id);
    console.warn('[Psittacus] cannot run here:', e?.message || e);
  }
  // Warm up OCR while the user is still dragging.
  Promise.all([getSettings(), ensureOffscreen()])
    .then(([s]) => sendToOffscreen({ type: 'warmup', langs: s.ocrLangs }))
    .catch(() => {});
}

function flashBadge(tabId) {
  chrome.action.setBadgeBackgroundColor({ color: '#B3261E', tabId });
  chrome.action.setBadgeText({ text: '!', tabId });
  setTimeout(() => chrome.action.setBadgeText({ text: '', tabId }), 2500);
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.target === 'offscreen') return false;
  if (msg?.type === 'psit:capture') {
    handleCapture(msg, sender).then(sendResponse, (e) =>
      sendResponse({ ok: false, error: e?.code || 'failed', message: String(e?.message || e) })
    );
    return true;
  }
  if (msg?.type === 'psit:launch' && sender.tab) {
    start(sender.tab, { mode: msg.mode === 'image' ? 'image' : 'select', srcUrl: msg.srcUrl });
    return false;
  }
  if (msg?.type === 'psit:options') {
    chrome.runtime.openOptionsPage();
    return false;
  }
  return false;
});

async function handleCapture(msg, sender) {
  const tab = sender.tab;
  let dataUrl;
  try {
    dataUrl = await chrome.tabs.captureVisibleTab(tab.windowId, { format: 'png' });
  } catch (e) {
    const err = new Error(e?.message || 'capture failed');
    err.code = 'captureFailed';
    throw err;
  }
  const settings = await getSettings();
  await ensureOffscreen();
  const res = await sendToOffscreen({
    type: 'ocr',
    dataUrl,
    rect: msg.rect,
    viewport: msg.viewport,
    langs: settings.ocrLangs
  });
  return res;
}

let creating = null;
async function ensureOffscreen() {
  const url = chrome.runtime.getURL(OFFSCREEN_URL);
  const existing = await chrome.runtime.getContexts({
    contextTypes: ['OFFSCREEN_DOCUMENT'],
    documentUrls: [url]
  });
  if (existing.length) return;
  if (!creating) {
    creating = chrome.offscreen
      .createDocument({
        url: OFFSCREEN_URL,
        reasons: ['WORKERS', 'BLOBS'],
        justification: 'Run text recognition (OCR) on the selected area in a Web Worker, locally.'
      })
      .finally(() => (creating = null));
  }
  await creating;
}

function sendToOffscreen(payload) {
  return chrome.runtime.sendMessage({ target: 'offscreen', ...payload });
}
