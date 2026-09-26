"""
EMBERFALL — the world layout, and the checks that keep it a world.

In this engine a map is not a picture. A zone is a square `size` metres across,
ringed by mountains, with up to four `passes` - gaps at its north, south, east
and west edges - and each pass carries a `zone_line` naming the neighbour and
the `arrive` point you materialise at. So the world is a GRID, and a world map
is the set of cells plus which edge of which cell opens onto which.

That is why this is a table and a script rather than 31 hand-written files.
Six areas at five or six zones each is 31 zones and 50-odd borders; every
border is four things that have to agree (a pass each side, a line each side)
and eight numbers. Typed out, that is where the one-way doors and the arrive
points inside a mountain come from.

CONVENTION, taken from the shipped zones rather than assumed: +z is SOUTH.
Greenmoor's pass at [0, 192] leads to Emberhold, which CLAUDE.md calls its
south pass. So in the grid below, gy rises NORTHWARD and converts to -z.
"""
import json, math

# A CITY ENDS IN -HOLD. Emberhold was already named that way, so the rule is
# taken rather than invented, and it means a player can tell a city from a wild
# zone by its name alone on the map, the compass and the zone line prompt. The
# light area's `Dawnhold` was an outpost and is renamed `Dawnwatch` here so the
# suffix keeps meaning one thing.
#
# id, display name, area, level band, size in metres, grid cell (gx east+, gy north+)
ZONES = [
    # ---- THE EMBERLANDS - the start, no deity. Everything already built lives here.
    ('emberhold',       'Emberhold',          'emberlands', (1, 1),   224, (0, 0), 'city'),
    ('greenmoor',       'Greenmoor',          'emberlands', (1, 7),   384, (0, 1), 'field'),
    # OFF THE GRID ON PURPOSE. No cell, so it has no neighbours and no passes:
    # the Grove is reached by teleport, not on foot. It was at (-1, 1) and its
    # north gate opened onto The Weeping Throat at 20-24 - a nineteen-level drop
    # out of a sanctuary's back door, which was the only lethal border on the map.
    ('the_grove',       'The Grove',          'emberlands', (1, 1),   256, None,    'sanctuary'),
    ('harrowfield',     'Harrowfield',        'emberlands', (3, 9),   384, (1, 1), 'field'),
    ('thornwood',       'Thornwood Vale',     'emberlands', (6, 14),  512, (0, 2), 'wood'),
    ('hollowmere',      'Hollowmere',         'emberlands', (10, 15), 448, (1, 2), 'water'),

    # ---- THE DAWNSTAIR - Prabhagaj, the Dawn-Tusk. East, climbing.
    ('sunward_steps',   'Sunward Steps',      'dawnstair',  (14, 18), 448, (2, 2), 'terrace'),
    ('high_terrace',    'High Terrace',       'dawnstair',  (18, 23), 512, (1, 3), 'terrace'),
    ('the_bleach',      'The Bleach',         'dawnstair',  (16, 21), 512, (2, 3), 'waste'),
    ('dawnwatch',       'Dawnwatch',          'dawnstair',  (22, 24), 448, (1, 4), 'outpost'),
    ('mirror_flats',    'Mirror Flats',       'dawnstair',  (20, 24), 512, (2, 4), 'waste'),
    # Beside Sunward Steps, the zone you arrive in: you enter the Dawnstair and
    # the town is right there.
    ('lanternhold',     'Lanternhold',        'dawnstair',  (14, 24), 224, (3, 2), 'city'),

    # ---- THE LONG MONSOON - Jalendra, the Tide-Trunked. West, and rising water.
    ('weeping_throat',  'The Weeping Throat', 'monsoon',    (20, 24), 448, (-1, 2), 'water'),
    ('reedmere',        'Reedmere',           'monsoon',    (22, 26), 512, (-2, 2), 'water'),
    ('drownfast',       'Drownfast',          'monsoon',    (26, 30), 512, (-1, 3), 'water'),
    ('silted_reach',    'The Silted Reach',   'monsoon',    (24, 28), 512, (-2, 3), 'water'),
    ('tidemouth',       'Tidemouth',          'monsoon',    (28, 30), 448, (-2, 4), 'outpost'),
    # The cell the Grove left. It touches Greenmoor as well as The Weeping
    # Throat, so a level 5 character can run to the water city and live - which
    # is the oldest rite of passage this genre has.
    ('rainhold',        'Rainhold',           'monsoon',    (20, 30), 224, (-1, 1), 'city'),

    # ---- THE ASHFALL - Agnavar, the Ember-Tusked. Due north of home.
    ('cinderpass',      'Cinderpass',         'ashfall',    (26, 30), 448, (0, 3), 'burn'),
    ('the_burn',        'The Burn',           'ashfall',    (29, 33), 512, (0, 4), 'burn'),
    ('blackglass',      'Blackglass',         'ashfall',    (31, 35), 512, (0, 5), 'burn'),
    ('smokewood',       'Smokewood',          'ashfall',    (33, 37), 512, (1, 5), 'wood'),
    ('agnavars_hearth', "Agnavar's Hearth",   'ashfall',    (35, 38), 512, (2, 5), 'burn'),
    # DEEP, and not by choice: every cell touching Cinderpass, The Burn,
    # Blackglass and Smokewood is already taken, so the only free ground beside
    # the Ashfall is past the Hearth. It suits Agnavar - his people live at the
    # far end, beside the fire that will not go out - but it is a constraint
    # before it is a decision, and moving it means moving a zone.
    ('forgehold',       'Forgehold',          'ashfall',    (26, 38), 224, (3, 5), 'city'),

    # ---- THE STANDING SKY - Vayuketh. North-west, open and high.
    ('windbreak',       'Windbreak',          'standingsky',(32, 36), 448, (-1, 4), 'plain'),
    ('the_long_grass',  'The Long Grass',     'standingsky',(34, 38), 512, (-1, 5), 'plain'),
    ('stonesail',       'Stonesail',          'standingsky',(37, 41), 512, (-2, 5), 'plain'),
    ('hollow_air',      'Hollow Air',         'standingsky',(39, 43), 512, (-1, 6), 'plain'),
    ('vayukeths_step',  "Vayuketh's Step",    'standingsky',(42, 44), 448, (-2, 6), 'outpost'),
    # West of Stonesail, mid-area. A permanent town for a god whose faithful
    # never stay anywhere long is the joke, and it should stay one.
    ('galehold',        'Galehold',           'standingsky',(32, 44), 224, (-3, 5), 'city'),

    # ---- THE BONEYARD - Timiraj, the Unlit. The top of the world.
    ('fogfall',         'Fogfall',            'boneyard',   (40, 43), 512, (0, 6), 'fog'),
    ('ivory_field',     'The Ivory Field',    'boneyard',   (42, 45), 512, (1, 6), 'fog'),
    ('the_unlit',       'The Unlit',          'boneyard',   (44, 47), 512, (2, 6), 'fog'),
    ('lastwalk',        'Lastwalk',           'boneyard',   (46, 49), 512, (0, 7), 'fog'),
    ('timirajs_table',  "Timiraj's Table",    'boneyard',   (48, 50), 512, (1, 7), 'fog'),
    # Touching both The Unlit and Timiraj's Table, so the last city has two ways
    # in rather than one dead-end road.
    ('barrowhold',      'Barrowhold',         'boneyard',   (40, 50), 224, (2, 7), 'city'),
]

AREAS = {
    'emberlands':  {'name': 'The Emberlands', 'deity': None,        'accent': '#7a9a5b'},
    'dawnstair':   {'name': 'The Dawnstair',  'deity': 'light',     'accent': '#e8d49a'},
    'monsoon':     {'name': 'The Long Monsoon','deity': 'water',    'accent': '#4fa3b8'},
    'ashfall':     {'name': 'The Ashfall',    'deity': 'fire',      'accent': '#d4552f'},
    'standingsky': {'name': 'The Standing Sky','deity': 'wind',     'accent': '#b8c4cc'},
    'boneyard':    {'name': 'The Boneyard',   'deity': 'dark',      'accent': '#6b5a9e'},
}

# what the engine already ships, so the map has to grow out of it rather than over it
EXISTING = {'emberhold', 'greenmoor', 'thornwood', 'hollowmere'}
# Zones with no cell: not on the grid, not walkable to, reached another way.
TELEPORT_ONLY = {'the_grove'}
# Thornwood's three unused passes, which CLAUDE.md reserves: "a future zone
# replaces one with a zone line"
ROCKSLIDES = {'thornwood': ['north', 'west'], 'hollowmere': ['north', 'east', 'south']}

DIRS = {'north': (0, 1), 'south': (0, -1), 'east': (1, 0), 'west': (-1, 0)}
OPPOSITE = {'north': 'south', 'south': 'north', 'east': 'west', 'west': 'east'}


def build():
    by_cell, by_id = {}, {}
    for z in ZONES:
        zid, name, area, band, size, cell, kind = z
        rec = {'id': zid, 'name': name, 'area': area, 'levels': list(band),
               'size': size, 'cell': list(cell) if cell else None, 'kind': kind,
               'existing': zid in EXISTING,
               'reached': 'teleport' if zid in TELEPORT_ONLY else 'foot'}
        by_id[zid] = rec
        if cell:
            by_cell[cell] = rec
    links = []
    for rec in by_id.values():
        if not rec['cell']:
            continue                      # no cell, no edges, no passes
        gx, gy = rec['cell']
        for d, (dx, dy) in DIRS.items():
            other = by_cell.get((gx + dx, gy + dy))
            if not other:
                continue
            if rec['id'] < other['id']:      # one entry per border
                links.append({'a': rec['id'], 'a_edge': d,
                              'b': other['id'], 'b_edge': OPPOSITE[d],
                              'cross_area': rec['area'] != other['area']})
    return by_id, by_cell, links


def check(by_id, by_cell, links):
    """Every claim this layout makes, tested. Failures print and exit non-zero."""
    fails, notes = [], []
    ok = lambda c, m: (notes if c else fails).append(m)

    on_grid = [r for r in by_id.values() if r['cell']]
    ok(len(by_cell) == len(on_grid),
       f'{len(on_grid)} zones on {len(by_cell)} distinct cells - no two share one')
    ok(all(not by_id[t]['cell'] for t in TELEPORT_ONLY),
       f'{len(TELEPORT_ONLY)} teleport-only zone(s) hold no cell: '
       f'{", ".join(by_id[t]["name"] for t in TELEPORT_ONLY)}')

    for a, meta in AREAS.items():
        cells = [tuple(r['cell']) for r in by_id.values() if r['area'] == a and r['cell']]
        total = sum(1 for r in by_id.values() if r['area'] == a)
        ok(5 <= total <= 6, f'{meta["name"]}: {total} zones'
           + (f' ({len(cells)} on the grid)' if total != len(cells) else ''))
        # contiguous: flood fill from one cell through 4-neighbours inside the area
        seen, stack = {cells[0]}, [cells[0]]
        while stack:
            cx, cy = stack.pop()
            for dx, dy in DIRS.values():
                n = (cx + dx, cy + dy)
                if n in cells and n not in seen:
                    seen.add(n); stack.append(n)
        ok(len(seen) == len(cells),
           f'{meta["name"]} is one connected landmass ({len(seen)}/{len(cells)})')

    # every zone reachable on foot from the starting zone
    seen, stack = {'emberhold'}, ['emberhold']
    adj = {}
    for l in links:
        adj.setdefault(l['a'], []).append(l['b'])
        adj.setdefault(l['b'], []).append(l['a'])
    while stack:
        for n in adj.get(stack.pop(), []):
            if n not in seen:
                seen.add(n); stack.append(n)
    walkable = {z for z in by_id if z not in TELEPORT_ONLY}
    ok(seen == walkable,
       f'every zone on the grid is walkable from Emberhold ({len(seen)}/{len(walkable)})')
    # and the teleport zones are UNREACHABLE on foot, which is the point of them
    ok(not (seen & TELEPORT_ONLY),
       f'{", ".join(by_id[t]["name"] for t in TELEPORT_ONLY)} cannot be walked to - '
       'it has no pass on any edge')

    # no zone may have more than four passes: a square has four edges
    deg = {}
    for l in links:
        deg[l['a']] = deg.get(l['a'], 0) + 1
        deg[l['b']] = deg.get(l['b'], 0) + 1
    worst = max(deg.values())
    ok(worst <= 4, f'no zone needs more than four passes (worst {worst})')

    for a, meta in AREAS.items():
        cities = [r['name'] for r in by_id.values() if r['area'] == a and r['kind'] == 'city']
        ok(len(cities) == 1, f'{meta["name"]}: one city, {cities[0] if cities else "NONE"}')
    bad = [r['name'] for r in by_id.values() if r['kind'] == 'city' and not r['name'].endswith('hold')]
    ok(not bad, 'every city ends in -hold' + ('' if not bad else f' (not {bad})'))

    # the three reserved rockslides all get used, and on different areas
    for zid, edges in ROCKSLIDES.items():
        used = {}
        for l in links:
            if l['a'] == zid: used[l['a_edge']] = by_id[l['b']]['area']
            if l['b'] == zid: used[l['b_edge']] = by_id[l['a']]['area']
        missing = [e for e in edges if e not in used]
        ok(not missing, f'{zid}: all three reserved passes open '
           f'({", ".join(f"{e} to {used[e]}" for e in edges if e in used)})')

    # a web, not a hub: areas must border each other and not only the start
    pairs = {tuple(sorted((by_id[l['a']]['area'], by_id[l['b']]['area'])))
             for l in links if l['cross_area']}
    non_start = [p for p in pairs if 'emberlands' not in p]
    ok(len(non_start) >= 4,
       f'{len(pairs)} area borders, {len(non_start)} of them between deity areas - a web, not a hub')

    # level bands: a border should not drop you more than 12 levels out of depth
    # A CITY IS EXEMPT. Walking into a town twenty levels above you is not a
    # death, it is an errand - guards, merchants, a bind point and a long run
    # home. The check is about wilderness you can be killed in.
    steep = []
    for l in links:
        a, b = by_id[l['a']], by_id[l['b']]
        if 'city' in (a['kind'], b['kind']) or 'sanctuary' in (a['kind'], b['kind']):
            continue
        gap = max(a['levels'][0] - b['levels'][1], b['levels'][0] - a['levels'][1])
        if gap > 12:
            steep.append(f'{a["name"]} -> {b["name"]} (+{gap})')
    ok(not steep, 'no border drops a player more than 12 levels out of depth'
       + ('' if not steep else ': ' + '; '.join(steep)))
    return notes, fails


if __name__ == '__main__':
    import sys
    by_id, by_cell, links = build()
    notes, fails = check(by_id, by_cell, links)
    for n in notes: print('  ok   ' + n)
    for f in fails: print('  FAIL ' + f)
    out = {'note': 'Emberfall world layout. Cells are grid squares; gy rises NORTH '
                   '(+z is south in the engine). Links are derived from the grid, '
                   'never typed: one border = a pass and a zone_line on each side.',
           'areas': AREAS, 'zones': list(by_id.values()), 'links': links}
    import os
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'world-layout.json')
    json.dump(out, open(path, 'w'), indent=1)
    print(f'\n{len(by_id)} zones, {len(links)} borders -> docs/world-layout.json')
    sys.exit(1 if fails else 0)
