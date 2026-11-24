// Psittacus — optional on-page buttons (registered only when the user turns
// them on in the options and grants access to sites).
// • A small button in a corner of the window → select an area.
// • A button over images when the mouse is on them → translate that image.
// The page is not read or captured until one of the buttons is clicked.

(() => {
  if (window.__psittacusLauncher || window.top !== window) return;
  window.__psittacusLauncher = true;

  const t = (k) => chrome.i18n.getMessage(k) || k;
  const host = location.hostname;
  let cfg = { launcher: 'off', launcherCorner: 'br', hiddenSites: [] };
  let root = null;
  let corner = null;
  let imgBtn = null;
  let currentImg = null;
  let hideTimer = null;
  let busy = false;

  const load = () =>
    chrome.storage.sync.get(cfg).then((s) => {
      cfg = s;
      render();
    });
  chrome.storage.onChanged.addListener((ch, area) => {
    if (area === 'sync' && (ch.launcher || ch.launcherCorner || ch.hiddenSites)) load();
  });
  load();

  // Hide while Psittacus captures the page, so the buttons are not in the shot.
  document.addEventListener('psittacus-busy', () => {
    busy = true;
    if (root) root.host.style.display = 'none';
  });
  document.addEventListener('psittacus-idle', () => {
    busy = false;
    if (root) root.host.style.display = '';
  });

  const enabled = () => cfg.launcher !== 'off' && !(cfg.hiddenSites || []).includes(host);
  const wantCorner = () => enabled() && (cfg.launcher === 'corner' || cfg.launcher === 'both');
  const wantImages = () => enabled() && (cfg.launcher === 'images' || cfg.launcher === 'both');

  function ensureRoot() {
    if (root) return;
    const h = document.createElement('psittacus-launcher');
    h.style.cssText = 'all:initial;position:fixed;top:0;left:0;width:0;height:0;z-index:2147483646;';
    root = h.attachShadow({ mode: 'closed' });
    const st = document.createElement('style');
    st.textContent = CSS;
    root.append(st);
    document.documentElement.append(h);
  }

  function launch(opts) {
    chrome.runtime.sendMessage({ type: 'psit:launch', ...opts }).catch(() => {});
  }

  function makeButton(cls, title) {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = cls;
    b.title = title;
    b.setAttribute('aria-label', title);
    const i = document.createElement('img');
    i.src = chrome.runtime.getURL('icons/icon32.png');
    i.alt = '';
    b.append(i);
    return b;
  }

  function render() {
    if (wantCorner()) {
      ensureRoot();
      if (!corner) {
        corner = document.createElement('div');
        corner.className = 'corner';
        const b = makeButton('btn', t('actionTitle'));
        b.onclick = () => launch({ mode: 'select' });
        const x = document.createElement('button');
        x.type = 'button';
        x.className = 'hide';
        x.textContent = '×';
        x.title = t('hideOnSite');
        x.setAttribute('aria-label', t('hideOnSite'));
        x.onclick = async (e) => {
          e.stopPropagation();
          const { hiddenSites = [] } = await chrome.storage.sync.get('hiddenSites');
          if (!hiddenSites.includes(host)) hiddenSites.push(host);
          await chrome.storage.sync.set({ hiddenSites });
        };
        corner.append(b, x);
        root.append(corner);
      }
      corner.dataset.pos = cfg.launcherCorner || 'br';
    } else if (corner) {
      corner.remove();
      corner = null;
    }
    if (!wantImages() && imgBtn) {
      imgBtn.remove();
      imgBtn = null;
    }
  }

  // ---------- Button over images ----------
  document.addEventListener(
    'mouseover',
    (e) => {
      if (!wantImages() || busy) return;
      const img = e.target instanceof HTMLImageElement ? e.target : null;
      if (!img) return;
      const r = img.getBoundingClientRect();
      if (r.width < 120 || r.height < 60) return;
      clearTimeout(hideTimer);
      currentImg = img;
      showImgBtn();
    },
    true
  );
  document.addEventListener(
    'mouseout',
    (e) => {
      if (e.target === currentImg) scheduleHide();
    },
    true
  );
  window.addEventListener('scroll', () => currentImg && placeImgBtn(), { passive: true, capture: true });

  function showImgBtn() {
    ensureRoot();
    if (!imgBtn) {
      imgBtn = makeButton('btn img', t('menuImage'));
      imgBtn.onmouseenter = () => clearTimeout(hideTimer);
      imgBtn.onmouseleave = scheduleHide;
      imgBtn.onclick = () => {
        if (!currentImg) return;
        launch({ mode: 'image', srcUrl: currentImg.currentSrc || currentImg.src });
        imgBtn.hidden = true;
      };
      root.append(imgBtn);
    }
    imgBtn.hidden = false;
    placeImgBtn();
  }
  function placeImgBtn() {
    if (!imgBtn || !currentImg) return;
    const r = currentImg.getBoundingClientRect();
    const top = Math.max(8, r.top + 8);
    const left = Math.max(8, r.left + 8);
    if (r.bottom < 40 || r.top > innerHeight - 40) {
      imgBtn.hidden = true;
      return;
    }
    imgBtn.style.top = `${top}px`;
    imgBtn.style.left = `${left}px`;
  }
  function scheduleHide() {
    clearTimeout(hideTimer);
    hideTimer = setTimeout(() => {
      if (imgBtn) imgBtn.hidden = true;
      currentImg = null;
    }, 350);
  }

  const CSS = `
* { box-sizing: border-box; }
.btn {
  all: unset; box-sizing: border-box; display: grid; place-items: center; cursor: pointer;
  width: 40px; height: 40px; border-radius: 50%; background: rgba(0,0,0,.6);
  -webkit-backdrop-filter: blur(16px); backdrop-filter: blur(16px);
  box-shadow: 0 4px 16px rgba(0,0,0,.28); transition: transform .12s, opacity .15s;
}
.btn:hover { transform: scale(1.06); }
.btn:focus-visible { outline: 2px solid #fff; outline-offset: 2px; }
.btn img { width: 24px; height: 24px; border-radius: 7px; image-rendering: pixelated; pointer-events: none; }
.btn.img { position: fixed; width: 34px; height: 34px; }
.btn.img img { width: 20px; height: 20px; border-radius: 6px; }
.corner { position: fixed; opacity: .55; transition: opacity .15s; }
.corner:hover, .corner:focus-within { opacity: 1; }
.corner[data-pos="br"] { right: 18px; bottom: 18px; }
.corner[data-pos="bl"] { left: 18px; bottom: 18px; }
.corner[data-pos="tr"] { right: 18px; top: 18px; }
.corner[data-pos="tl"] { left: 18px; top: 18px; }
.hide {
  all: unset; position: absolute; top: -6px; right: -6px; width: 18px; height: 18px; border-radius: 50%;
  display: none; place-items: center; cursor: pointer; background: #fff; color: #222;
  font: 700 13px/18px system-ui, sans-serif; text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,.3);
}
.corner:hover .hide { display: block; }
[hidden] { display: none !important; }
`;
})();
