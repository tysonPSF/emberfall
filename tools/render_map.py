"""Draw the layout as a map you can look at. Cells are drawn at their real
`size` in metres, so a 512 m wild reads bigger than a 224 m city."""
import json, os, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.lines import Line2D

DOCS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs')
W = json.load(open(os.path.join(DOCS, 'world-layout.json')))
AREAS, ZONES, LINKS = W['areas'], {z['id']: z for z in W['zones']}, W['links']

CELL = 1.0
# Zones with no cell are not on the grid at all. They still have to be SEEN, so
# each gets a display berth well clear of the map, drawn dashed and tied to
# nothing - the picture should say "you cannot walk here" without a caption.
BERTH = {'the_grove': (-2.0, 0.15)}
BG, INK, DIM = '#14161a', '#e8e6e0', '#8b9199'
fig, ax = plt.subplots(figsize=(18.5, 17.5), facecolor=BG)
ax.set_facecolor(BG)

def hexa(c, a):
    c = c.lstrip('#')
    r, g, b = (int(c[i:i+2], 16) / 255 for i in (0, 2, 4))
    return (r, g, b, a)

def side(z):
    return 0.30 + 0.52 * (z['size'] - 224) / (512 - 224)

def at(z):
    return tuple(z['cell']) if z['cell'] else BERTH[z['id']]

# Borders, drawn ONLY in the gap between the two boxes.
#
# Centre to centre was the first cut and it lies: the segments run under the
# cells, so a gold border and the grey one past it read as one continuous line
# and the map looks like it has long-distance roads. A pass is a door in a
# shared wall, so the line is exactly the wall.
for l in LINKS:
    a, b = ZONES[l['a']], ZONES[l['b']]
    x1, y1 = at(a); x2, y2 = at(b)
    ha, hb = side(a) / 2, side(b) / 2
    if x1 == x2:                               # a north-south border
        lo, hi = (y1 + ha, y2 - hb) if y2 > y1 else (y1 - ha, y2 + hb)
        xs, ys = [x1, x2], [lo, hi]
    else:                                      # east-west
        lo, hi = (x1 + ha, x2 - hb) if x2 > x1 else (x1 - ha, x2 + hb)
        xs, ys = [lo, hi], [y1, y2]
    cross = l['cross_area']
    ax.add_line(Line2D(xs, ys, zorder=1,
                       color='#f0c674' if cross else DIM,
                       lw=4.0 if cross else 2.0,
                       alpha=0.95 if cross else 0.45,
                       solid_capstyle='butt'))

for z in ZONES.values():
    gx, gy = at(z)
    off = z['cell'] is None
    acc = AREAS[z['area']]['accent']
    s = side(z)                                          # real metres, scaled
    ax.add_patch(FancyBboxPatch((gx - s / 2, gy - s / 2), s, s,
                 boxstyle='round,pad=0.018,rounding_size=0.05',
                 linewidth=2.4 if z['existing'] else 1.2,
                 linestyle=(0, (4, 3)) if off else 'solid',
                 edgecolor=acc if not z['existing'] else '#ffffff',
                 facecolor=hexa(acc, 0.20 if not z['existing'] else 0.34), zorder=2))
    lo, hi = z['levels']
    band = 'sanctuary' if z['kind'] == 'sanctuary' else ('city' if z['kind'] == 'city' else f'{lo}–{hi}')
    tight = s < 0.42                                  # a city is too small to label inside
    ty = gy - s / 2 - 0.085 if tight else gy + 0.075
    ax.text(gx, ty, z['name'], ha='center', va='center', color=INK,
            fontsize=9.6, fontweight='bold', zorder=3)
    ax.text(gx, ty - 0.115 if tight else gy - 0.085, band, ha='center', va='center',
            color=acc, fontsize=8.8, zorder=3)
    if z['existing']:
        ax.text(gx, (ty - 0.225) if tight else (gy - 0.205), 'BUILT', ha='center',
                va='center', color='#ffffff', fontsize=7, fontweight='bold',
                alpha=0.75, zorder=3)
    if off:
        # stacked UNDER the band line, not on top of it: a small cell already
        # puts its name and level outside the box, so these are rows four and five
        base = (ty - 0.115) if tight else (gy - 0.085)
        ax.text(gx, base - 0.125, 'TELEPORT ONLY', ha='center', va='center',
                color=acc, fontsize=7.4, fontweight='bold', alpha=0.9, zorder=3)
        ax.text(gx, base - 0.245, 'no passes, no borders', ha='center',
                va='center', color=DIM, fontsize=7.4, zorder=3)

xs = [at(z)[0] for z in ZONES.values()]; ys = [at(z)[1] for z in ZONES.values()]
ax.set_xlim(min(xs) - 0.85, max(xs) + 0.85)
ax.set_ylim(min(ys) - 1.35, max(ys) + 1.15)
ax.set_aspect('equal'); ax.axis('off')

ax.text(min(xs) - 0.7, max(ys) + 0.85, 'EMBERFALL', color=INK, fontsize=25,
        fontweight='bold', va='center')
ax.text(min(xs) - 0.7, max(ys) + 0.52,
        f'{len(ZONES)} zones · {len(AREAS)} areas · levels 1–{max(z[chr(34)+chr(34)] if False else z["levels"][1] for z in ZONES.values())} · north is up, and +z is south in the engine',
        color=DIM, fontsize=10.5, va='center')

leg = []
for key, meta in AREAS.items():
    n = sum(1 for z in ZONES.values() if z['area'] == key)
    lo = min(z['levels'][0] for z in ZONES.values() if z['area'] == key)
    hi = max(z['levels'][1] for z in ZONES.values() if z['area'] == key)
    d = meta['deity']
    lbl = f"{meta['name']}  —  {n} zones, {lo}–{hi}" + (f"  ·  {d}" if d else '  ·  no deity, the start')
    leg.append(Line2D([], [], marker='s', linestyle='none', markersize=11,
                      markerfacecolor=hexa(meta['accent'], .55),
                      markeredgecolor=meta['accent'], label=lbl))
leg += [Line2D([], [], color='#f0c674', lw=2.6, label='border between two areas'),
        Line2D([], [], color=DIM, lw=1.4, alpha=.5, label='border inside one area'),
        Line2D([], [], marker='s', linestyle='none', markersize=11,
               markerfacecolor=(1, 1, 1, .34), markeredgecolor='#ffffff',
               label='already built'),
        Line2D([], [], marker='s', linestyle='none', markersize=11,
               markerfacecolor=(1, 1, 1, .10), markeredgecolor=DIM,
               label='off the grid — reached by teleport')]
lg = ax.legend(handles=leg, loc='lower left', bbox_to_anchor=(-0.02, -0.055),
               frameon=False, fontsize=10, labelcolor=INK, ncol=2,
               handletextpad=0.9, columnspacing=2.4, labelspacing=0.75)
plt.tight_layout()
plt.savefig(os.path.join(DOCS, 'world-map.png'), dpi=132,
            facecolor=BG, bbox_inches='tight', pad_inches=0.35)
print('ok')
