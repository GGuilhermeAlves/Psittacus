import numpy as np
from PIL import Image
from icon_art import hexc, tile_icon
X1 = [
"................",
"................",
"......ooooo.....",
".....oHHHHHo....",
"....oHWWWWWHo...",
"....oHWYPWWkBo..",
"....oHWWWWWBBBo.",
"....oHHWWWHBoBo.",
"...ooHHHHHHo.o..",
"..oDGHLHHLHGDo..",
".oDdGLGGLGGGdDo.",
".oDdGGLGGLGGdDo.",
".oDdGLGGLGGLdDo.",
".oDdGGLGGLGGdDo.",
".oddGLGGLGGGddo.",
".oddGGLGGLGGddo.",
]
P = {'H': '#A3AAB0', 'W': '#EEF0F1', 'Y': '#F2EBBE', 'P': '#0E0E10', 'B': '#1C1E22', 'k': '#3A3E44',
     'G': '#7C838A', 'L': '#A9AFB5', 'D': '#4F555B', 'd': '#353A3F'}
def make16(bg='#4A1C22', art=X1):
    bgc = hexc(bg); im = np.zeros((16, 16, 3)); im[:] = bgc
    for y, row in enumerate(art):
        assert len(row) == 16, (y, row)
        for x, ch in enumerate(row):
            if ch == '.': continue
            im[y, x] = bgc * .55 if ch == 'o' else hexc(P[ch])
    return Image.fromarray(im.astype(np.uint8), 'RGB')
