"""The guide's theme, derived from the atlas rather than typed by hand.

The atlas is already the style guide: it has a paper, an ink, a sea colour and
a pen for each of the seven realms, and it is lettered in two typefaces. This
module reads those out of tools/atlas_map.py and turns them into CSS custom
properties, so the site and the map stay the same object. Change the atlas's
palette and the site follows.

It is parsed, not imported: atlas_map builds its warp field at import time,
which takes seconds and needs scipy. Parsing wants neither.

Two things are assets rather than code, checked in beside the page:

  docs/wiki/fonts/*.woff2   the four faces the atlas letters with, subsetted
                            (TeX Gyre, GUST Font License; tools/make_webfonts.py)
  docs/wiki/art/paper.jpg   a seamless tile of the atlas's own parchment noise,
                            regenerated here when numpy and scipy are present
"""
import ast, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'docs', 'wiki')

# The atlas's own constants, in case the file ever moves out from under us.
FALLBACK = {
    'INK': (62, 44, 30), 'INK_SOFT': (96, 74, 52), 'SEA': (196, 176, 140),
    'PEN': {'emberlands': (58, 92, 48), 'dawnstair': (150, 106, 28),
            'monsoon': (30, 104, 124), 'ashfall': (160, 54, 26),
            'standingsky': (78, 94, 106), 'boneyard': (86, 62, 124),
            'blackwater': (56, 74, 40)},
}


def atlas_palette():
    """INK, INK_SOFT, SEA and the seven realm pens, read out of the renderer."""
    out = dict(FALLBACK)
    try:
        tree = ast.parse(open(os.path.join(ROOT, 'tools', 'atlas_map.py')).read())
    except Exception:
        return out
    for node in tree.body:
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)):
            continue
        name = node.targets[0].id
        if name in ('INK', 'INK_SOFT', 'SEA', 'PEN'):
            try:
                out[name] = ast.literal_eval(node.value)
            except Exception:
                pass
    return out


def unhex(s_):
    s_ = (s_ or '').lstrip('#')
    if len(s_) != 6:
        return None
    return tuple(int(s_[i:i + 2], 16) for i in (0, 2, 4))


def class_colours():
    """Each class's colour, as the game's own character sheet uses it."""
    try:
        d = json.load(open(os.path.join(ROOT, 'data', 'classes.json')))
    except Exception:
        return {}
    return {k: v.get('color') for k, v in d.items()
            if isinstance(v, dict) and not k.startswith('_') and v.get('color')}


def hexc(rgb):
    return '#%02x%02x%02x' % tuple(int(round(c)) for c in rgb[:3])


def mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def lum(rgb):
    """Relative luminance, for the contrast checks in the build log."""
    c = []
    for v in rgb[:3]:
        v /= 255.0
        c.append(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a, b):
    la, lb = lum(a), lum(b)
    lo, hi = sorted((la, lb))
    return (hi + 0.05) / (lo + 0.05)


# The parchment recipe, lifted from atlas_map.parchment(): a warm base with
# fibre, blotches and broad variation. Here it is made to tile: the filters
# wrap, and the broad swing is damped so the repeat does not read as a grid.
PAPER_BANDS = ((198, 236), (176, 214), (136, 176))
PAPER_T = 0.80          # where on the band the page sits: paler than the map,
                        # because this paper carries paragraphs, not coastlines


def paper_tile(path, n=512, seed=11):
    """Write a seamless parchment tile. Returns False if numpy/scipy are absent."""
    try:
        import numpy as np
        from scipy import ndimage
        from PIL import Image
    except Exception:
        return False
    g = np.random.default_rng(seed)
    w = lambda a, s: ndimage.gaussian_filter(a, s, mode='wrap')
    fine = w(g.normal(size=(n, n)), 1.0)
    broad = w(g.normal(size=(n, n)), 7.0)
    blotch = w(g.normal(size=(n, n)), 2.4)
    norm = lambda a: a / (np.abs(a).max() + 1e-9)
    t = np.clip(PAPER_T + 0.085 * norm(broad) + 0.05 * norm(blotch)
                + 0.03 * norm(fine), 0, 1)
    img = np.zeros((n, n, 3), float)
    for i, (lo, hi) in enumerate(PAPER_BANDS):
        img[..., i] = lo + (hi - lo) * t
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im = Image.fromarray(img.astype('uint8'))
    if path.endswith('.jpg'):
        im.save(path, quality=92, optimize=True, subsampling=0)
    else:
        im.save(path, optimize=True)
    return True


def paper_colour():
    """The flat colour the tile averages to, for the CSS fallback."""
    return tuple(lo + (hi - lo) * PAPER_T for lo, hi in PAPER_BANDS)


FACES = [
    ('Pagella', 'pagella-regular.woff2', 400, 'normal'),
    ('Pagella', 'pagella-italic.woff2', 400, 'italic'),
    ('Pagella', 'pagella-bold.woff2', 700, 'normal'),
    ('Chorus', 'chorus-mediumitalic.woff2', 400, 'italic'),
]


def font_css():
    out = ['/* TeX Gyre Pagella and Chorus, the faces the atlas letters with.',
           '   (c) GUST e-foundry, GUST Font License; see fonts/LICENSE.txt */']
    for fam, f, weight, style in FACES:
        if not os.path.exists(os.path.join(OUT, 'fonts', f)):
            continue
        out.append('@font-face{font-family:%s;src:url("fonts/%s") format("woff2");'
                   'font-weight:%d;font-style:%s;font-display:swap}'
                   % (fam, f, weight, style))
    return '\n'.join(out)


def tokens():
    """The CSS custom properties. Everything here comes from the atlas."""
    p = atlas_palette()
    ink, soft, sea = p['INK'], p['INK_SOFT'], p['SEA']
    paper = paper_colour()
    white = (255, 255, 255)

    t = {
        # paper, in three weights: the page, a plate laid on it, a well sunk in
        'paper': hexc(paper),
        'plate': hexc(mix(paper, white, 0.42)),
        'well': hexc(mix(paper, sea, 0.55)),
        'sea': hexc(sea),
        # ink, in the map's three weights plus two for rules
        'ink': hexc(ink),
        'ink-soft': hexc(soft),
        'ink-faint': hexc(mix(soft, paper, 0.45)),
        'rule': hexc(mix(sea, ink, 0.34)),
        'hair': hexc(mix(paper, sea, 0.75)),
    }
    lines = [':root{']
    for k, v in t.items():
        lines.append(f'  --{k}: {v};')
    lines.append('  --paper-img: url("art/paper.jpg");')
    lines.append('}')

    # A pen per realm, and the same colour again softened for large areas.
    lines.append('/* the seven realm pens, straight off the map */')
    for aid, rgb in p['PEN'].items():
        # --pen is for marks, rules and big type; --pen-text is the same
        # colour pulled toward ink until it clears 4.5:1 on paper, for the
        # places a realm's name is set small.
        dark = rgb
        while contrast(dark, paper) < 4.6:
            dark = mix(dark, (0, 0, 0), 0.08)
        lines.append('[data-realm="%s"]{--pen:%s;--pen-wash:%s;--pen-text:%s}'
                     % (aid, hexc(rgb), hexc(mix(rgb, paper, 0.72)), hexc(dark)))
    lines.append(':root{--pen:var(--ink);--pen-wash:var(--hair);'
                 '--pen-text:var(--ink)}')

    # A class carries a colour in the game's own UI. Those were picked for a
    # dark screen, so each is walked toward black until it clears 4.5:1 here.
    lines.append('/* the class colours, darkened until they hold on paper */')
    for cid, col in class_colours().items():
        rgb = unhex(col)
        if not rgb:
            continue
        dark = rgb
        while contrast(dark, paper) < 4.6:
            dark = mix(dark, (0, 0, 0), 0.08)
        lines.append('[data-class="%s"]{--pen:%s;--pen-text:%s}'
                     % (cid, hexc(rgb), hexc(dark)))
    return '\n'.join(lines), t


def build():
    """Refresh the generated assets and return the derived CSS."""
    tile = os.path.join(OUT, 'art', 'paper.jpg')
    if not os.path.exists(tile):
        paper_tile(tile)
    css, t = tokens()
    return '\n'.join([font_css(), css])


def report():
    """Contrast of the type colours on the page, checked at build time."""
    p = atlas_palette()
    paper = paper_colour()
    out = []
    for name, rgb in (('ink', p['INK']), ('ink-soft', p['INK_SOFT'])):
        out.append(f'{name} on paper {contrast(rgb, paper):.1f}:1')
    for aid, rgb in p['PEN'].items():
        out.append(f'{aid} pen {contrast(rgb, paper):.1f}:1')
    return out


if __name__ == '__main__':
    print(build())
    print('\n'.join('/* ' + r + ' */' for r in report()))
