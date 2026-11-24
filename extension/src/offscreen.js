// Psittacus — offscreen document: runs Tesseract.js (OCR) in a Web Worker.
// Receives a capture of the visible tab + the selected rectangle, crops it,
// reads the text and returns paragraphs with their position and colours.
// Nothing is stored or sent anywhere.

/* global Tesseract */

const URL_ = (p) => chrome.runtime.getURL(p);

// One worker per group of languages. Latin/Cyrillic and CJK models are run
// separately: mixed together, the English model "reads" Japanese as garbage
// like "CB Tle" and wins over the right reading.
const workers = new Map();
const CJK_LANGS = new Set(['jpn', 'jpn_vert', 'chi_sim', 'chi_tra', 'kor']);

function passes(langs) {
  const cjk = langs.filter((l) => CJK_LANGS.has(l));
  const other = langs.filter((l) => !CJK_LANGS.has(l));
  return [other, cjk].filter((g) => g.length);
}

function getWorker(langs) {
  const key = langs.join('+');
  if (workers.has(key)) return workers.get(key);
  // Keep at most the workers of the current settings.
  const p = (async () => {
    if (typeof Tesseract === 'undefined') {
      const e = new Error('Tesseract.js missing');
      e.code = 'ocrMissing';
      throw e;
    }
    const w = await Tesseract.createWorker(langs, Tesseract.OEM.LSTM_ONLY, {
      workerPath: URL_('vendor/worker.min.js'),
      corePath: URL_('vendor/core'),
      langPath: URL_('lang'),
      workerBlobURL: false,
      cacheMethod: 'none',
      gzip: true
    });
    // A fixed DPI and a silent debug file stop Tesseract from printing
    // "Estimating resolution as …" to the console (Chrome lists it as an error).
    await w.setParameters({ preserve_interword_spaces: '1', user_defined_dpi: '300', debug_file: '/dev/null' });
    return w;
  })();
  workers.set(key, p);
  p.catch(() => workers.delete(key));
  return p;
}

function dropUnused(langs) {
  const keep = new Set(passes(langs).map((g) => g.join('+')));
  for (const [key, p] of workers) {
    if (!keep.has(key)) {
      workers.delete(key);
      p.then((w) => w.terminate()).catch(() => {});
    }
  }
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.target !== 'offscreen') return false;
  if (msg.type === 'warmup') {
    if (msg.langs?.length) {
      dropUnused(msg.langs);
      passes(msg.langs).forEach((g) => getWorker(g).catch(() => {}));
    }
    sendResponse({ ok: true });
    return false;
  }
  if (msg.type === 'ocr') {
    runOcr(msg).then(sendResponse, (e) =>
      sendResponse({ ok: false, error: e?.code || 'failed', message: String(e?.message || e) })
    );
    return true;
  }
  return false;
});

async function runOcr({ dataUrl, rect, viewport, langs }) {
  const t0 = performance.now();
  const bmp = await createImageBitmap(await (await fetch(dataUrl)).blob());
  // Pixels of the capture per CSS pixel of the page.
  const sx = bmp.width / viewport.w;
  const sy = bmp.height / viewport.h;
  const s = Math.abs(sx - sy) < 0.05 ? sx : Math.min(sx, sy);

  const cx = Math.max(0, Math.round(rect.x * s));
  const cy = Math.max(0, Math.round(rect.y * s));
  const cw = Math.min(bmp.width - cx, Math.round(rect.w * s));
  const ch = Math.min(bmp.height - cy, Math.round(rect.h * s));
  if (cw < 4 || ch < 4) return { ok: true, paragraphs: [], image: null };

  // The crop shown back to the user (native resolution).
  const crop = new OffscreenCanvas(cw, ch);
  const cctx = crop.getContext('2d', { willReadFrequently: true });
  cctx.drawImage(bmp, cx, cy, cw, ch, 0, 0, cw, ch);
  bmp.close();
  const pixels = cctx.getImageData(0, 0, cw, ch);

  // Tesseract reads small text much better when it is enlarged.
  const up = s >= 2 ? 1.5 : 3 - s; // 1x → 2x, 1.25x → 1.75x, 2x+ → 1.5x
  const ow = Math.round(cw * up);
  const oh = Math.round(ch * up);
  const big = new OffscreenCanvas(ow, oh);
  const bctx = big.getContext('2d');
  bctx.imageSmoothingEnabled = true;
  bctx.imageSmoothingQuality = 'high';
  bctx.drawImage(removeRules(pixels), 0, 0, ow, oh);
  const bigBlob = await big.convertToBlob({ type: 'image/png' });

  dropUnused(langs);
  const groups = passes(langs);
  // Text colour of a line (to split a heading from a differently coloured subtitle).
  const lineColor = new Map();
  const colorOf = (l) => {
    if (!lineColor.has(l)) {
      const k = up * s;
      const box = { x: l.bbox.x0 / k, y: l.bbox.y0 / k, w: (l.bbox.x1 - l.bbox.x0) / k, h: (l.bbox.y1 - l.bbox.y0) / k };
      lineColor.set(l, sampleColors(pixels, box, s).fgArr);
    }
    return lineColor.get(l);
  };
  const read = async (psm) => {
    const results = [];
    for (const g of groups) {
      const worker = await getWorker(g);
      await worker.setParameters({ tessedit_pageseg_mode: psm });
      const { data } = await worker.recognize(bigBlob, {}, { blocks: true });
      results.push(data);
    }
    return collect(mergeLines(results), up * s, colorOf);
  };
  let paras = await read('3');
  // Small selections (a single line or word) do better as "one block".
  if (!paras.length) paras = await read('6');

  for (const p of paras) {
    const { fgArr, stroke, ...c } = sampleColors(pixels, p.box, s);
    // Stroke width relative to the font size (minus ~0.6px of anti-aliasing,
    // which matters a lot for small text): regular ≈ 0.07–0.10 em, bold ≥ 0.13 em.
    Object.assign(p, c, { weight: Math.max(0, stroke - 0.6) / (p.fontSize * s) });
  }
  // Bold = clearly heavier than the body text of the same selection
  // (compared within the same script: CJK and Latin strokes differ).
  for (const cjk of [true, false]) {
    const group = paras.filter((p) => CJK_RE.test(p.text) === cjk);
    const ws = group.map((p) => p.weight).sort((a, b) => a - b);
    const body = ws[Math.floor((ws.length - 1) / 4)] ?? 0;
    const abs = cjk ? 0.11 : 0.125;
    for (const p of group) {
      p.bold = group.length > 1 ? p.weight > Math.max(body * 1.3, abs * 0.8) : p.weight > abs;
      delete p.weight;
    }
  }

  const imgBlob = await crop.convertToBlob({ type: 'image/png' });
  const image = await blobToDataUrl(imgBlob);
  return { ok: true, paragraphs: paras, image, ms: Math.round(performance.now() - t0) };
}

// Thin full-width/height lines (table borders, dashed "cut here" strips,
// underlines) make Tesseract's layout analysis treat the area as a picture and
// skip the text inside. They are painted over with the background before OCR.
function removeRules(img) {
  const { width: W, height: H, data } = img;
  const out = new ImageData(new Uint8ClampedArray(data), W, H);
  const samples = [];
  const step = Math.max(1, Math.floor((W * H) / 20000));
  for (let i = 0; i < W * H; i += step) samples.push([data[i * 4], data[i * 4 + 1], data[i * 4 + 2]]);
  const bg = [0, 1, 2].map((c) => median(samples.map((p) => p[c])));
  const ink = new Uint8Array(W * H);
  for (let i = 0; i < W * H; i += 1) {
    ink[i] = dist([data[i * 4], data[i * 4 + 1], data[i * 4 + 2]], bg) > 80 ? 1 : 0;
  }
  const rowR = new Float32Array(H);
  const colR = new Float32Array(W);
  for (let y = 0; y < H; y += 1) {
    let n = 0;
    for (let x = 0; x < W; x += 1) n += ink[y * W + x];
    rowR[y] = n / W;
  }
  for (let x = 0; x < W; x += 1) {
    let n = 0;
    for (let y = 0; y < H; y += 1) n += ink[y * W + x];
    colR[x] = n / H;
  }
  const find = (r, len) => {
    const found = [];
    const maxThick = Math.max(4, Math.round(len / 300));
    for (let i = 0; i < r.length; i += 1) {
      if (r[i] <= 0.35) continue;
      const a = i;
      let peak = 0;
      while (i < r.length && r[i] > 0.2) peak = Math.max(peak, r[i++]);
      const b = i;
      const before = r[Math.max(0, a - 3)];
      const after = r[Math.min(r.length - 1, b + 2)];
      if (b - a <= maxThick && before < peak * 0.5 && after < peak * 0.5) found.push([Math.max(0, a - 1), Math.min(r.length, b + 1)]);
    }
    return found;
  };
  const paint = (x, y) => {
    const i = (y * W + x) * 4;
    out.data[i] = bg[0];
    out.data[i + 1] = bg[1];
    out.data[i + 2] = bg[2];
  };
  for (const [a, b] of find(rowR, H)) for (let y = a; y < b; y += 1) for (let x = 0; x < W; x += 1) paint(x, y);
  for (const [a, b] of find(colR, W)) for (let x = a; x < b; x += 1) for (let y = 0; y < H; y += 1) paint(x, y);
  const c = new OffscreenCanvas(W, H);
  c.getContext('2d').putImageData(out, 0, 0);
  return c;
}

// Paragraphs in CSS pixels relative to the selection.
// Tesseract sometimes joins lines that belong to different elements (a title
// and its subtitle, a Japanese line and its romaji), so a paragraph is split
// where the script or the text size changes.
const CJK_RE = /[぀-ヿ㐀-鿿가-힯＀-￯]/;
// A bullet as Tesseract reads it: a lone mark (•, ●, *, ©, +…) or a stray
// "e"/"o", followed by a gap wider than a normal space.
function bulletOf(l) {
  const [a, b] = l.words || [];
  if (!a || !b || [...a.text].length !== 1) return false;
  if (!/[•●○◦▪■□·*©®+»›>–\-eoc]/u.test(a.text)) return false;
  const h = l.bbox.y1 - l.bbox.y0;
  return b.bbox.x0 - a.bbox.x1 > h * 0.45 || /[•●▪■]/u.test(a.text);
}
const stripBullet = (l) => (bulletOf(l) ? l.text.trim().replace(/^\S+\s+/, '') : l.text);

const scriptOf = (t) => (CJK_RE.test(t) ? 'cjk' : 'latin');

// Lines from every OCR pass; where two readings overlap, the more confident
// one wins. Returns the kept lines grouped by their original paragraph.
// Tesseract's line confidence collapses when a single character is unsure
// (a whole Japanese line drops to ~19 because of one kanji), so lines are
// judged by the average confidence of their words.
function lineConf(l) {
  const ws = (l.words || []).filter((w) => w.text.trim());
  if (!ws.length) return l.confidence;
  return ws.reduce((a, w) => a + w.confidence, 0) / ws.length;
}

function mergeLines(results) {
  const all = [];
  results.forEach((data, pass) => {
    (data.blocks || []).forEach((b, bi) => {
      (b.paragraphs || []).forEach((p, pi) => {
        for (const l of p.lines || []) {
          if (l.text.trim() && lineConf(l) > 30) all.push({ l, key: `${pass}.${bi}.${pi}` });
        }
      });
    });
  });
  const area = (b) => Math.max(0, b.x1 - b.x0) * Math.max(0, b.y1 - b.y0);
  const overlap = (a, b) => {
    const i = { x0: Math.max(a.x0, b.x0), y0: Math.max(a.y0, b.y0), x1: Math.min(a.x1, b.x1), y1: Math.min(a.y1, b.y1) };
    return area(i) / Math.max(1, Math.min(area(a), area(b)));
  };
  // A Latin model "reading" big CJK glyphs can still report a decent confidence,
  // so a line that the CJK model reads as real CJK text gets a head start.
  const cjkChars = (t) => (t.match(/[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]/g) || []).length;
  const score = (c) => lineConf(c.l) * (cjkChars(c.l.text) >= 2 ? 1.5 : 1);
  const kept = [];
  for (const c of all.slice().sort((a, b) => score(b) - score(a))) {
    if (!kept.some((k) => overlap(k.l.bbox, c.l.bbox) > 0.4)) kept.push(c);
  }
  const keptSet = new Set(kept);
  const groups = new Map();
  for (const c of all) {
    if (!keptSet.has(c)) continue;
    if (!groups.has(c.key)) groups.set(c.key, []);
    groups.get(c.key).push(c.l);
  }
  // Reading order: top to bottom, then left to right (right to left for vertical CJK).
  return [...groups.values()].sort((a, b) => a[0].bbox.y0 - b[0].bbox.y0 || a[0].bbox.x0 - b[0].bbox.x0);
}

function collect(paragraphs, k, colorOf) {
  const out = [];
  for (const lines of paragraphs) {
    {
      let group = [];
      const flush = () => {
        if (group.length) out.push(...toParagraph(group, k));
        group = [];
      };
      for (const l of lines) {
        const prev = group[group.length - 1];
        if (prev) {
          const vert = isVertical(l);
          // Size: column width for vertical text; x-height for horizontal text
          // (bbox height changes with ascenders/descenders such as "p" or "y").
          const xh = (x) => (x.rowAttributes ? x.rowAttributes.rowHeight - x.rowAttributes.ascenders - x.rowAttributes.descenders : 0);
          const size = (x) => (vert ? x.bbox.x1 - x.bbox.x0 : xh(x) > 2 ? xh(x) : x.bbox.y1 - x.bbox.y0);
          const ratio = size(l) / Math.max(1, size(prev));
          const recolor = colorOf && dist(colorOf(l), colorOf(prev)) > 70;
          // A wide gap between lines or a bullet means a new item.
          const gap = vert ? prev.bbox.x0 - l.bbox.x1 : l.bbox.y0 - prev.bbox.y1;
          const spaced = gap > size(prev) * 1.6;
          if (scriptOf(l.text) !== scriptOf(prev.text) || ratio > 1.15 || ratio < 0.87 || recolor || spaced || bulletOf(l)) flush();
        }
        group.push(l);
      }
      flush();
    }
  }
  return out;
}

const isVertical = (l) => l.bbox.y1 - l.bbox.y0 > (l.bbox.x1 - l.bbox.x0) * 1.6 && CJK_RE.test(l.text);

function toParagraph(lines, k) {
  const cjk = CJK_RE.test(lines.map((l) => l.text).join(''));
  const vertical = lines.every(isVertical);
  let text = lines
    .map((l) => stripBullet(l).replace(/\s+/g, ' ').trim())
    .join(cjk ? '' : ' ')
    .replace(/(\w)- (\w)/g, '$1$2'); // hyphenated line breaks
  if (cjk) {
    // Tesseract puts spaces between CJK characters and before punctuation.
    const C = '\\u3000-\\u30ff\\u3400-\\u9fff\\uac00-\\ud7af\\uff00-\\uffef';
    text = text
      .replace(new RegExp(`([${C}])\\s+(?=[${C}!?！？。、,.…])`, 'g'), '$1')
      .replace(new RegExp(`([!?！？。、])\\s+(?=[${C}])`, 'g'), '$1');
  }
  if (cjk) {
    // A full-width "？" is often read as "2?".
    text = text.replace(new RegExp('([\\u3040-\\u30ff\\u3400-\\u9fff])2\\?', 'g'), '$1？');
  }
  if (!/[\p{L}\p{N}]/u.test(text)) return [];
  // Lines and borders read as "ーー", "一一", "|||".
  if (cjk && !/[\p{L}\p{N}]/u.test(text.replace(/[ー一丨ノ|｜ｰ\-_=~〜・]/gu, ''))) return [];
  // Lone Latin letters are usually noise (a speech-bubble outline, an icon).
  if (!cjk && (text.match(/\p{L}/gu) || []).length < 2 && !/\p{N}/u.test(text)) return [];
  const conf = lines.reduce((a, l) => a + lineConf(l), 0) / lines.length;
  if (conf < 40 && text.length < 4) return [];
  // Keep the bullet visible: the patch starts after it.
  const x0 = Math.min(...lines.map((l) => (bulletOf(l) ? l.words[1].bbox.x0 : l.bbox.x0)));
  const y0 = Math.min(...lines.map((l) => l.bbox.y0));
  const x1 = Math.max(...lines.map((l) => l.bbox.x1));
  const y1 = Math.max(...lines.map((l) => l.bbox.y1));
  const avg = (f) => lines.reduce((a, l) => a + f(l), 0) / lines.length;
  const lh = vertical ? avg((l) => l.bbox.x1 - l.bbox.x0) : avg((l) => l.bbox.y1 - l.bbox.y0);
  const row = avg((l) => l.rowAttributes?.rowHeight || 0);
  const asc = avg((l) => l.rowAttributes?.ascenders || 0);
  const desc = avg((l) => l.rowAttributes?.descenders || 0);
  const pitch = !vertical && lines.length > 1 ? (lines[lines.length - 1].bbox.y0 - lines[0].bbox.y0) / (lines.length - 1) : 0;
  // Latin: x-height ≈ 0.53em for most sans fonts. CJK glyphs fill ~0.9em.
  const fontSize = cjk ? lh / 0.9 : row - asc - desc > 2 ? (row - asc - desc) / 0.53 : lh;
  return [{
    text,
    lines: lines.length,
    conf: Math.round(conf),
    vertical,
    box: { x: x0 / k, y: y0 / k, w: (x1 - x0) / k, h: (y1 - y0) / k },
    lineHeight: lh / k,
    fontSize: fontSize / k,
    pitch: pitch / k
  }];
}

// Background = median colour of the ring around the box.
// Text = the pixels inside the box that differ most from the background.
function sampleColors(img, box, s) {
  const { width: W, height: H, data } = img;
  const x0 = clamp(Math.floor(box.x * s) - 3, 0, W - 1);
  const y0 = clamp(Math.floor(box.y * s) - 3, 0, H - 1);
  const x1 = clamp(Math.ceil((box.x + box.w) * s) + 3, 0, W - 1);
  const y1 = clamp(Math.ceil((box.y + box.h) * s) + 3, 0, H - 1);
  const ring = [];
  const px = (x, y) => {
    const i = (y * W + x) * 4;
    return [data[i], data[i + 1], data[i + 2]];
  };
  for (let x = x0; x <= x1; x += 1) ring.push(px(x, y0), px(x, y1));
  for (let y = y0; y <= y1; y += 1) ring.push(px(x0, y), px(x1, y));
  const bg = [0, 1, 2].map((c) => median(ring.map((p) => p[c])));

  const inner = [];
  const step = Math.max(1, Math.floor(((x1 - x0) * (y1 - y0)) / 40000));
  let n = 0;
  for (let y = y0 + 3; y < y1 - 3; y += 1) {
    for (let x = x0 + 3; x < x1 - 3; x += 1) {
      if (n++ % step) continue;
      const p = px(x, y);
      inner.push([dist(p, bg), p]);
    }
  }
  let fg;
  if (inner.length) {
    inner.sort((a, b) => b[0] - a[0]);
    const top = inner.slice(0, Math.max(1, Math.floor(inner.length * 0.08)));
    fg = [0, 1, 2].map((c) => Math.round(top.reduce((a, t) => a + t[1][c], 0) / top.length));
  }
  if (!fg || dist(fg, bg) < 60) fg = lum(bg) > 140 ? [20, 20, 20] : [245, 245, 245];
  // Busy backgrounds (photos): the ring varies a lot → use a solid chip.
  const spread = ring.reduce((a, p) => a + dist(p, bg), 0) / ring.length;
  // Stroke width: median length of horizontal ink runs inside the box.
  const thr = dist(fg, bg) / 2;
  const runs = [];
  const rowStep = Math.max(1, Math.floor((y1 - y0) / 24));
  for (let y = y0 + 1; y < y1; y += rowStep) {
    let run = 0;
    for (let x = x0; x <= x1; x += 1) {
      if (dist(px(x, y), bg) > thr) run += 1;
      else if (run) {
        runs.push(run);
        run = 0;
      }
    }
    if (run) runs.push(run);
  }
  const stroke = runs.length ? median(runs) : 0;
  return { bg: rgb(bg), fg: rgb(fg), fgArr: fg, busy: spread > 40, stroke };
}

const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const median = (arr) => {
  const s = arr.slice().sort((a, b) => a - b);
  return s[s.length >> 1] ?? 0;
};
const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
const lum = (c) => 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
const rgb = (c) => `rgb(${c[0]}, ${c[1]}, ${c[2]})`;

function blobToDataUrl(blob) {
  return new Promise((res, rej) => {
    const r = new FileReader();
    r.onload = () => res(r.result);
    r.onerror = rej;
    r.readAsDataURL(blob);
  });
}
