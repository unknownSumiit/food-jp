"""ふたりの台所 logo kit. Text converted to outlines (Noto Serif/Sans CJK JP, OFL)."""
import os
from fontTools.ttLib import TTCollection
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
INDIGO, VERM, CREAM, INK = "#2c4a6e", "#c0462f", "#faf6ee", "#262421"

def jp(path):
    for f in TTCollection(path).fonts:
        if "JP" in f["name"].getDebugName(1):
            return f
    raise SystemExit("JP face not found")

class Font:
    def __init__(self, tt):
        self.gs, self.cmap, self.hmtx, self.upm = tt.getGlyphSet(), tt.getBestCmap(), tt["hmtx"], tt["head"].unitsPerEm
    def text(self, s, x, y, size, tracking=0.0):
        sc, pen, cx = size / self.upm, SVGPathPen(self.gs), x
        for ch in s:
            n = self.cmap[ord(ch)]
            self.gs[n].draw(TransformPen(pen, (sc, 0, 0, -sc, cx, y)))
            cx += self.hmtx[n][0] * sc + tracking * size
        return pen.getCommands(), cx - x - tracking * size

SERIF = Font(jp("/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"))
SANS = Font(jp("/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc"))

def mark(bowl1=INDIGO, bowl2=VERM, rice=CREAM, steam=INDIGO):
    """Two rice bowls side by side with steam."""
    def bowl(cx, col):
        return (f'<path d="M{cx-21} 54 H{cx+21} A21 23 0 0 1 {cx} 78 A21 23 0 0 1 {cx-21} 54 Z" fill="{col}"/>'
                f'<path d="M{cx-18} 54 C{cx-15} 41 {cx+15} 41 {cx+18} 54 Z" fill="{rice}" stroke="{col}" stroke-width="2.5"/>'
                f'<rect x="{cx-9}" y="77" width="18" height="6" rx="2" fill="{col}"/>')
    st = "".join(f'<path d="M{x} 38 c-4 -5 4 -8 0 -14" stroke="{steam}" stroke-width="3" stroke-linecap="round" fill="none" opacity=".7"/>'
                 for x in (22, 32, 70, 80))
    return bowl(27, bowl1) + bowl(75, bowl2) + st

def lockup(word=INK, small=VERM, **kw):
    main_d, main_w = SERIF.text("ふたりの台所", 112, 70, 44, tracking=0.04)
    sub_d, sub_w = SANS.text("ふたり分がちょうどいい、毎日のごはん", 114, 92, 13, tracking=0.08)
    W = int(110 + max(main_w, sub_w) + 8)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} 100" width="{W*3}" height="300">'
            f'<g transform="translate(0 4)">{mark(**kw)}</g><path d="{main_d}" fill="{word}"/><path d="{sub_d}" fill="{small}"/></svg>'), W

def icon(bg=CREAM, rx=22):
    back = f'<rect width="100" height="100" rx="{rx}" fill="{bg}"/>' if bg else ""
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">{back}<g transform="translate(0 4)">{mark()}</g></svg>'

logo, W = lockup()
open(os.path.join(OUT, "logo.svg"), "w").write(logo)
open(os.path.join(OUT, "logo-white.svg"), "w").write(lockup(word="#ffffff", small="#ffb4a3", bowl1="#a9c3e3", steam="#a9c3e3", rice="#1f242b")[0])
open(os.path.join(OUT, "icon.svg"), "w").write(icon())
open(os.path.join(OUT, "icon-square.svg"), "w").write(icon(rx=0))
print("width", W)
