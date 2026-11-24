// Copies the OCR engine from node_modules into extension/vendor.
// Only needed to update Tesseract.js: the files are already committed.
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1')), '..');
const nm = path.join(root, 'node_modules');
const out = path.join(root, 'extension', 'vendor');
fs.mkdirSync(path.join(out, 'core'), { recursive: true });

const copy = (from, to, strip = false) => {
  let data = fs.readFileSync(path.join(nm, from));
  if (strip) data = Buffer.from(data.toString('utf8').replace(/^\/\/# sourceMappingURL=.*$/m, ''));
  fs.writeFileSync(path.join(out, to), data);
  console.log('✓', to);
};
copy('tesseract.js/dist/tesseract.min.js', 'tesseract.min.js', true);
copy('tesseract.js/dist/worker.min.js', 'worker.min.js', true);
copy('tesseract.js/LICENSE.md', 'LICENSE-tesseract.js.md');
// Psittacus only uses the LSTM engine, so only the *-lstm cores are shipped.
for (const f of ['tesseract-core-lstm.wasm.js', 'tesseract-core-simd-lstm.wasm.js', 'tesseract-core-relaxedsimd-lstm.wasm.js']) {
  copy(`tesseract.js-core/${f}`, `core/${f}`);
}
copy('tesseract.js-core/LICENSE', 'core/LICENSE-tesseract.js-core');
