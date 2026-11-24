# Psittacus erithacus (grey parrot) — painted at 1024px, reduced to 56x56 with
# Bayer dithering, same pipeline as the Glaux owl and the Lampyris firefly.
import numpy as np
from PIL import Image, ImageDraw

R = 1024
YY0, XX0 = (np.mgrid[0:R, 0:R] + .5) / R
yy, xx = YY0, XX0

def view(z=1.0, cx=.5, cy=.5):
    """Zoom the painting: z > 1 brings the bird closer (centred on cx, cy)."""
    global xx, yy
    xx = cx + (XX0 - .5) / z
    yy = cy + (YY0 - .5) / z

def ell(cx, cy, rx, ry, a=0.0):
    ca, sa = np.cos(a), np.sin(a)
    dx, dy = xx - cx, yy - cy
    u, v = dx * ca + dy * sa, -dx * sa + dy * ca
    return (u / rx) ** 2 + (v / ry) ** 2

def poly(pts):
    from matplotlib.path import Path
    p = Path(pts)
    return p.contains_points(np.stack([xx.ravel(), yy.ravel()], 1)).reshape(R, R)

def seg(x0, y0, x1, y1, w):
    px, py = xx - x0, yy - y0; dx, dy = x1 - x0, y1 - y0
    t = np.clip((px * dx + py * dy) / (dx * dx + dy * dy), 0, 1)
    return np.hypot(px - t * dx, py - t * dy) < w

def hexc(h):
    h = h.lstrip('#'); return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float)

def scallop(rows, cols, phase=0.0):
    """Feathers: rows of U-shaped edges. Returns 0..1, 1 on the pale edge of each feather."""
    r = yy * rows
    row = np.floor(r)
    off = (row % 2) * .5
    u = (xx * cols + off + phase) % 1.0
    v = r - row
    edge = v - .28 * (1 - (2 * u - 1) ** 2)   # arc
    return np.clip(1 - np.abs(edge - .62) / .16, 0, 1)

# ---------------- palette (real colours of the species) ----------------
RAMPS = {
    'body':   ['#4C5258', '#6B7279', '#8A9198', '#A9AFB5', '#C6CBD0'],
    'wing':   ['#2E3338', '#454B51', '#626970', '#838A91', '#A6ACB2', '#C3C8CC'],
    'head':   ['#6B7279', '#8C939A', '#AEB4BA', '#CDD1D5', '#E2E5E7'],
    'face':   ['#BFC3C6', '#DDE0E2', '#F3F4F5'],
    'iris':   ['#CDBE84', '#EDE2AE', '#FAF4D6'],
    'pupil':  ['#0B0B0C', '#1A1A1C'],
    'beak':   ['#0C0D0F', '#1C1E22', '#33373D', '#525860', '#737A82'],
    'tail':   ['#6E130F', '#A81D16', '#D1352A', '#EC5A45'],
    'branch': ['#3A2819', '#5C4129', '#7E5C3C', '#9C7850'],
    'feet':   ['#34383C', '#4F555A', '#6A7076'],
    'lid':    ['#8E959B', '#AEB4B9', '#C9CDD1'],
    'nostril': ['#1A1B1E', '#2E3136'],
    'lowbeak': ['#1F2125', '#34383E', '#4B5058'],
    'wing2':  ['#2E3338', '#454B51', '#5E656C'],
    'rock':   ['#2E2620', '#4A3E33', '#6A5A4A', '#8C7A64', '#A89478'],
    'moss':   ['#3E4A22', '#5B6B2E', '#7C8C3C'],
    'leg':    ['#3A3F44', '#585E64', '#767D84'],
    'claw':   ['#141517', '#2A2C30'],
}
THR = {'nostril': .25, 'lowbeak': .4, 'claw': .3, 'leg': .4, 'moss': .5, 'pupil': .25, 'iris': .3, 'feet': .4, 'beak': .45}
LIGHT = hexc('#FFFFFF')
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16 + 1 / 32

def shade(cx, cy, rx, ry, lx=-.35, ly=-.45):
    """Round volume lit from the top-left: 0 (shadow) .. 1 (light)."""
    nx, ny = (xx - cx) / rx, (yy - cy) / ry
    return np.clip(.55 + .45 * (nx * lx + ny * ly) - .25 * np.clip(nx * nx + ny * ny - .6, 0, 1), 0, 1)

# ---------------- FRONT VIEW ----------------
def body_front(reg, T):
    """Perch, tail, body, folded wings and feet seen from the front."""
    tail = poly([(.41, .74), (.59, .74), (.62, .97), (.38, .97)])
    reg['tail'] = tail; T[tail] = (.6 + .3 * np.clip(1 - np.abs(xx - .5) / .12, 0, 1) - .3 * np.clip((yy - .88) / .08, 0, 1))[tail]
    br = (yy > .815) & (yy < .868) & (xx > .02) & (xx < .98)
    reg['branch'] = br; T[br] = (.8 - 9 * (yy - .815) + .08 * np.sin(xx * 90))[br]
    e = ell(.5, .575, .195, .27)
    bo = e <= 1
    reg['body'] = bo
    neck = np.exp(-((yy - .43) / .045) ** 2) * (np.abs(xx - .5) < .17)
    T[bo] = np.clip(shade(.5, .575, .195, .27) * .78 + .25 * scallop(24, 8) - .28 * neck, 0, 1)[bo]
    reg['wing'] = np.zeros((R, R), bool)
    for s in (-1, 1):
        we = ell(.5 + s * .15, .60, .075, .22, -s * .1)
        w = (we <= 1) & bo
        reg['wing'] |= w
        tip = np.clip((yy - .72) / .1, 0, 1)
        rim = np.clip((we - .7) / .3, 0, 1)          # dark rim → wing reads apart from the chest
        T[w] = np.clip(.42 + .38 * scallop(16, 6, .25) - .3 * tip - .35 * rim + (.08 if s < 0 else -.06), 0, 1)[w]
    ft = np.zeros((R, R), bool)
    for s in (-1, 1):
        for dx in (-.025, .025):
            ft |= seg(.5 + s * .085 + dx, .80, .5 + s * .085 + dx * 1.3, .85, .017)
    reg['feet'] = ft; T[ft] = .5

def rock_front(reg, T, slim=True):
    """Upright on a mossy stump: legs and the red under-tail show between them."""
    top = .82 + .012 * np.sin(xx * 31) + .02 * np.clip(np.abs(xx - .5) - .14, 0, 1) * 6
    rock = (yy > top) & (np.abs(xx - .5) < .3 + (yy - .82) * .25)
    reg['rock'] = rock
    T[rock] = np.clip(.75 - 2.2 * (yy - top) - .25 * (xx > .64) + .12 * np.sin(xx * 140 + yy * 60), 0, 1)[rock]
    moss = rock & (np.sin(xx * 97) * np.sin(yy * 83 + xx * 20) > .55) & (yy > .87)
    reg['moss'] = moss; T[moss] = .6
    red = ell(.5, .775, .085, .065) <= 1
    reg['tail'] = red; T[red] = (.65 - .3 * np.clip((yy - .78) / .05, 0, 1))[red]
    leg = np.zeros((R, R), bool); claw = np.zeros((R, R), bool)
    for x0 in (.445, .555):
        leg |= seg(x0, .74, x0, .82, .022)
        for dx in (-.03, 0, .03):
            leg |= seg(x0, .82, x0 + dx * 1.4, .85, .012)
            claw |= ell(x0 + dx * 1.45, .86, .009, .014) <= 1
    reg['leg'] = leg; T[leg] = (.55 - 2 * (yy - .76))[leg]
    reg['claw'] = claw; T[claw] = .3
    cy, ry, rx = (.54, .235, .17) if slim else (.56, .25, .19)
    bo = ell(.5, cy, rx, ry) <= 1
    reg['body'] = bo
    neck = np.exp(-((yy - .40) / .045) ** 2) * (np.abs(xx - .5) < .16)
    T[bo] = np.clip(shade(.5, cy, rx, ry) * .78 + .25 * scallop(26, 9) - .28 * neck, 0, 1)[bo]
    reg['wing'] = np.zeros((R, R), bool)
    for s_ in (-1, 1):
        we = ell(.5 + s_ * (rx - .045), cy + .03, .068, ry * .9, -s_ * .08)
        w = (we <= 1)
        reg['wing'] |= w
        tip = np.clip((yy - (cy + .13)) / .1, 0, 1)
        rim = np.clip((we - .7) / .3, 0, 1)
        T[w] = np.clip(.42 + .38 * scallop(16, 6, .25) - .3 * tip - .35 * rim + (.08 if s_ < 0 else -.06), 0, 1)[w]

def front(pdx=0.0, lid=0.0, tilt=0.0, base='branch', hy=.30, look_up=0.0, yaw=0.0):
    reg, T = {}, np.zeros((R, R))
    (rock_front if base == 'rock' else body_front)(reg, T)
    o = rotated(tilt, .5, .38) if tilt else None
    # yaw > 0: the head turns a little to the right — the face slides right and
    # the far (right) eye gets narrower, close to the edge of the head.
    hc = .5 + yaw * .03
    fcx = .5 + yaw * .075 + max(0.0, yaw - .6) * .22   # past ~60% the face swings out toward the profile
    hd = (ell(hc, hy, .165, .158) <= 1) | ((ell(.5, .40, .15, .12) <= 1) & (yy < .42))
    reg['head'] = hd
    T[hd] = np.clip(shade(hc, hy, .165, .158) * .78 + .2 * scallop(34, 12), 0, 1)[hd]
    fc = np.zeros((R, R), bool)
    eyes = []
    for s in (-1, 1):
        k = 1 - yaw * (.9 if s > 0 else -.25)          # foreshortening
        ex = fcx + s * .1 * (1 - yaw * (.45 if s > 0 else .05))
        eyes.append((ex, k))
        fc |= ell(fcx + s * .088 * (1 - yaw * (.45 if s > 0 else .05)), hy, .074 * k, .064, -s * .08) <= 1
    fc |= ell(fcx, hy + .005, .05, .026) <= 1
    reg['face'] = fc; T[fc] = (.88 - .35 * np.clip(ell(fcx, hy, .16, .08), 0, 1))[fc]
    ir = np.zeros((R, R), bool); pu = np.zeros((R, R), bool); ld = np.zeros((R, R), bool)
    eyes = [(ex, k) for ex, k in eyes if k > .42]
    for ex, k in eyes:
        ey = hy - .008
        ir |= ell(ex, ey, .036 * k, .036) <= 1
        pu |= ell(ex + pdx * .018 * k, ey - look_up * .012, .019 * max(k, .75), .019) <= 1
        if lid:
            ld |= (ell(ex, ey, .043 * k, .043) <= 1) & (yy < ey - .036 + lid * .05)
    reg['iris'] = ir; T[ir] = .7
    reg['pupil'] = pu; T[pu] = .2
    if lid: reg['lid'] = ld; T[ld] = .45
    # eyes are re-drawn pixel by pixel after the reduction (see stamp_eyes)
    reg['_eyes'] = [(ex, hy - .008, k, pdx, look_up, lid, tilt) for ex, k in eyes]
    # beak: solid black hook with a paler ridge on top (no stray highlight)
    bx, hook = fcx, yaw * .03 + max(0, yaw - .35) * .09
    wf = 1 - .45 * yaw                     # the beak looks narrower as the head turns
    bk = poly([(bx - .032 * wf, hy + .01), (bx + .032 * wf, hy + .01), (bx + .05 * wf + hook * .5, hy + .05), (bx + .042 * wf + hook, hy + .1),
               (bx + .018 * wf + hook, hy + .148), (bx + hook * .9, hy + .168), (bx - .018 * wf + hook * .55, hy + .14),
               (bx - .04 * wf + hook * .25, hy + .095), (bx - .05 * wf, hy + .05)])
    reg['beak'] = bk
    ridge = np.clip(1 - np.abs(xx - (bx + hook * .3)) / .012, 0, 1) * np.clip(1 - (yy - (hy + .02)) / .07, 0, 1)
    T[bk] = np.clip(.18 + .5 * ridge - .1 * np.clip((yy - (hy + .12)) / .04, 0, 1), 0, 1)[bk]
    if o is not None: restore(o)
    halo = np.exp(-((xx - .5) ** 2 / .09 + (yy - .42) ** 2 / .09))
    order = ['rock', 'moss', 'tail', 'branch', 'wing', 'body', 'leg', 'claw', 'feet', 'head', 'face', 'iris', 'pupil', 'lid', 'beak']
    return reg, np.clip(T, 0, 1), halo, order

# ---------------- BODY FROM THE FRONT, HEAD TURNED: SIDE-EYE ----------------
def sideeye(look_back=True, lid=False, tilt=0.0, body=None):
    reg, T = {}, np.zeros((R, R))
    (body or body_front)(reg, T)
    o = rotated(tilt, .47, .36) if tilt else None
    hx, hy = .47, .30
    hd = (ell(hx, hy, .165, .155) <= 1) | ((ell(.5, .40, .15, .12) <= 1) & (yy < .42))
    reg['head'] = hd
    T[hd] = np.clip(shade(hx, hy, .165, .155, .1, -.6) * .82 + .16 * scallop(34, 12), 0, 1)[hd]
    fc = ell(hx + .085, .295, .085, .068, .15) <= 1
    reg['face'] = fc; T[fc] = (.88 - .35 * np.clip(ell(hx + .085, .295, .085, .068), 0, 1))[fc]
    ex = hx + .08
    ir = ell(ex, .285, .038, .038) <= 1
    # the pupil sits at the back of the eye: the parrot is looking at you sideways
    pu = ell(ex - (.017 if look_back else -.008), .287, .021, .021) <= 1
    reg['iris'] = ir; T[ir] = .7
    reg['pupil'] = pu; T[pu] = .2
    if lid:   # half-closed upper lid: the unimpressed look
        lidm = (ell(ex, .285, .046, .046) <= 1) & (yy < .279)
        reg['lid'] = lidm; T[lidm] = .45
    dx = hx + .165 - .735          # beak hooked out to the right of the head
    upm = poly([(x + dx, y) for x, y in [(.725, .245), (.77, .25), (.81, .28), (.83, .325), (.828, .37), (.812, .405),
                                          (.80, .37), (.785, .345), (.755, .338), (.725, .335)]])
    low = poly([(x + dx, y) for x, y in [(.725, .335), (.765, .34), (.778, .37), (.75, .39), (.725, .375)]])
    reg['beak'] = upm | low
    T[upm] = np.clip(.2 + .55 * np.clip(1 - np.hypot((xx - (.765 + dx)) / .04, (yy - .27) / .025), 0, 1), 0, 1)[upm]
    T[low] = .35
    if o is not None: restore(o)
    halo = np.exp(-((xx - .5) ** 2 / .09 + (yy - .42) ** 2 / .09))
    return reg, np.clip(T, 0, 1), halo, ['tail', 'branch', 'body', 'wing', 'feet', 'head', 'face', 'iris', 'pupil', 'lid', 'beak']

# ---------------- SIDE VIEW (profile facing right) ----------------
def side():
    reg, T = {}, np.zeros((R, R))
    tail = poly([(.33, .68), (.44, .72), (.40, .95), (.27, .93)])
    reg['tail'] = tail; T[tail] = (.7 - .45 * np.clip((yy - .82) / .13, 0, 1))[tail]
    br = (yy > .80) & (yy < .85) & (xx > .06) & (xx < .94)
    reg['branch'] = br; T[br] = (.75 - 8 * (yy - .80) + .08 * np.sin(xx * 90))[br]
    bo = ell(.50, .55, .17, .28, -.38) <= 1
    reg['body'] = bo
    T[bo] = np.clip(shade(.50, .55, .17, .28, .3, -.6) * .8 + .2 * scallop(26, 9), 0, 1)[bo]
    wg = (ell(.44, .58, .12, .25, -.42) <= 1) & bo
    reg['wing'] = wg
    tip = np.clip((yy - .70) / .12, 0, 1)
    T[wg] = np.clip(.42 + .38 * scallop(18, 7, .25) - .35 * tip, 0, 1)[wg]
    ft = np.zeros((R, R), bool)
    for x in (.50, .57):
        ft |= seg(x, .78, x + .01, .83, .018)
    reg['feet'] = ft; T[ft] = .5
    hd = ell(.6, .29, .15, .14) <= 1
    reg['head'] = hd
    T[hd] = np.clip(shade(.6, .29, .15, .14, .1, -.6) * .85 + .14 * scallop(40, 14), 0, 1)[hd]
    fc = ell(.675, .29, .075, .06, .2) <= 1
    reg['face'] = fc; T[fc] = (.85 - .35 * np.clip(ell(.685, .295, .085, .072), 0, 1))[fc]
    ir = ell(.668, .28, .034, .034) <= 1
    pu = ell(.673, .28, .018, .018) <= 1
    reg['iris'] = ir; T[ir] = .7
    reg['pupil'] = pu; T[pu] = .2
    # hooked beak: upper mandible curving down past the lower one
    upm = poly([(.725, .245), (.77, .25), (.81, .28), (.83, .325), (.828, .37), (.812, .405),
                (.80, .37), (.785, .345), (.755, .338), (.725, .335)])
    low = poly([(.725, .335), (.765, .34), (.778, .37), (.75, .39), (.725, .375)])
    reg['beak'] = upm | low
    T[upm] = np.clip(.2 + .55 * np.clip(1 - np.hypot((xx - .765) / .04, (yy - .27) / .025), 0, 1), 0, 1)[upm]
    T[low] = .35
    halo = np.exp(-((xx - .55) ** 2 / .09 + (yy - .40) ** 2 / .09))
    order = ['tail', 'branch', 'body', 'wing', 'feet', 'head', 'face', 'iris', 'pupil', 'beak']
    return reg, np.clip(T, 0, 1), halo, order

def rotated(angle, cx, cy):
    """Temporarily rotate the canvas around (cx, cy) — used to tilt the head."""
    global xx, yy
    ox, oy = xx, yy
    ca, sa = np.cos(angle), np.sin(angle)
    dx, dy = xx - cx, yy - cy
    xx, yy = cx + dx * ca - dy * sa, cy + dx * sa + dy * ca
    return ox, oy

def restore(o):
    global xx, yy
    xx, yy = o

def zoomed(fn, z=1.12, cy=.55, cx=.5, **kw):
    def run():
        view(z, cx, cy)
        try:
            out = fn(**kw)
            out[0]['_view'] = (z, cx, cy)
            return out
        finally:
            view()
    return run

def stamp_eyes(img, reg, N):
    """Crisp hand-placed eyes: pale iris, 2x2 pupil, optional lid — no dither noise."""
    if '_eyes' not in reg: return img
    z, cx, cy = reg.get('_view', (1, .5, .5))
    a = np.array(img).astype(int)
    iris, iris_d, pupil, lidc, white = hexc('#F2EBBE'), hexc('#D6C68A'), hexc('#0E0E10'), hexc('#9AA1A7'), hexc('#EEF0F1')
    for ex, ey, k, pdx, up, lid, tilt in reg['_eyes']:
        if tilt:   # eye centres were placed in the tilted frame: rotate back
            ca, sa = np.cos(-tilt), np.sin(-tilt)
            dx, dy = ex - .5, ey - .38
            ex, ey = .5 + dx * ca - dy * sa, .38 + dx * sa + dy * ca
        px = ((ex - cx) * z + .5) * N
        py = ((ey - cy) * z + .5) * N
        if k > 1.1:   # big eye: 5x5 iris with a thin grey eye-ring, 2x2 pupil and a catch-light
            x0, y0 = int(round(px - 2.5)), int(round(py - 2.5))
            ring = hexc('#9BA1A7')
            for yy_ in range(-1, 6):
                for xx_ in range(-1, 6):
                    corner = (yy_ in (-1, 5)) and (xx_ in (-1, 0, 4, 5)) or (xx_ in (-1, 5)) and (yy_ in (0, 4))
                    if (yy_ in (-1, 5) or xx_ in (-1, 5)) and not corner: a[y0 + yy_, x0 + xx_] = ring
            for yy_ in range(5):
                for xx_ in range(5):
                    if yy_ in (0, 4) and xx_ in (0, 4): continue
                    a[y0 + yy_, x0 + xx_] = iris if yy_ < 3 else iris_d
            pc = x0 + 2 + int(np.sign(pdx)); pr = y0 + 1 - (1 if up else 0)
            for yy_ in range(2):
                for xx_ in range(2):
                    a[pr + yy_, pc + xx_ - (1 if pdx <= 0 else 0)] = pupil
            a[pr, pc - (1 if pdx <= 0 else 0)] = hexc('#3A3A3E')
            a[pr - 1 if pr - 1 >= y0 else pr, pc + 1 - (1 if pdx <= 0 else 0)] = hexc('#FFFFFF')
            if lid:
                for yy_ in range(-1, max(1, int(round(lid * 5))) - 1):
                    for xx_ in range(-1, 6): a[y0 + yy_, x0 + xx_] = lidc
            continue
        w = 4 if k > .8 else 3
        x0, y0 = int(round(px - w / 2)), int(round(py - 2))
        for yy_ in range(4):
            for xx_ in range(w):
                if w == 4 and yy_ in (0, 3) and xx_ in (0, 3): continue
                a[y0 + yy_, x0 + xx_] = iris if yy_ < 2 else iris_d
        pw = 2 if w == 4 else 1
        # darker ring at the bottom edge of the iris for depth
        if w == 4:
            a[y0 + 3, x0 + 1] = iris_d; a[y0 + 3, x0 + 2] = iris_d
        pcol = x0 + (w - pw) // 2 + int(np.sign(pdx)) * (1 if w == 4 else 1)
        pcol = max(x0, min(x0 + w - pw, pcol))
        prow = y0 + 1 - (1 if up else 0)
        for yy_ in range(2):
            for xx_ in range(pw):
                a[prow + yy_, pcol + xx_] = pupil
        if lid:
            rows = max(1, int(round(lid * 4)))
            for yy_ in range(rows):
                for xx_ in range(-1, w + 1):
                    if 0 <= x0 + xx_ < N: a[y0 + yy_ - 1, x0 + xx_] = lidc
    return Image.fromarray(a.astype(np.uint8), 'RGB')

def body_back(reg, T):
    """Seen from behind: folded wings cover the back, the red tail shows in full."""
    tail = poly([(.40, .72), (.60, .72), (.64, .98), (.36, .98)])
    reg['tail'] = tail
    T[tail] = (.62 + .28 * np.clip(1 - np.abs(xx - .5) / .13, 0, 1) - .3 * np.clip((yy - .90) / .08, 0, 1))[tail]
    br = (yy > .815) & (yy < .868) & (xx > .02) & (xx < .98)
    reg['branch'] = br; T[br] = (.8 - 9 * (yy - .815) + .08 * np.sin(xx * 90))[br]
    bo = ell(.5, .58, .19, .27) <= 1
    reg['body'] = bo
    T[bo] = np.clip(shade(.5, .58, .19, .27) * .7 + .2 * scallop(24, 8), 0, 1)[bo]
    reg['wing'] = np.zeros((R, R), bool)
    for s_ in (-1, 1):
        we = ell(.5 + s_ * .085, .62, .105, .25, s_ * .06)
        w = (we <= 1) & bo
        reg['wing'] |= w
        tip = np.clip((yy - .70) / .12, 0, 1)
        rim = np.clip((we - .75) / .25, 0, 1)
        T[w] = np.clip(.5 + .35 * scallop(16, 6, .25) - .35 * tip - .4 * rim + (.06 if s_ < 0 else -.04), 0, 1)[w]
    ft = np.zeros((R, R), bool)
    for s_ in (-1, 1):
        ft |= seg(.5 + s_ * .085, .80, .5 + s_ * .09, .85, .02)
    reg['feet'] = ft; T[ft] = .45

# Upright on a mossy stump, neck stretched, head turned in 3/4 (photo reference pose)
def perched():
    reg, T = {}, np.zeros((R, R))
    # stump with an uneven top
    top = .80 + .015 * np.sin(xx * 31) + .02 * np.clip(np.abs(xx - .5) - .12, 0, 1) * 6
    rock = (yy > top) & (np.abs(xx - .5) < .27 + (yy - .8) * .25)
    reg['rock'] = rock
    T[rock] = np.clip(.75 - 2.2 * (yy - top) - .25 * (xx > .62) + .12 * np.sin(xx * 140 + yy * 60), 0, 1)[rock]
    moss = rock & (np.sin(xx * 97) * np.sin(yy * 83 + xx * 20) > .55) & (yy > .86)
    reg['moss'] = moss; T[moss] = .6
    # red under-tail between the legs
    red = (ell(.5, .74, .085, .07) <= 1)
    reg['tail'] = red; T[red] = (.65 - .3 * np.clip((yy - .74) / .05, 0, 1))[red]
    # legs + toes gripping the stump edge
    leg = np.zeros((R, R), bool); claw = np.zeros((R, R), bool)
    for x0 in (.445, .555):
        leg |= seg(x0, .70, x0 + (.01 if x0 > .5 else -.01), .80, .022)
        for dx in (-.03, 0, .03):
            leg |= seg(x0 + (.01 if x0 > .5 else -.01), .80, x0 + dx * 1.4, .835, .012)
            claw |= ell(x0 + dx * 1.45, .845, .009, .014) <= 1
    reg['leg'] = leg; T[leg] = (.55 - 2 * (yy - .72))[leg]
    reg['claw'] = claw; T[claw] = .3
    # slim upright body + long folded wings
    e = ell(.5, .52, .155, .225)
    bo = e <= 1
    reg['body'] = bo
    neck = np.exp(-((yy - .345) / .04) ** 2) * .0
    T[bo] = np.clip(shade(.5, .52, .155, .225) * .8 + .24 * scallop(30, 10) - neck, 0, 1)[bo]
    reg['wing'] = np.zeros((R, R), bool)
    for sd in (-1, 1):
        we = ell(.5 + sd * .135, .55, .06, .235, -sd * .08)
        w = we <= 1
        reg['wing'] |= w
        tip = np.clip((yy - .66) / .1, 0, 1)
        rim = np.clip((we - .7) / .3, 0, 1)
        T[w] = np.clip(.45 + .35 * scallop(18, 7, .25) - .35 * tip - .35 * rim + (.06 if sd < 0 else -.06), 0, 1)[w]
    # stretched neck and small head turned to the right (3/4)
    hx, hy = .53, .235
    hd = (ell(hx, hy, .118, .108) <= 1) | (ell(.515, .32, .105, .1) <= 1)
    reg['head'] = hd
    T[hd] = np.clip(shade(hx, hy, .118, .108, .1, -.6) * .62 + .34 * scallop(46, 16), 0, 1)[hd]
    fc = ell(hx + .058, .232, .068, .05, .2) <= 1
    reg['face'] = fc; T[fc] = (.88 - .35 * np.clip(ell(hx + .06, .232, .062, .045), 0, 1))[fc]
    ex = hx + .052
    ir = ell(ex, .226, .026, .026) <= 1
    pu = ell(ex + .004, .226, .014, .014) <= 1
    reg['iris'] = ir; T[ir] = .7
    reg['pupil'] = pu; T[pu] = .2
    sc, ox, oy = .78, hx + .118 - .725 * .78, .235 - .30 * .78
    P = lambda pts: poly([(ox + x * sc, oy + y * sc) for x, y in pts])
    upm = P([(.725, .245), (.77, .25), (.81, .28), (.83, .325), (.828, .37), (.812, .405),
             (.80, .37), (.785, .345), (.755, .338), (.725, .335)])
    low = P([(.725, .335), (.765, .34), (.778, .37), (.75, .39), (.725, .375)])
    reg['beak'] = upm | low
    T[upm] = np.clip(.2 + .55 * np.clip(1 - np.hypot((xx - (ox + .765 * sc)) / .03, (yy - (oy + .27 * sc)) / .02), 0, 1), 0, 1)[upm]
    T[low] = .35
    halo = np.exp(-((xx - .5) ** 2 / .08 + (yy - .38) ** 2 / .08))
    return reg, np.clip(T, 0, 1), halo, ['rock', 'moss', 'tail', 'wing', 'body', 'leg', 'claw', 'head', 'face', 'iris', 'pupil', 'beak']

def body_close(reg, T):
    """Close-up from the front: no perch, no feet; red under-tail peeks below the belly."""
    red = ell(.5, .86, .085, .06) <= 1
    reg['tail'] = red; T[red] = (.7 - .35 * np.clip((yy - .86) / .05, 0, 1))[red]
    e = ell(.5, .575, .195, .27)
    bo = e <= 1
    reg['body'] = bo
    neck = np.exp(-((yy - .43) / .045) ** 2) * (np.abs(xx - .5) < .17)
    T[bo] = np.clip(shade(.5, .575, .195, .27) * .72 + .34 * scallop(17, 7) - .26 * neck - .1, 0, 1)[bo]
    reg['wing'] = np.zeros((R, R), bool)
    for s_ in (-1, 1):
        we = ell(.5 + s_ * .15, .60, .075, .22, -s_ * .1)
        w = (we <= 1) & bo
        reg['wing'] |= w
        prim = yy > .70                                   # long flight feathers at the bottom of the wing
        stripes = .5 + .5 * np.sin((xx * 1.0 + (yy - .7) * .25 * s_) * 2 * np.pi * 14)
        cov = scallop(12, 5, .25)                          # coverts: big scales
        rim = np.clip((we - .72) / .28, 0, 1)
        t = np.where(prim, .18 + .35 * stripes, .38 + .45 * cov)
        t = t - .3 * rim + (.06 if s_ < 0 else -.05)
        # pale leading edge where the wing meets the chest
        edge = (we > .78) & (np.sign(xx - (.5 + s_ * .15)) == -s_) & (yy < .70)
        t = np.where(edge, .8, t)
        T[w] = np.clip(t, 0, 1)[w]

# Front body, head turned fully to profile (the chosen pose), with a detailed head:
# big hooked beak, nostril in the bare cere, large white face patch, pale eye.
def profile_head(eye_look=0.0, lid=0.0, base='branch', beak=1.0, fine=False):
    reg, T = {}, np.zeros((R, R))
    {'rock': rock_front, 'close': body_close}.get(base, body_front)(reg, T)
    hx, hy = .475, .29
    hd = (ell(hx, hy, .168, .158) <= 1) | ((ell(.5, .40, .15, .12) <= 1) & (yy < .43)) | (ell(hx + .1, hy + .02, .09, .1) <= 1)
    reg['head'] = hd
    nape = np.clip((hx - xx) / .17, 0, 1)                      # darker toward the back of the head
    ringd = np.clip(1 - np.abs(ell(hx + .085, hy - .01, .1, .072, .18) - 1.25) / .3, 0, 1)   # darker feathers around the bare patch
    sc_h = scallop(15, 6) if fine else scallop(22, 9)
    T[hd] = np.clip(.62 - .25 * nape + .1 * (hy - yy) + .45 * sc_h - .18 * ringd, 0, 1)[hd]
    # bare white skin: around the eye and forward to the beak (lores + cere)
    fc = (ell(hx + .085, hy - .01, .1, .072, .18) <= 1) | (ell(hx + .14, hy - .035, .05, .04) <= 1)
    fc &= ~(xx > hx + .17)
    reg['face'] = fc
    fe = np.clip(ell(hx + .085, hy - .01, .1, .072, .18), 0, 1)
    T[fc] = np.clip(.95 - .45 * fe ** 3 + .05 * np.sin(xx * 300) * np.sin(yy * 300), 0, 1)[fc]
    # nostril
    no = ell(hx + .133, hy - .042, .015, .012) <= 1
    reg['nostril'] = no; T[no] = .1
    # beak: thick at the base, deeply hooked upper mandible + lower mandible
    bx, by = hx + .15, hy - .075 + (1 - beak) * .03
    P = lambda pts: poly([(bx + x * beak, by + y * beak) for x, y in pts])
    upm = P([(.0, .0), (.06, .0), (.115, .03), (.155, .085), (.17, .15), (.162, .215), (.145, .26),
             (.135, .21), (.12, .165), (.09, .14), (.05, .132), (.0, .135)])
    low = P([(.0, .135), (.05, .14), (.09, .152), (.112, .178), (.085, .2), (.045, .205), (.0, .19)])
    reg['beak'] = upm
    # sheen along the curved ridge of the upper mandible, black toward the tip
    d_top = np.clip((yy - (by + .0)) / (.05 * beak), 0, 1)
    along = np.clip(1 - (xx - bx) / (.17 * beak), 0, 1)
    T[upm] = np.clip(.15 + .7 * (1 - d_top) * (.4 + .6 * along) - .1 * np.clip((yy - (by + .17 * beak)) / .06, 0, 1), 0, 1)[upm]
    reg['lowbeak'] = low & ~upm
    T[low] = .45
    reg['_eyes'] = [(hx + .075, hy - .022, 1.2, eye_look, 0, lid, 0)]
    halo = np.exp(-((xx - .5) ** 2 / .09 + (yy - .42) ** 2 / .09))
    order = ['rock', 'moss', 'tail', 'branch', 'wing', 'body', 'leg', 'claw', 'feet', 'head', 'face', 'nostril', 'lowbeak', 'beak']
    return reg, np.clip(T, 0, 1), halo, order

# Three-quarter view (second photo reference): body turned to the left showing the
# near wing with big pale coverts and dark primaries, chest of fine crescents,
# head turned right in profile with the white face, small hooked beak, red tail.
def scallop_dark(rows, cols, phase=0.0):
    """Feathers with dark edges (for the pale wing coverts)."""
    return 1 - scallop(rows, cols, phase)

def three_quarter(eye_look=0.0, lid=0.0, beak=.55, tail=True):
    reg, T = {}, np.zeros((R, R))
    if tail:
        tl = poly([(.22, .80), (.40, .86), (.36, 1.02), (.16, 1.0)])
        reg['tail'] = tl; T[tl] = (.75 - .4 * np.clip((yy - .9) / .1, 0, 1) - .15 * (xx < .22))[tl]
    # body
    be = ell(.53, .58, .22, .33, -.12)
    bo = be <= 1
    reg['body'] = bo
    T[bo] = np.clip(shade(.53, .58, .22, .33, .3, -.6) * .62 + .36 * scallop(19, 8) - .02, 0, 1)[bo]
    # near wing (left, in front of the body)
    we = ell(.37, .60, .16, .33, .22)
    wg = we <= 1
    reg['wing'] = wg
    # axis coordinate along the wing: 0 at the shoulder, 1 at the tip (bottom-left)
    ax = np.clip(((yy - .30) * .97 + (.45 - xx) * .24) / .62, 0, 1)
    # coverts: big pale feathers outlined in darker grey, like in the photo
    coverts = .82 - .55 * scallop(8.5, 3.6, .2)
    prim_lines = .5 + .5 * np.sin(((xx - .37) * .97 + (yy - .6) * .24) * 2 * np.pi * 16)
    prim = .12 + .25 * prim_lines - .1 * np.clip((ax - .8) / .2, 0, 1)
    sec = .3 + .3 * prim_lines
    t = np.where(ax < .58, coverts + .08 * (1 - ax), np.where(ax < .72, sec, prim))
    rim = np.clip((we - .66) / .34, 0, 1)
    # shadow where the wing tucks under the neck, so head and wing read apart
    under = np.exp(-(((xx - .47) / .12) ** 2 + ((yy - .36) / .05) ** 2))
    T[wg] = np.clip(t - .35 * rim - .3 * under, 0, 1)[wg]
    # neck + head
    hx, hy = .60, .245
    hd = (ell(hx, hy, .15, .14) <= 1) | (ell(.565, .37, .15, .13) <= 1)
    reg['head'] = hd
    nape = np.clip((hx - xx) / .15, 0, 1)
    T[hd] = np.clip(.6 - .22 * nape + .1 * (hy - yy) + .45 * scallop(26, 11), 0, 1)[hd]
    fc = (ell(hx + .068, hy, .088, .062, .15) <= 1) & (xx < hx + .15)
    reg['face'] = fc
    fe = np.clip(ell(hx + .068, hy, .088, .062, .15), 0, 1)
    T[fc] = np.clip(.95 - .45 * fe ** 3, 0, 1)[fc]
    no = ell(hx + .127, hy - .028, .012, .01) <= 1
    reg['nostril'] = no; T[no] = .1
    bx, by = hx + .135, hy - .045
    P = lambda pts: poly([(bx + x * beak, by + y * beak) for x, y in pts])
    upm = P([(.0, .0), (.06, .0), (.115, .03), (.155, .085), (.17, .15), (.162, .215), (.145, .26),
             (.135, .21), (.12, .165), (.09, .14), (.05, .132), (.0, .135)])
    low = P([(.0, .135), (.05, .14), (.09, .152), (.112, .178), (.085, .2), (.045, .205), (.0, .19)])
    reg['beak'] = upm
    d_top = np.clip((yy - by) / (.05 * beak), 0, 1)
    along = np.clip(1 - (xx - bx) / (.17 * beak), 0, 1)
    T[upm] = np.clip(.15 + .7 * (1 - d_top) * (.4 + .6 * along), 0, 1)[upm]
    reg['lowbeak'] = low & ~upm; T[low] = .45
    reg['_eyes'] = [(hx + .06, hy - .012, 1.2, eye_look, 0, lid, 0)]
    halo = np.exp(-((xx - .55) ** 2 / .09 + (yy - .40) ** 2 / .09))
    return reg, np.clip(T, 0, 1), halo, ['tail', 'body', 'wing', 'head', 'face', 'nostril', 'lowbeak', 'beak']

# Front body (slim) + side-eye head: the final direction.
def front_sideeye(eye_look=-1.0, lid=0.0, beak=.55, slim=.165):
    reg, T = {}, np.zeros((R, R))
    tl = poly([(.38, .80), (.54, .80), (.55, 1.02), (.35, 1.02)])
    reg['tail'] = tl; T[tl] = (.75 - .4 * np.clip((yy - .9) / .1, 0, 1) - .15 * (xx < .39))[tl]
    # far wing: only its dark edge shows on the right of the body
    w2 = ell(.5 + slim + .005, .62, .05, .25, -.06) <= 1
    reg['wing2'] = w2; T[w2] = (.25 + .15 * scallop(10, 5))[w2]
    be = ell(.5, .58, slim, .31, -.04)
    bo = be <= 1
    reg['body'] = bo
    T[bo] = np.clip(shade(.5, .58, slim, .31, .2, -.6) * .6 + .38 * scallop(19, 8) - .02, 0, 1)[bo]
    # near wing on the left, folded along the side
    we = ell(.5 - slim * .62, .62, .095, .285, .1)
    wg = we <= 1
    reg['wing'] = wg
    ax = np.clip((yy - .36) / .52, 0, 1)
    coverts = .82 - .55 * scallop(8.5, 3.6, .2)
    lines = .5 + .5 * np.sin((xx - .38) * 2 * np.pi * 18)
    t = np.where(ax < .5, coverts + .08 * (1 - ax), np.where(ax < .66, .3 + .3 * lines, .12 + .25 * lines - .1 * np.clip((ax - .85) / .15, 0, 1)))
    rim = np.clip((we - .66) / .34, 0, 1)
    under = np.exp(-(((xx - .44) / .1) ** 2 + ((yy - .37) / .05) ** 2))
    T[wg] = np.clip(t - .35 * rim - .3 * under, 0, 1)[wg]
    # neck + head turned to the right
    hx, hy = .555, .25
    hd = (ell(hx, hy, .145, .135) <= 1) | (ell(.515, .37, .14, .12) <= 1)
    reg['head'] = hd
    nape = np.clip((hx - xx) / .15, 0, 1)
    T[hd] = np.clip(.6 - .22 * nape + .1 * (hy - yy) + .45 * scallop(26, 11), 0, 1)[hd]
    fc = (ell(hx + .066, hy, .085, .06, .15) <= 1) & (xx < hx + .145)
    reg['face'] = fc
    fe = np.clip(ell(hx + .066, hy, .085, .06, .15), 0, 1)
    T[fc] = np.clip(.95 - .45 * fe ** 3, 0, 1)[fc]
    no = ell(hx + .124, hy - .027, .012, .01) <= 1
    reg['nostril'] = no; T[no] = .1
    bx, by = hx + .132, hy - .044
    P = lambda pts: poly([(bx + x * beak, by + y * beak) for x, y in pts])
    upm = P([(.0, .0), (.06, .0), (.115, .03), (.155, .085), (.17, .15), (.162, .215), (.145, .26),
             (.135, .21), (.12, .165), (.09, .14), (.05, .132), (.0, .135)])
    low = P([(.0, .135), (.05, .14), (.09, .152), (.112, .178), (.085, .2), (.045, .205), (.0, .19)])
    reg['beak'] = upm
    d_top = np.clip((yy - by) / (.05 * beak), 0, 1)
    along = np.clip(1 - (xx - bx) / (.17 * beak), 0, 1)
    T[upm] = np.clip(.15 + .7 * (1 - d_top) * (.4 + .6 * along), 0, 1)[upm]
    reg['lowbeak'] = low & ~upm; T[low] = .45
    reg['_eyes'] = [(hx + .058, hy - .012, 1.2, eye_look, 0, lid, 0)]
    halo = np.exp(-((xx - .5) ** 2 / .09 + (yy - .40) ** 2 / .09))
    return reg, np.clip(T, 0, 1), halo, ['tail', 'wing2', 'body', 'wing', 'head', 'face', 'nostril', 'lowbeak', 'beak']

def curved_body(reg, T, w=.21, chest=.13, wd=0.0):
    """Fuller body whose wings wrap around the sides in a natural curve: the
    silhouette is one rounded body; the chest shows in the middle and each
    wing is the crescent between the chest and the outer edge."""
    out = ell(.5, .62, w, .33)
    body = out <= 1
    ch = ell(.5, .64, chest, .31)
    chest_m = body & (ch <= 1)
    reg['body'] = chest_m
    T[chest_m] = np.clip(shade(.5, .64, chest, .31, -.1, -.6) * .5 + .5 * scallop(16, 9) - .02, 0, 1)[chest_m]
    wing = body & (ch > 1)
    reg['wing'] = wing
    side = np.sign(xx - .5)
    down = np.clip((yy - .36) / .55, 0, 1)
    cov = .62 - .45 * scallop(10, 6, .2)          # coverts: scales with dark edges
    ang = np.arctan2(yy - .25, (xx - .5) * 1.3)     # flight feathers fan down along the side
    prim_l = .5 + .5 * np.sin(ang * 60)
    t = np.where(down < .45, cov, np.where(down < .58, .3 + .25 * prim_l, .14 + .26 * prim_l))
    rim_out = np.clip((out - .75) / .25, 0, 1)
    rim_in = np.clip(1 - (ch - 1) / .35, 0, 1)      # shadow where the wing folds against the chest
    t = t - .25 * rim_out - .45 * rim_in + .05 * (side < 0) - wd
    T[wing] = np.clip(t, 0, 1)[wing]

# Third photo: slim body from the front with both wings showing on the sides,
# head turned ~3/4 to the right — one eye visible, beak pointing down-right.
def photo3(eye_look=0.0, lid=0.0, beak=1.0, slim=.165, turn=1.0, bshift=0.0, eshift=0.0, face=1.0, up=0.0, wings='old', chest=.13, wd=0.0):
    reg, T = {}, np.zeros((R, R))
    if wings == 'curved':
        curved_body(reg, T, slim, chest, wd)
    else:
        tl = poly([(.43, .84), (.57, .84), (.58, 1.02), (.42, 1.02)])
        reg['tail'] = tl; T[tl] = (.75 - .4 * np.clip((yy - .92) / .1, 0, 1))[tl]
        be = ell(.5, .60, slim, .30)
        bo = be <= 1
        reg['body'] = bo
        neck = np.exp(-((yy - .37) / .05) ** 2) * .0
        T[bo] = np.clip(shade(.5, .60, slim, .30, -.2, -.6) * .55 + .5 * scallop(17, 7) - .04 - neck, 0, 1)[bo]
        reg['wing'] = np.zeros((R, R), bool)
        for sd in (-1, 1):
            we = ell(.5 + sd * (slim - .035), .64, .065, .27, -sd * .07)
            w = we <= 1
            reg['wing'] |= w
            ax = np.clip((yy - .38) / .52, 0, 1)
            cov = .7 - .5 * scallop(10, 5, .2)
            lines = .5 + .5 * np.sin((xx - .5) * 2 * np.pi * 20)
            t = np.where(ax < .42, cov, .18 + .25 * lines - .1 * np.clip((ax - .85) / .15, 0, 1))
            rim = np.clip((we - .6) / .4, 0, 1)
            T[w] = np.clip(t - .35 * rim + (.05 if sd < 0 else -.05), 0, 1)[w]
    # head, turned to the right
    hx, hy = .5 + .02 * turn, .245
    hd = (ell(hx, hy, .145, .138) <= 1) | (ell(.5, .36, .14, .12) <= 1)
    reg['head'] = hd
    nape = np.clip((hx - .05 - xx) / .15, 0, 1)
    T[hd] = np.clip(.46 - .2 * nape + .1 * (hy - yy) + .42 * scallop(24, 10), 0, 1)[hd]
    ex, ey = hx - .01 + .0 * turn, hy - .02
    fc = (ell(ex + .025, ey + .008, .088 * face, .066 * face, .2) <= 1) | (ell(hx + .072 + bshift * .6, hy - .012, .06 + bshift * .4, .05) <= 1)
    fc &= hd   # keep the bare skin inside the head outline (no white sliver over the beak)
    reg['face'] = fc
    fe = np.clip(ell(ex + .025, ey + .008, .088 * face, .066 * face, .2), 0, 1)
    T[fc] = np.clip(.95 - .4 * fe ** 3, 0, 1)[fc]
    no = ell(hx + .085 + bshift * .8, hy - .03, .011, .01) <= 1
    reg['nostril'] = no; T[no] = .1
    # beak in 3/4: broad, hooking down to the right
    c = (hx + .085 + bshift, hy - .005)
    Pb = lambda pts: poly([(c[0] + (x - .58) * beak, c[1] + (y - .24) * beak) for x, y in pts])
    upm = Pb([(.55, .21), (.595, .20), (.635, .225), (.656, .27), (.655, .325), (.64, .372), (.622, .40),
              (.615, .36), (.605, .328), (.585, .312), (.555, .31)])
    low = Pb([(.555, .31), (.585, .315), (.602, .335), (.585, .355), (.557, .345)])
    reg['beak'] = upm
    # pale sheen along the top/front of the upper mandible, black hook
    sheen = np.clip(1 - np.hypot((xx - (c[0] + .015 * beak)) / (.05 * beak), (yy - (c[1] - .02 * beak)) / (.04 * beak)), 0, 1)
    T[upm] = np.clip(.15 + .95 * sheen - .1 * np.clip((yy - (c[1] + .08 * beak)) / .05, 0, 1), 0, 1)[upm]
    reg['lowbeak'] = low & ~upm; T[low] = .6
    reg['_eyes'] = [(ex + eshift, ey, 1.2, eye_look, up, lid, 0)]
    halo = np.exp(-((xx - .5) ** 2 / .09 + (yy - .40) ** 2 / .09))
    return reg, np.clip(T, 0, 1), halo, ['tail', 'body', 'wing', 'head', 'face', 'nostril', 'lowbeak', 'beak']

# The logo's bird (front body, head turned, curved wings) with feet and the red
# tail added, for scenes where the whole parrot is visible.
def logo_full(**kw):
    P = 1 / 56
    reg, T, halo, order = photo3(wings='curved', slim=.21, chest=.13, bshift=3 * P, eshift=2 * P, face=1.24, wd=.12, **kw)
    tail = poly([(.43, .90), (.57, .90), (.585, 1.12), (.415, 1.12)])
    reg['tail'] = tail
    T[tail] = (.72 - .35 * np.clip((yy - 1.02) / .1, 0, 1) - .15 * (np.abs(xx - .5) > .05))[tail]
    ft = np.zeros((R, R), bool)
    for x0 in (.44, .56):
        for dx in (-.03, .0, .03):
            ft |= seg(x0, .9, x0 + dx * 1.3, .965, .016)
    reg['feet'] = ft; T[ft] = .5
    order = ['tail'] + [k for k in order if k != 'tail'] + ['feet']
    return reg, np.clip(T, 0, 1), halo, order

STUDIES = {
    'front': zoomed(front),
    'sideeye': zoomed(sideeye),
    'sideeye_lid': zoomed(sideeye, lid=True),
    'v_front': zoomed(front, z=1.04, cy=.53),
    'f1': zoomed(front, z=1.04, cy=.53),
    'p1': zoomed(profile_head, z=1.04, cy=.53),
    'full': zoomed(logo_full, z=.78, cy=.6),
    'x1': zoomed(photo3, z=1.25, cy=.42, slim=.21, chest=.13, wings='curved', bshift=0.0536, eshift=0.0357, face=1.24, wd=.12),
    'x2': zoomed(photo3, z=1.34, cy=.40, slim=.21, chest=.13, wings='curved', bshift=0.0536, eshift=0.0357, face=1.24, wd=.12),
    'x3': zoomed(photo3, z=1.25, cy=.42, slim=.21, chest=.13, beak=.9, wings='curved', bshift=0.0536, eshift=0.0357, face=1.24, wd=.12),
    'x4': zoomed(photo3, z=1.25, cy=.42, slim=.22, chest=.135, wings='curved', bshift=0.0536, eshift=0.0357, face=1.24, wd=.12),
    'x5': zoomed(photo3, z=1.25, cy=.42, slim=.21, chest=.13, wings='curved', bshift=0.0536, eshift=0.0357, face=1.24, wd=.12),
    'x6': zoomed(photo3, z=1.25, cy=.42, slim=.21, chest=.13, wings='curved', bshift=0.0536, eshift=0.0357, face=1.24, wd=.2),
    'x7': zoomed(photo3, z=1.34, cy=.40, slim=.21, chest=.13, beak=.9, wings='curved', bshift=0.0536, eshift=0.0357, face=1.24, wd=.12),
    'x8': zoomed(photo3, z=1.34, cy=.40, slim=.22, chest=.135, beak=.9, wings='curved', bshift=0.0536, eshift=0.0357, face=1.24, wd=.12),
    'm1': zoomed(photo3, z=1.25, cy=.42, slim=.21, chest=.13, face=1.1, wings='curved', bshift=0.0536, eshift=0.0357),
    'm2': zoomed(photo3, z=1.34, cy=.40, slim=.21, chest=.13, face=1.1, wings='curved', bshift=0.0536, eshift=0.0357),
    'm3': zoomed(photo3, z=1.19, cy=.43, slim=.21, chest=.13, face=1.1, wings='curved', bshift=0.0536, eshift=0.0357),
    'm4': zoomed(photo3, z=1.25, cy=.42, slim=.225, chest=.135, face=1.1, wings='curved', bshift=0.0536, eshift=0.0357),
    'm5': zoomed(photo3, z=1.25, cy=.42, slim=.21, chest=.15, face=1.1, wings='curved', bshift=0.0536, eshift=0.0357),
    'm6': zoomed(photo3, z=1.25, cy=.42, slim=.21, chest=.13, face=1.1, beak=.9, wings='curved', bshift=0.0536, eshift=0.0357),
    'm7': zoomed(photo3, z=1.25, cy=.42, slim=.21, chest=.13, face=1.24, wings='curved', bshift=0.0536, eshift=0.0357),
    'm8': zoomed(photo3, z=1.25, cy=.42, slim=.21, chest=.13, face=1.1, wd=.12, wings='curved', bshift=0.0536, eshift=0.0357),
    'k1': zoomed(photo3, z=1.15, cy=.44, wings='curved', slim=.21, chest=.13, bshift=0.0536, eshift=0.0357, face=1.1),
    'k2': zoomed(photo3, z=1.15, cy=.44, wings='curved', slim=.22, chest=.135, bshift=0.0536, eshift=0.0357, face=1.1),
    'k3': zoomed(photo3, z=1.15, cy=.44, wings='curved', slim=.21, chest=.12, bshift=0.0536, eshift=0.0357, face=1.1, eye_look=-1),
    'k4': zoomed(photo3, z=1.25, cy=.42, wings='curved', slim=.21, chest=.13, bshift=0.0536, eshift=0.0357, face=1.1),
    'w1': zoomed(photo3, z=1.07, cy=.52, slim=.19, bshift=0.0357, eshift=0.0179),
    'w2': zoomed(photo3, z=1.07, cy=.52, slim=.19, bshift=0.0357, eshift=0.0179, eye_look=-1),
    'w3': zoomed(photo3, z=1.07, cy=.52, slim=.19, bshift=0.0357, eshift=0.0179, beak=.88),
    'w4': zoomed(photo3, z=1.07, cy=.52, slim=.19, bshift=0.0357, eshift=0.0179, beak=1.12),
    'w5': zoomed(photo3, z=1.07, cy=.52, slim=.19, bshift=0.0357, eshift=0.0179, face=1.22),
    'w6': zoomed(photo3, z=1.07, cy=.52, slim=.19, bshift=0.0357, eshift=0.0179, up=1),
    'w7': zoomed(photo3, z=1.07, cy=.52, slim=.19, bshift=0.0357, eshift=0.0179, eye_look=-1, lid=.4),
    'w8': zoomed(photo3, z=1.07, cy=.52, slim=.19, bshift=0.0536, eshift=0.0357, face=1.1),
    'r1': zoomed(photo3, z=1.0, cy=.53, slim=.18, bshift=0.0179, eshift=0.0179),
    'r2': zoomed(photo3, z=1.0, cy=.53, slim=.19, bshift=0.0179, eshift=0.0179),
    'r3': zoomed(photo3, z=1.0, cy=.53, slim=.19, bshift=0.0357, eshift=0.0179),
    'r4': zoomed(photo3, z=1.0, cy=.53, slim=.20, bshift=0.0357, eshift=0.0179),
    'q1': zoomed(photo3, z=1.0, cy=.53),
    'q2': zoomed(photo3, z=1.0, cy=.53, eye_look=-1),
    'q3': zoomed(photo3, z=1.0, cy=.53, beak=.85),
    'q4': zoomed(photo3, z=1.08, cy=.50),
    's1': zoomed(front_sideeye, z=1.0, cy=.52),
    's2': zoomed(front_sideeye, z=1.0, cy=.52, eye_look=0),
    's3': zoomed(front_sideeye, z=1.0, cy=.52, slim=.15),
    's4': zoomed(front_sideeye, z=1.0, cy=.52, lid=.35),
    't1': zoomed(three_quarter, z=1.0, cy=.52, cx=.5),
    't2': zoomed(three_quarter, z=1.0, cy=.52, cx=.5, eye_look=-1),
    't3': zoomed(three_quarter, z=1.12, cy=.48, cx=.52),
    't4': zoomed(three_quarter, z=1.0, cy=.52, cx=.5, beak=.48),
    'c1': zoomed(profile_head, z=1.3, cy=.50, base='close', beak=.75, fine=True),
    'c2': zoomed(profile_head, z=1.3, cy=.50, base='close', beak=.68, fine=True),
    'c3': zoomed(profile_head, z=1.3, cy=.50, base='close', beak=.75, fine=True, eye_look=-1),
    'c4': zoomed(profile_head, z=1.42, cy=.47, base='close', beak=.75, fine=True),
    'p2': zoomed(profile_head, z=1.04, cy=.53, eye_look=-1),
    'p3': zoomed(profile_head, z=1.04, cy=.53, eye_look=-1, lid=.4),
    'p4': zoomed(profile_head, z=1.04, cy=.54, base='rock'),
    **{f'h{i+1}': zoomed(front, z=1.04, cy=.53, yaw=v) for i, v in enumerate([.78, .82, .86, .90, .93, .96, .98, 1.0])},
    **{f'g{i+1}': zoomed(front, z=1.04, cy=.53, yaw=round(.5 + i * .04, 2)) for i in range(8)},
    'z1': zoomed(front, z=1.04, cy=.53, yaw=.5),
    'z2': zoomed(front, z=1.04, cy=.53, yaw=.6),
    'z3': zoomed(front, z=1.04, cy=.53, yaw=.7),
    'z4': zoomed(front, z=1.04, cy=.53, yaw=.6, pdx=-1),
    'z5': zoomed(front, z=1.04, cy=.53, yaw=.6, pdx=-1, lid=.4),
    'z6': zoomed(front, z=1.04, cy=.53, yaw=.6, pdx=-1, tilt=-.15),
    'z7': zoomed(front, z=1.04, cy=.54, yaw=.6, base='rock', pdx=-1),
    'z8': zoomed(front, z=1.04, cy=.53, yaw=.5, pdx=-1),
    'y1': zoomed(front, z=1.04, cy=.53, yaw=.22),
    'y2': zoomed(front, z=1.04, cy=.53, yaw=.38),
    'y3': zoomed(front, z=1.04, cy=.53, yaw=.3, pdx=-1),
    'y4': zoomed(front, z=1.04, cy=.53, yaw=.3, pdx=-1, lid=.45),
    'y5': zoomed(front, z=1.04, cy=.53, yaw=.3, tilt=-.15),
    'y6': zoomed(front, z=1.04, cy=.53, yaw=.3, look_up=1),
    'y7': zoomed(front, z=1.04, cy=.54, yaw=.3, base='rock'),
    'y8': zoomed(front, z=1.04, cy=.54, yaw=.3, base='rock', pdx=-1, lid=.4),
    'f2': zoomed(front, z=1.04, cy=.53, pdx=1),
    'f3': zoomed(front, z=1.04, cy=.53, pdx=1, lid=.45),
    'f4': zoomed(front, z=1.04, cy=.53, tilt=.28, pdx=.6),
    'f5': zoomed(front, z=1.04, cy=.54, base='rock'),
    'f6': zoomed(front, z=1.04, cy=.54, base='rock', pdx=1, lid=.4),
    'f7': zoomed(front, z=1.04, cy=.53, look_up=1),
    'f8': zoomed(front, z=1.04, cy=.53, lid=.55),
    'v_side': zoomed(sideeye, z=1.04, cy=.53),
    'v_tilt': zoomed(sideeye, z=1.06, cy=.53, tilt=-.32),
    'v_back': zoomed(sideeye, z=1.04, cy=.53, body=body_back),
    'v_bust': zoomed(sideeye, z=1.75, cy=.40),
    'v_perched': zoomed(perched, z=1.0, cy=.5),
    'v_perched_close': zoomed(perched, z=1.12, cy=.5),
    'v_bubble': zoomed(sideeye, z=1.1, cy=.58, cx=.6),
}

def box(a, N): return np.array(Image.fromarray(a.astype(np.float32), 'F').resize((N, N), Image.BOX))

def ramp(t, cols, th):
    cols = [hexc(c) if isinstance(c, str) else c for c in cols]
    n = len(cols) - 1; v = np.clip(t, 0, 1) * n
    i = np.minimum(np.floor(v).astype(int), n - 1); f = v - i
    return np.stack(cols)[i + (f > th)]

def make(study, N, bg, halo_amt=.16):
    reg, T, halo, order = study
    bgc = hexc(bg); th = np.tile(BAYER, (N // 4 + 1, N // 4 + 1))[:N, :N]
    lit = bgc * (1 - halo_amt) + LIGHT * halo_amt
    img = ramp(box(halo, N), [bgc, bgc * .5 + lit * .5, lit], th)
    for k in order:
        if k not in reg or k.startswith('_'): continue
        cov = box(reg[k].astype(float), N); sel = cov >= THR.get(k, .5)
        tone = box(T * reg[k], N) / np.maximum(cov, 1e-6)
        img[sel] = ramp(tone, RAMPS[k], th)[sel]
    # 1px dark outline around the bird, like the owl
    bird = np.zeros((N, N), bool)
    for k in order:
        if k in reg and not k.startswith('_'): bird |= box(reg[k].astype(float), N) >= THR.get(k, .5)
    edge = np.zeros_like(bird)
    for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0)):
        edge |= np.roll(np.roll(bird, dy, 0), dx, 1)
    edge &= ~bird
    img[edge] = bgc * .55
    return stamp_eyes(Image.fromarray(img.astype(np.uint8), 'RGB'), reg, N)

def tile_icon(px, S=1024):
    big = px.convert('RGBA').resize((S, S), Image.NEAREST)
    m = Image.new('L', (S, S), 0); ImageDraw.Draw(m).rounded_rectangle([32, 32, S - 32, S - 32], radius=230, fill=255)
    out = Image.new('RGBA', (S, S), (0, 0, 0, 0)); out.paste(big, (0, 0), m); return out

# ---------- speech bubble with "A あ" (the parrot repeats words — in another language) ----------
GLYPH_A = ["..#..", ".#.#.", "#...#", "#####", "#...#", "#...#"]
GLYPH_ARROW = ["....", "..#.", "####", "..#.", "...."]
GLYPH_HIRA_A = [".#...", "#####", ".#.#.", ".###.", "#.#.#", "##.#."]
def add_bubble(img, x0=33, y0=3, w=20, h=11, bg_dark=(40, 12, 16)):
    a = np.array(img).astype(int)
    white, edge, ink = np.array([245, 245, 246]), np.array(bg_dark), np.array([74, 28, 34])
    for y in range(y0, y0 + h):
        for x in range(x0, x0 + w):
            corner = (y in (y0, y0 + h - 1)) and (x in (x0, x0 + w - 1))
            if corner: continue
            border = y in (y0, y0 + h - 1) or x in (x0, x0 + w - 1)
            a[y, x] = edge if border else white
    # tail pointing down-left, toward the beak
    for i, (tx, ty) in enumerate([(x0 + 4, y0 + h), (x0 + 3, y0 + h + 1), (x0 + 2, y0 + h + 2)]):
        a[ty, tx] = edge
        if i == 0: a[ty - 1, tx] = white; a[ty, tx + 1] = edge
    def glyph(g, gx, gy):
        for yy_, row in enumerate(g):
            for xx_, c in enumerate(row):
                if c == '#': a[gy + yy_, gx + xx_] = ink
    glyph(GLYPH_A, x0 + 2, y0 + 3)
    glyph([r for r in GLYPH_ARROW], x0 + 8, y0 + 3)
    glyph(GLYPH_HIRA_A, x0 + 13, y0 + 3)
    return Image.fromarray(a.astype(np.uint8), 'RGB')
