// Psittacus — content script (injected on demand with activeTab).
// 1. Lets the user drag a rectangle over the page.
// 2. Asks the service worker to capture + OCR that area.
// 3. Translates the paragraphs with Chrome's built-in Translator API
//    (on-device) and shows them over a temporary "screenshot" of the area.

(() => {
  if (window.__psittacus) return;
  window.__psittacus = true;

  const t = (key, subs = {}) =>
    (chrome.i18n.getMessage(key) || key).replace(/\{(\w+)\}/g, (_, k) => subs[k] ?? '');
  const UI_LANG = (chrome.i18n.getUILanguage() || 'en').split('-')[0];
  const OCR_TO_BCP = { eng: 'en', por: 'pt', spa: 'es', fra: 'fr', deu: 'de', ita: 'it', jpn: 'ja', chi_sim: 'zh', kor: 'ko', rus: 'ru' };
  const TARGETS = ['pt', 'en', 'es', 'fr', 'de', 'it', 'ja', 'zh', 'ko', 'ru'];
  let langNames;
  try {
    langNames = new Intl.DisplayNames([chrome.i18n.getUILanguage()], { type: 'language' });
  } catch {
    langNames = { of: (c) => c };
  }
  const nameOf = (c) => {
    try {
      return langNames.of(c) || c;
    } catch {
      return c;
    }
  };

  // ---------- Shadow host ----------
  let host = null;
  let root = null;
  function ensureHost() {
    if (host?.isConnected) return;
    host = document.createElement('psittacus-root');
    host.style.cssText = 'all:initial;position:absolute;top:0;left:0;width:0;height:0;z-index:2147483647;';
    root = host.attachShadow({ mode: 'closed' });
    const style = document.createElement('style');
    style.textContent = CSS;
    root.appendChild(style);
    document.documentElement.appendChild(host);
  }
  function clearUi() {
    if (!root) return;
    [...root.children].forEach((c) => c.tagName !== 'STYLE' && c.remove());
    cleanup.forEach((f) => f());
    cleanup = [];
  }
  let cleanup = [];
  function on(target, type, fn, opts) {
    target.addEventListener(type, fn, opts);
    cleanup.push(() => target.removeEventListener(type, fn, opts));
  }

  // ---------- Messages from the service worker ----------
  chrome.runtime.onMessage.addListener((msg, _s, sendResponse) => {
    if (msg?.type !== 'psit:start') return false;
    sendResponse({ ok: true });
    if (msg.mode === 'image' && startFromImage(msg.srcUrl)) return false;
    startSelection();
    return false;
  });

  // ---------- 1. Selection ----------
  function startSelection() {
    ensureHost();
    clearUi();
    const layer = el('div', 'select-layer');
    const hole = el('div', 'hole');
    hole.hidden = true;
    const hint = el('div', 'pill hint');
    hint.append(parrot(), el('span', '', t('hintSelect')), el('span', 'dim', t('hintEsc')));
    layer.append(hole, hint);
    root.append(layer);
    // Fixed layer over the viewport.
    layer.focus?.();

    let start = null;
    let rect = null;
    const norm = (a, b) => ({
      x: Math.min(a.x, b.x),
      y: Math.min(a.y, b.y),
      w: Math.abs(a.x - b.x),
      h: Math.abs(a.y - b.y)
    });
    on(layer, 'pointerdown', (e) => {
      if (e.button !== 0) return;
      e.preventDefault();
      layer.setPointerCapture(e.pointerId);
      start = { x: e.clientX, y: e.clientY };
      rect = { x: start.x, y: start.y, w: 0, h: 0 };
      layer.classList.add('dragging');
      hint.classList.add('fade');
    });
    on(layer, 'pointermove', (e) => {
      if (!start) return;
      rect = norm(start, { x: e.clientX, y: e.clientY });
      Object.assign(hole.style, px(rect));
      hole.hidden = false;
    });
    on(layer, 'pointerup', () => {
      if (!start) return;
      start = null;
      if (!rect || rect.w < 8 || rect.h < 8) {
        layer.classList.remove('dragging');
        hint.classList.remove('fade');
        hole.hidden = true;
        return;
      }
      capture(rect);
    });
    on(window, 'keydown', (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        e.stopPropagation();
        clearUi();
      }
    }, true);
  }

  function startFromImage(srcUrl) {
    const img = [...document.images].find((i) => (i.currentSrc || i.src) === srcUrl);
    if (!img) return false;
    const r = img.getBoundingClientRect();
    const x = Math.max(0, r.left);
    const y = Math.max(0, r.top);
    const w = Math.min(innerWidth, r.right) - x;
    const h = Math.min(innerHeight, r.bottom) - y;
    if (w < 8 || h < 8) return false;
    ensureHost();
    clearUi();
    capture({ x, y, w, h });
    return true;
  }

  // ---------- 2. Capture + OCR ----------
  async function capture(rect) {
    clearUi();
    const page = { x: rect.x + scrollX, y: rect.y + scrollY, w: rect.w, h: rect.h };
    document.dispatchEvent(new Event('psittacus-busy'));
    // Let the browser paint the page without our overlay before capturing.
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(r, 16))));

    const viewport = { w: innerWidth, h: innerHeight };
    const res = chrome.runtime.sendMessage({ type: 'psit:capture', rect, viewport });
    // The capture is taken right away; the on-page buttons can come back.
    setTimeout(() => document.dispatchEvent(new Event('psittacus-idle')), 400);
    const frame = loading(page);
    let out;
    try {
      out = await res;
    } catch (e) {
      out = { ok: false, error: 'failed', message: String(e?.message || e) };
    }
    frame.remove();
    if (!out?.ok) return toast(page, errorText(out));
    if (!out.paragraphs.length) {
      const { ocrLangs = [] } = await chrome.storage.sync.get('ocrLangs');
      const cjk = ocrLangs.some((l) => /^(jpn|chi|kor)/.test(l));
      return toast(page, cjk ? t('noText') : t('noTextHint'), !cjk);
    }
    showResult(page, out);
  }

  function errorText(out) {
    if (out?.error === 'ocrMissing') return t('ocrMissing');
    if (out?.error === 'captureFailed') return t('captureFailed');
    return t('failed', { msg: out?.message || '?' });
  }

  function loading(page) {
    ensureHost();
    const frame = el('div', 'frame loading');
    Object.assign(frame.style, px(page));
    const pill = el('div', 'pill status');
    pill.append(spinner(), el('span', '', t('reading')));
    frame.append(pill);
    root.append(frame);
    return frame;
  }

  function toast(page, text, withOptions = false) {
    ensureHost();
    clearUi();
    const frame = el('div', 'frame ghost');
    Object.assign(frame.style, px(page));
    const pill = el('div', 'pill status');
    pill.append(parrot(), el('span', '', text));
    if (withOptions) {
      const b = button(t('options'), ICONS.settings);
      b.onclick = () => chrome.runtime.sendMessage({ type: 'psit:options' });
      pill.append(b);
    }
    frame.append(pill);
    root.append(frame);
    const kill = () => clearUi();
    setTimeout(kill, withOptions ? 7000 : 3500);
    on(window, 'keydown', (e) => e.key === 'Escape' && kill(), true);
    on(window, 'pointerdown', (e) => !e.composedPath().includes(host) && kill(), true);
  }

  // ---------- 3. Result card ----------
  async function showResult(page, out) {
    ensureHost();
    clearUi();
    const card = el('div', 'card');
    Object.assign(card.style, px(page));
    const shot = document.createElement('img');
    shot.className = 'shot';
    shot.src = out.image;
    shot.alt = '';
    shot.draggable = false;
    card.append(shot);

    const patches = out.paragraphs.map((p) => {
      const d = el('div', 'patch pending');
      const pad = Math.max(2, Math.min(6, p.lineHeight * 0.18));
      // Vertical Japanese (manga): the translation is written horizontally,
      // so the narrow column is widened around its centre.
      let x = p.box.x;
      let w = p.box.w;
      if (p.vertical) {
        w = Math.min(page.w - 4, Math.max(w, Math.min(180, p.box.h * 0.9)));
        x = Math.max(2, Math.min(page.w - w - 2, p.box.x + p.box.w / 2 - w / 2));
        d.classList.add('vertical');
      }
      Object.assign(d.style, {
        left: `${x - pad}px`,
        top: `${p.box.y - pad}px`,
        width: `${w + pad * 2}px`,
        minHeight: `${p.box.h + pad * 2}px`,
        padding: `${pad}px`,
        color: p.fg
      });
      if (p.busy) d.classList.add('busy');
      d.title = p.text;
      card.append(d);
      return d;
    });

    const bar = el('div', 'pill bar');
    const label = el('span', 'langs', '');
    const status = el('span', 'status-text', t('translating'));
    const toggle = button(t('showOriginal'), ICONS.eye);
    const copy = button(t('copy'), ICONS.copy);
    const close = button(t('close'), ICONS.close, true);
    toggle.hidden = true;
    copy.hidden = true;
    // Target language picker: changing it re-translates and becomes the default.
    const picker = document.createElement('select');
    picker.className = 'target';
    picker.title = t('optTarget');
    picker.setAttribute('aria-label', t('optTarget'));
    for (const code of TARGETS) picker.add(new Option(code.toUpperCase(), code));
    bar.append(parrot(), label, picker, status, toggle, copy, sep(), close);
    root.append(card, bar);
    placeBar(bar, page);

    const kill = () => clearUi();
    close.onclick = kill;
    on(window, 'keydown', (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        kill();
      }
    }, true);
    on(window, 'pointerdown', (e) => !e.composedPath().includes(host) && kill(), true);
    on(window, 'resize', () => placeBar(bar, page));
    on(window, 'scroll', () => placeBar(bar, page), { passive: true });

    let showingOriginal = false;
    toggle.onclick = () => {
      showingOriginal = !showingOriginal;
      card.classList.toggle('original', showingOriginal);
      setButton(toggle, showingOriginal ? t('showTranslation') : t('showOriginal'), showingOriginal ? ICONS.translate : ICONS.eye);
    };
    let translated = null;
    copy.onclick = async () => {
      const text = (translated || out.paragraphs.map((p) => p.text)).join('\n\n');
      try {
        await navigator.clipboard.writeText(text);
      } catch {
        const ta = document.createElement('textarea');
        ta.value = text;
        root.append(ta);
        ta.select();
        document.execCommand('copy');
        ta.remove();
      }
      setButton(copy, t('copied'), ICONS.check);
      setTimeout(() => setButton(copy, t('copy'), ICONS.copy), 1400);
    };

    const settings = await chrome.storage.sync.get({ targetLang: null, ocrLangs: ['eng', 'spa'] });
    const dst = settings.targetLang || (TARGETS.includes(UI_LANG) ? UI_LANG : 'en');
    const paras = out.paragraphs;
    picker.value = dst;
    picker.onchange = async () => {
      await chrome.storage.sync.set({ targetLang: picker.value });
      showResult(page, out);
    };

    const done = (msg) => {
      status.textContent = msg || '';
      status.hidden = !msg;
      copy.hidden = false;
      placeBar(bar, page);
    };
    const showOriginalOnly = (msg) => {
      card.classList.add('original');
      patches.forEach((d) => d?.remove());
      done(msg);
    };

    if (!('Translator' in self)) return showOriginalOnly(t('noTranslator'));

    // Each paragraph gets its own language: one picture often mixes
    // Japanese, English and romaji.
    const langs = await detectAll(paras.map((p) => p.text), settings.ocrLangs, dst);
    const sources = [...new Set(langs.filter((l) => l && l !== 'romaji' && base(l) !== base(dst)))];
    label.textContent = `${(sources.length ? sources : [dst]).map((l) => base(l).toUpperCase()).join(', ')} →`;

    translated = paras.map((p) => p.text);
    const notes = new Set();
    const keepOriginal = (i) => {
      patches[i].remove();
      patches[i] = null;
    };
    langs.forEach((l, i) => {
      if (l === 'romaji') {
        keepOriginal(i);
        notes.add(t('romajiKept'));
      } else if (!l || base(l) === base(dst)) {
        keepOriginal(i);
      }
    });
    if (!sources.length) return showOriginalOnly(t('sameLang', { lang: nameOf(dst) }));

    for (const src of sources) {
      let translator;
      try {
        translator = await getTranslator(src, dst, status, bar, page);
      } catch (e) {
        const msg = e?.code === 'unsupported' ? t('unsupportedPair', { src: nameOf(src), dst: nameOf(dst) }) : t('failed', { msg: e?.message || e });
        notes.add(msg);
        langs.forEach((l, i) => l === src && patches[i] && keepOriginal(i));
        continue;
      }
      if (!card.isConnected) return;
      const idx = langs.map((l, i) => (l === src && patches[i] ? i : -1)).filter((i) => i >= 0);
      try {
        const res = await Promise.all(idx.map((i) => translator.translate(paras[i].text)));
        idx.forEach((i, j) => (translated[i] = res[j]));
      } catch (e) {
        notes.add(t('failed', { msg: e?.message || e }));
        idx.forEach(keepOriginal);
        continue;
      }
      if (!card.isConnected) return;
      idx.forEach((i) => {
        const d = patches[i];
        d.textContent = translated[i];
        d.style.background = paras[i].bg;
        d.classList.remove('pending');
        fit(d, paras[i]);
      });
    }
    if (!patches.some(Boolean)) return showOriginalOnly([...notes].join(' · '));
    toggle.hidden = false;
    done([...notes].join(' · '));
  }

  // Starts at the original size and shrinks until the translation fits the box.
  function fit(d, p) {
    const boxH = parseFloat(d.style.minHeight);
    let size = Math.max(8, Math.min(p.fontSize || p.lineHeight, 96));
    if (p.vertical) size = Math.min(size, 22);
    const ratio = p.lines > 1 && p.pitch ? Math.max(1.05, Math.min(p.pitch / size, 2)) : 1.15;
    if (p.bold) d.style.fontWeight = '700';
    const apply = () => {
      d.style.fontSize = `${size}px`;
      d.style.lineHeight = `${size * ratio}px`;
    };
    apply();
    // A longer translation may first grow to the right (up to 1.6× the original
    // width, inside the card) before the font gets smaller.
    if (!p.vertical && (d.scrollHeight > boxH + 1 || d.scrollWidth > d.clientWidth + 1)) {
      const left = parseFloat(d.style.left);
      const w = parseFloat(d.style.width);
      const room = d.parentElement.clientWidth - left - 4;
      d.style.width = `${Math.max(w, Math.min(room, w * 1.6))}px`;
    }
    let guard = 80;
    while (guard-- > 0 && size > 7 && (d.scrollHeight > boxH + 1 || d.scrollWidth > d.clientWidth + 1)) {
      size -= size > 20 ? 1 : 0.5;
      apply();
    }
  }

  function placeBar(bar, page) {
    const gap = 10;
    const bw = bar.offsetWidth || 300;
    const bh = bar.offsetHeight || 40;
    let left = page.x + page.w / 2 - bw / 2;
    left = Math.max(scrollX + 8, Math.min(left, scrollX + innerWidth - bw - 8));
    const below = page.y + page.h + gap;
    const above = page.y - bh - gap;
    const fitsBelow = below + bh <= scrollY + innerHeight - 8;
    let top = fitsBelow || above < scrollY + 8 ? below : above;
    if (!fitsBelow && above < scrollY + 8) top = Math.min(below, scrollY + innerHeight - bh - 8); // inside, at the bottom
    bar.style.left = `${left}px`;
    bar.style.top = `${top}px`;
  }

  // ---------- Translation (Chrome built-in, on device) ----------
  const translators = new Map();
  let detector = null;

  const LATIN = new Set(['en', 'pt', 'es', 'fr', 'de', 'it']);
  const KANA = /[぀-ヿㇰ-ㇿｦ-ﾟ]/;
  const HANGUL = /[가-힯ᄀ-ᇿ㄰-㆏]/;
  const HAN = /[㐀-鿿]/;
  const CYRILLIC = /[Ѐ-ӿ]/;
  const LETTER = /\p{L}/u;

  // Language of each paragraph: the writing system decides when it can
  // (kana → Japanese, hangul → Korean…); the Language Detector decides
  // between Latin-script languages, limited to the ones ticked in the settings.
  async function detectAll(texts, ocrLangs, dst) {
    const enabled = new Set((ocrLangs || []).map((c) => OCR_TO_BCP[c.replace('_vert', '')]).filter(Boolean));
    const latin = [...enabled].filter((l) => LATIN.has(l));
    const latinCands = new Set([...latin, ...(LATIN.has(base(dst)) ? [base(dst)] : [])]);
    const latinFallback = latin.includes('en') ? 'en' : latin[0] || 'en';
    const hasCJK = enabled.has('ja') || enabled.has('zh') || enabled.has('ko');

    const res = [];
    for (const text of texts) {
      if (!LETTER.test(text)) {
        res.push(null); // numbers, times, prices: nothing to translate
        continue;
      }
      if (KANA.test(text)) res.push('ja');
      else if (HANGUL.test(text)) res.push('ko');
      else if (HAN.test(text)) res.push(enabled.has('zh') && !enabled.has('ja') ? 'zh' : enabled.has('ja') && !enabled.has('zh') ? 'ja' : await pick(text, new Set(['ja', 'zh']), 'ja'));
      else if (CYRILLIC.test(text)) res.push('ru');
      else {
        const l = await pick(text, latinCands, null, true);
        // Latin letters that the detector reads as Japanese/Chinese/Korean = romanization.
        if (l === 'cjk') res.push(hasCJK ? 'romaji' : latinFallback);
        else res.push(l || null);
      }
    }
    // Very short Latin bits ("OK", "vs") borrow the language of their neighbours.
    const known = res.filter((l) => l && LATIN.has(l));
    const majority = known.sort((a, b) => known.filter((x) => x === b).length - known.filter((x) => x === a).length)[0] || latinFallback;
    return res.map((l, i) => (l === undefined || (l === null && LETTER.test(texts[i])) ? majority : l));
  }

  async function pick(text, cands, fallback, latinText = false) {
    let results = null;
    if ('LanguageDetector' in self) {
      try {
        if (!detector) detector = await LanguageDetector.create();
        results = await detector.detect(text);
      } catch {
        results = null;
      }
    }
    if (!results?.length) return fallback ?? undefined;
    const top = results[0];
    if (latinText && ['ja', 'zh', 'ko'].includes(base(top.detectedLanguage)) && top.confidence > 0.5) return 'cjk';
    for (const r of results) {
      if (r.confidence < 0.05) break;
      if (cands.has(base(r.detectedLanguage))) return base(r.detectedLanguage);
    }
    return fallback ?? undefined;
  }

  const base = (c) => String(c).toLowerCase().split('-')[0];

  async function getTranslator(src, dst, status, bar, page) {
    const key = `${src}>${dst}`;
    if (translators.has(key)) return translators.get(key);
    const opts = { sourceLanguage: src, targetLanguage: dst };
    let avail = await Translator.availability(opts);
    if (avail === 'unavailable' && src.includes('-')) {
      opts.sourceLanguage = base(src);
      avail = await Translator.availability(opts);
    }
    if (avail === 'unavailable') {
      const e = new Error('unsupported');
      e.code = 'unsupported';
      throw e;
    }
    if (avail !== 'available') status.textContent = t('downloadingModel', { pct: 0 });
    const create = () =>
      Translator.create({
        ...opts,
        monitor(m) {
          m.addEventListener('downloadprogress', (ev) => {
            status.textContent = t('downloadingModel', { pct: Math.round((ev.loaded || 0) * 100) });
            placeBar(bar, page);
          });
        }
      });
    let tr;
    try {
      tr = await create();
    } catch (e) {
      if (e?.name !== 'NotAllowedError') throw e;
      // The model must be downloaded and the click that started this has expired:
      // ask for one more click.
      tr = await new Promise((resolve, reject) => {
        const b = button(t('downloadModel', { src: nameOf(opts.sourceLanguage), dst: nameOf(dst) }), ICONS.download);
        b.classList.add('primary');
        status.hidden = true;
        bar.insertBefore(b, status);
        placeBar(bar, page);
        b.onclick = async () => {
          b.remove();
          status.hidden = false;
          status.textContent = t('downloadingModel', { pct: 0 });
          try {
            resolve(await create());
          } catch (err) {
            reject(err);
          }
        };
      });
    }
    translators.set(key, tr);
    return tr;
  }

  // ---------- Small helpers ----------
  function el(tag, cls, text) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function px(r) {
    return { left: `${r.x}px`, top: `${r.y}px`, width: `${r.w}px`, height: `${r.h}px` };
  }
  function sep() {
    return el('span', 'sep');
  }
  function button(label, icon, iconOnly = false) {
    const b = el('button', iconOnly ? 'btn icon-only' : 'btn');
    b.type = 'button';
    setButton(b, label, icon, iconOnly);
    return b;
  }
  function setButton(b, label, icon, iconOnly = b.classList.contains('icon-only')) {
    b.replaceChildren(svg(icon));
    if (!iconOnly) b.append(el('span', '', label));
    b.title = label;
    b.setAttribute('aria-label', label);
  }
  function svg(d) {
    const ns = 'http://www.w3.org/2000/svg';
    const s = document.createElementNS(ns, 'svg');
    s.setAttribute('viewBox', '0 0 24 24');
    s.setAttribute('aria-hidden', 'true');
    const p = document.createElementNS(ns, 'path');
    p.setAttribute('d', d);
    s.append(p);
    return s;
  }
  function spinner() {
    return el('span', 'spinner');
  }
  function parrot() {
    const i = document.createElement('img');
    i.className = 'logo';
    i.src = chrome.runtime.getURL('icons/icon32.png');
    i.alt = '';
    return i;
  }

  const ICONS = {
    eye: 'M12 5c-5 0-9 4.5-10 7 1 2.5 5 7 10 7s9-4.5 10-7c-1-2.5-5-7-10-7zm0 11.5a4.5 4.5 0 1 1 0-9 4.5 4.5 0 0 1 0 9zm0-2.3a2.2 2.2 0 1 0 0-4.4 2.2 2.2 0 0 0 0 4.4z',
    translate: 'M12.9 15.1 10.4 12.6l.03-.03A17.5 17.5 0 0 0 14.1 6H17V4h-7V2H8v2H1v2h11.2A15.8 15.8 0 0 1 9 11.4 15.6 15.6 0 0 1 6.7 8H4.7c.73 1.6 1.7 3.2 3 4.6l-5.1 5L4 19l5-5 3.1 3.1.8-2zM18.5 10h-2L12 22h2l1.1-3h4.8l1.1 3h2l-4.5-12zm-2.6 7 1.6-4.3 1.6 4.3h-3.2z',
    copy: 'M16 1H4a2 2 0 0 0-2 2v14h2V3h12V1zm3 4H8a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2zm0 16H8V7h11v14z',
    check: 'M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4L9 16.2z',
    close: 'M19 6.4 17.6 5 12 10.6 6.4 5 5 6.4 10.6 12 5 17.6 6.4 19 12 13.4 17.6 19 19 17.6 13.4 12z',
    download: 'M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z',
    settings: 'M19.4 13a7.5 7.5 0 0 0 0-2l2.1-1.6-2-3.5-2.5 1a7.4 7.4 0 0 0-1.7-1L15 3h-4l-.4 2.7a7.4 7.4 0 0 0-1.7 1l-2.5-1-2 3.5L6.6 11a7.5 7.5 0 0 0 0 2l-2.1 1.6 2 3.5 2.5-1c.5.4 1.1.7 1.7 1L11 21h4l.4-2.7c.6-.3 1.2-.6 1.7-1l2.5 1 2-3.5-2.2-1.8zM13 15.5a3.5 3.5 0 1 1 0-7 3.5 3.5 0 0 1 0 7z'
  };

  const CSS = `
:host { all: initial; }
* { box-sizing: border-box; }
.select-layer {
  position: fixed; inset: 0; cursor: crosshair; background: rgba(0,0,0,.28);
  outline: none; touch-action: none; user-select: none;
}
.select-layer.dragging { background: transparent; }
.hole {
  position: fixed; border-radius: 6px; pointer-events: none;
  box-shadow: 0 0 0 100vmax rgba(0,0,0,.42), inset 0 0 0 1.5px rgba(255,255,255,.95);
}
.pill {
  display: inline-flex; align-items: center; gap: 8px; height: 40px; padding: 0 14px 0 10px;
  border-radius: 28px; background: rgba(0,0,0,.6); color: #fff;
  -webkit-backdrop-filter: blur(16px); backdrop-filter: blur(16px);
  font: 500 13px/1 "Roboto", system-ui, -apple-system, "Segoe UI", sans-serif;
  box-shadow: 0 4px 20px rgba(0,0,0,.25); white-space: nowrap;
}
.hint { position: fixed; top: 18px; left: 50%; transform: translateX(-50%); transition: opacity .15s; }
.hint.fade { opacity: 0; }
.dim { opacity: .6; font-weight: 400; }
.logo { width: 20px; height: 20px; border-radius: 6px; image-rendering: pixelated; flex: none; }
.frame { position: absolute; border-radius: 6px; pointer-events: none; }
.frame.loading {
  box-shadow: inset 0 0 0 1.5px rgba(255,255,255,.9), 0 0 0 1px rgba(0,0,0,.35);
  background: linear-gradient(100deg, rgba(255,255,255,0) 30%, rgba(255,255,255,.22) 50%, rgba(255,255,255,0) 70%) 0 0 / 250% 100%;
  animation: shimmer 1.1s linear infinite;
}
.frame.ghost { box-shadow: inset 0 0 0 1.5px rgba(255,255,255,.7); }
.frame .status { position: absolute; left: 50%; top: calc(100% + 10px); transform: translateX(-50%); pointer-events: auto; }
@keyframes shimmer { from { background-position: 125% 0; } to { background-position: -125% 0; } }
.spinner {
  width: 16px; height: 16px; border-radius: 50%; flex: none;
  border: 2px solid rgba(255,255,255,.3); border-top-color: #fff; animation: spin .7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.card {
  position: absolute; overflow: hidden; border-radius: 6px;
  box-shadow: 0 0 0 1px rgba(255,255,255,.55), 0 10px 36px rgba(0,0,0,.38);
  animation: pop .16s ease-out; background: #000;
}
@keyframes pop { from { transform: scale(.985); opacity: .4; } to { transform: none; opacity: 1; } }
.shot { position: absolute; inset: 0; width: 100%; height: 100%; display: block; user-select: none; pointer-events: none; }
.patch {
  position: absolute; border-radius: 4px; overflow: hidden; overflow-wrap: anywhere;
  font-family: system-ui, -apple-system, "Segoe UI", "Roboto", "Noto Sans", sans-serif; font-weight: 500;
  user-select: text; cursor: text; transition: opacity .15s;
}
.patch.busy { box-shadow: 0 1px 6px rgba(0,0,0,.25); }
.patch.vertical { display: flex; align-items: center; justify-content: center; text-align: center; }
.patch.pending {
  color: transparent !important;
  background-image: linear-gradient(100deg, rgba(127,127,127,0) 30%, rgba(127,127,127,.3) 50%, rgba(127,127,127,0) 70%);
  background-size: 250% 100%; animation: shimmer 1.1s linear infinite;
}
.card.original .patch { opacity: 0; pointer-events: none; }
.bar { position: absolute; z-index: 1; animation: pop .16s ease-out; }
.langs { font-weight: 600; letter-spacing: .02em; }
.langs:empty { display: none; }
.target {
  all: unset; font-family: inherit; font-size: 13px; font-weight: 600; line-height: 1; color: #fff; cursor: pointer; letter-spacing: .02em;
  padding: 6px 20px 6px 8px; margin-left: -4px; border-radius: 12px; color-scheme: dark;
  background: rgba(255,255,255,.12) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 10 6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='white'/%3E%3C/svg%3E") no-repeat right 7px center / 8px 5px;
}
.target:hover { background-color: rgba(255,255,255,.2); }
.target:focus-visible { outline: 2px solid #fff; }
.target option { background: #222; color: #fff; }
.status-text { opacity: .8; font-weight: 400; }
.status-text:empty { display: none; }
.sep { width: 1px; height: 18px; background: rgba(255,255,255,.25); }
.btn {
  all: unset; display: inline-flex; align-items: center; gap: 6px; height: 30px; padding: 0 10px;
  border-radius: 16px; color: #fff; cursor: pointer; font: inherit;
}
.btn:hover { background: rgba(255,255,255,.14); }
.btn:focus-visible { outline: 2px solid #fff; outline-offset: 1px; }
.btn.icon-only { width: 30px; padding: 0; justify-content: center; }
.btn.primary { background: #fff; color: #111; }
.btn.primary svg { fill: #111; }
.btn svg { width: 18px; height: 18px; fill: #fff; flex: none; }
[hidden] { display: none !important; }
`;
})();
