# Regenerates extension/icons and docs/icon-*.png (run from this folder; needs numpy, pillow, matplotlib).
from icon_art import make, tile_icon, STUDIES
from icon16 import make16
from PIL import Image
BG = '#4A1C22'
big = tile_icon(make(STUDIES['x1'](), 56, BG))
for n in (128, 48, 32): big.resize((n, n), Image.LANCZOS).save(f'../extension/icons/icon{n}.png')
tile_icon(make16(BG), S=1024).resize((16, 16), Image.BOX).save('../extension/icons/icon16.png')
big.resize((512, 512), Image.NEAREST).save('../docs/icon-512.png'); big.save('../docs/icon-1024.png')
big.resize((256, 256), Image.NEAREST).save('../docs/icon-preview.png')
