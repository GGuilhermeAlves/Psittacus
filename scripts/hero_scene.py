# Run: python3 scripts/hero_scene.py  (needs numpy, pillow, matplotlib and the Unifont font)
# Pixel-art hero for the README: grey parrots on a branch at dusk, each "repeating"
# a word in another language. Painted at 400x150 and scaled 4x (nearest).
import numpy as np
from PIL import Image, ImageDraw, ImageFont
W, H, S = 400, 150, 4
hexc = lambda h: np.array([int(h.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)], float)
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16 + 1 / 32
TH = np.tile(BAYER, (H // 4 + 1, W // 4 + 1))[:H, :W]
img = np.zeros((H, W, 3))
yy, xx = np.mgrid[0:H, 0:W]

def ramp(t, cols):
    cols = [hexc(c) for c in cols]; n = len(cols) - 1
    v = np.clip(t, 0, 1) * n; i = np.minimum(np.floor(v).astype(int), n - 1); f = v - i
    return np.stack(cols)[i + (f > TH)]

# sky: wine at the top to warm dusk at the horizon
sky = ramp(yy / 118, ['#1c0b12', '#2e1019', '#4A1C22', '#6c2a2e', '#934035', '#bd6340', '#dc8f55'])
img[:] = sky
# sun + glow
d = np.hypot(xx - 322, (yy - 108) * 1.1)
glow = np.clip(1 - d / 70, 0, 1) ** 2
img = np.where((glow > 0)[..., None], ramp(np.clip(yy / 118 + glow * .55, 0, 1), ['#1c0b12', '#2e1019', '#4A1C22', '#6c2a2e', '#934035', '#bd6340', '#dc8f55', '#f0b46a']), img)
img[d < 15] = hexc('#f6c98a'); img[(d < 15) & (d > 13)] = hexc('#efb070')
# a few stars at the top
rng = np.random.default_rng(7)
for _ in range(38):
    x, y = rng.integers(0, W), rng.integers(0, 40)
    img[y, x] = hexc('#e9c9c0') * (.5 + .5 * rng.random())
# far forest silhouettes (two layers)
def hills(base, amp, freq, phase, col, dith=None):
    h = base + amp * (np.sin(xx[0] * freq + phase) * .6 + np.sin(xx[0] * freq * 2.7 + phase * 1.7) * .3 + np.sin(xx[0] * freq * 6.1) * .1)
    for x in range(W):
        top = int(h[x])
        img[top:, x] = hexc(col)
        if dith is not None and top > 0:
            for y in range(max(0, top - 2), top):
                if TH[y, x] < .35: img[y, x] = hexc(col)
hills(104, 7, .045, 0.0, '#5b2630', True)
hills(114, 6, .07, 2.0, '#3c1820', True)
hills(126, 4, .11, 4.0, '#24101a', True)
img[134:, :] = hexc('#170a10')

# ---------- big branch from the left ----------
def branch_y(x): return int(round(104 - (x - 10) * .045 + 2.2 * np.sin(x * .05)))
for x in range(0, 352):
    y = branch_y(x); th = 9 if x < 60 else (8 if x < 220 else 7)
    if x > 320: th = 5
    for k in range(th):
        c = '#9a6c46' if k == 0 else ('#7a5638' if k < 3 else ('#5e4130' if k < th - 1 else '#3a2619'))
        if 2 <= k < th - 1 and (x * 7 + k * 5) % 17 < 2: c = '#4a3324'
        img[y + k, x] = hexc(c)
    img[y - 1, x] = hexc('#24140e') if x % 3 else img[y - 1, x]
# leaf clusters
def leaves(cx, cy, r):
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r - 3, cx + r + 4):
            if 0 <= x < W and 0 <= y < H and ((x - cx) / (r + 3)) ** 2 + ((y - cy) / r) ** 2 <= 1:
                t = .5 + .5 * np.sin(x * 1.3 + y * 2.1) - (y - cy) / (2 * r)
                img[y, x] = ramp(np.full((1, 1), np.clip(t, 0, 1)), ['#10211a', '#1d3a26', '#2c5232', '#3f6e3c'])[0, 0] if TH[y, x] < .9 else img[y, x]
for cx, cy, r in [(8, 92, 9), (30, 86, 7), (58, 112, 6), (140, 112, 5), (300, 98, 6), (338, 92, 5), (352, 96, 4)]:
    leaves(cx, cy, r)

# ---------- painted parrots (same pipeline as the icon) ----------
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import icon_art as art
KEY = '#FF00FF'
def painted(N=90, flip=False, look=None):
    reg, T, halo, order = art.STUDIES['full']()
    order = [k for k in order if k != 'branch']
    px = np.array(art.make((reg, T, halo * 0, order), N, KEY, halo_amt=0)).astype(int)
    key = hexc(KEY).astype(int); dark = (hexc(KEY) * .55).astype(int)
    alpha = ~np.all(px == key, axis=2)
    outline = np.all(np.abs(px - dark) <= 1, axis=2)
    px[outline] = hexc('#140a0d')
    if flip: px, alpha = px[:, ::-1], alpha[:, ::-1]
    return px, alpha
SPRITE = painted()
SPRITE_F = painted(flip=True)
BRANCH_ROW = 63          # row of the sprite that sits on the branch top
def parrot(x0, flip=False):
    px, al = SPRITE_F if flip else SPRITE
    yb = branch_y(x0 + 45)
    y0 = yb - BRANCH_ROW
    for j in range(px.shape[0]):
        for i in range(px.shape[1]):
            if al[j, i] and j_ok(y0 + j, x0 + i): img[y0 + j, x0 + i] = px[j, i]
def j_ok(y, x): return 0 <= y < H and 0 <= x < W
for x0, flip in [(56, False), (150, True), (250, False)]:
    parrot(x0, flip)

# ---------- speech bubbles (Unifont, pixel-exact) ----------
FONT = ImageFont.truetype('/usr/share/fonts/opentype/unifont/unifont_jp.otf', 16)
def bubble(text, x, y, tail_x, tail_dir=1):
    tmp = Image.new('1', (200, 20), 0); dr = ImageDraw.Draw(tmp); dr.fontmode = '1'
    dr.text((0, 0), text, font=FONT, fill=1)
    bb = tmp.getbbox(); g = np.array(tmp.crop((bb[0], 0, bb[2], 17)))
    w, h = g.shape[1] + 10, 21
    for j in range(h):
        for i in range(w):
            edge = j in (0, h - 1) or i in (0, w - 1)
            corner = (j in (0, h - 1)) and (i in (0, w - 1))
            if corner: continue
            img[y + j, x + i] = hexc('#140a0d') if edge else hexc('#FBF7F2')
    for j in range(g.shape[0]):
        for i in range(g.shape[1]):
            if g[j, i]: img[y + 2 + j, x + 5 + i] = hexc('#4A1C22')
    # tail
    for k in range(4):
        for i in range(4 - k):
            img[y + h - 1 + k, tail_x + i * tail_dir] = hexc('#FBF7F2')
        img[y + h - 1 + k, tail_x - tail_dir] = hexc('#140a0d')
        img[y + h - 1 + k, tail_x + (4 - k) * tail_dir] = hexc('#140a0d')
    img[y + h + 3, tail_x] = hexc('#140a0d')
bubble('Olá!', 86, 16, 104, 1)
bubble('こんにちは', 146, 14, 190, -1)
bubble('Hello!', 290, 16, 306, 1)

out = Image.fromarray(img.astype(np.uint8), 'RGB').resize((W * S, H * S), Image.NEAREST)
out.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'hero.png'))
