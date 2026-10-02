"""EMBERFALL - the player's guide, generated from the game itself.

Nothing here is written by hand. Every race, class, god, spell, quest, item,
creature and zone on the page is read out of data/ and docs/ at build time, so
the guide cannot drift from the game: change the data, run this, the guide is
right again. That is the whole design. A wiki somebody types is wrong a week
after the map moves, and this map has moved three times in three days.

    python3 tools/wiki.py          ->  docs/wiki/index.html

Art (creature portraits, the atlas) lives in docs/wiki/art/ and is copied in by
whoever renders it; the page links whatever is there and does without the rest.
"""
import json, os, glob, html, re, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, 'data', *p)
OUT = os.path.join(ROOT, 'docs', 'wiki')

def load(p, default=None):
    try:
        return json.load(open(p))
    except Exception:
        return {} if default is None else default

def clean(d):
    """Drop the _about / _comment keys the data files carry for their editors."""
    return {k: v for k, v in d.items() if not k.startswith('_') and isinstance(v, dict)}

MOBS     = clean(load(D('mobs.json')))
NPCS     = clean(load(D('npcs.json')))
SPELLS   = clean(load(D('spells.json')))
QUESTS   = clean(load(D('quests.json')))
RACES    = clean(load(D('races.json')))
CLASSES  = clean(load(D('classes.json')))
DEITIES  = clean(load(D('deities.json')))
FACTIONS = clean(load(D('factions.json')))
SKILLS   = load(D('skills.json')).get('skills', {})
ALIGN    = load(D('alignment.json'))
CONFIG   = load(D('config.json'))

ITEMS = {}
for _f in sorted(glob.glob(D('items', '*.json'))):
    for _k, _v in load(_f).items():
        if not _k.startswith('_') and isinstance(_v, dict):
            ITEMS[_k] = _v

LAYOUT = load(os.path.join(ROOT, 'docs', 'world-layout.json'))
AREAS  = LAYOUT.get('areas', {})
ZONES  = {z['id']: z for z in LAYOUT.get('zones', [])}

ZONE_FILES = {}
for _f in sorted(glob.glob(os.path.join(ROOT, 'data', 'zones', '*.json'))):
    ZONE_FILES[os.path.basename(_f)[:-5]] = load(_f)

def art(name):
    """Return the art path if we actually have that picture, else None."""
    p = os.path.join(OUT, 'art', name)
    return f'art/{name}' if os.path.exists(p) else None

# ---------------------------------------------------------------- derived
# Where does each creature spawn, and what does each zone hold?
SPAWNS_IN = collections.defaultdict(set)     # mob id -> {zone id}
ZONE_POOL = collections.defaultdict(collections.Counter)
for zid, zf in ZONE_FILES.items():
    for sp in zf.get('spawns', []) or []:
        for mob, w in (sp.get('pool') or {}).items():
            SPAWNS_IN[mob].add(zid)
            ZONE_POOL[zid][mob] += w

ZONE_NPCS = collections.defaultdict(list)    # zone id -> [npc id]
NPC_ZONE = {}
for zid, zf in ZONE_FILES.items():
    for e in zf.get('npcs', []) or []:
        if isinstance(e, dict) and e.get('id'):
            ZONE_NPCS[zid].append(e['id'])
            NPC_ZONE.setdefault(e['id'], zid)

DROPS_FROM = collections.defaultdict(set)    # item id -> {mob id}
for mid, m in MOBS.items():
    for entry in m.get('loot', []) or []:
        if isinstance(entry, dict) and entry.get('item'):
            DROPS_FROM[entry['item']].add(mid)

QUEST_WANTS = collections.defaultdict(set)   # item id -> {quest id}
QUEST_GIVES = collections.defaultdict(set)
for qid, q in QUESTS.items():
    for it in (q.get('wants') or {}):
        QUEST_WANTS[it].add(qid)
    r = q.get('reward') or {}
    for it in (r.get('items') or []):
        QUEST_GIVES[it].add(qid)
    _fr = q.get('first_reward_item')
    if isinstance(_fr, dict):          # one item per class
        for _it in _fr.values():
            QUEST_GIVES[_it].add(qid)
    elif _fr:
        QUEST_GIVES[_fr].add(qid)

def first_items(q):
    """What a task hands over the first time. Usually one item; sometimes one
    per class, and then the guide names them all."""
    fr = q.get('first_reward_item')
    if isinstance(fr, dict):
        seen = []
        for it in fr.values():
            if it not in seen:
                seen.append(it)
        return seen
    return [fr] if fr else []


def zone_name(zid):
    z = ZONES.get(zid)
    if z:
        return z['name']
    zf = ZONE_FILES.get(zid)
    return zf.get('name', zid.replace('_', ' ').title()) if zf else zid.replace('_', ' ').title()

def item_name(iid):
    return (ITEMS.get(iid) or {}).get('name', iid.replace('_', ' ').title())

def npc_name(nid):
    return (NPCS.get(nid) or {}).get('name', nid.replace('_', ' ').title())

def mob_name(mid, title=True):
    """Most creatures are named 'a gnoll pup'. That wants a capital at the
    start of a line and none in the middle of a sentence."""
    n = (MOBS.get(mid) or {}).get('name', mid.replace('_', ' ').title())
    if title and n[:2] in ('a ', 'an', 'th'):
        return n[0].upper() + n[1:]
    return n

def esc(s):
    return html.escape(str(s))

def hp_at(m, lv):
    return int(m.get('hp_base', 0)) + int(m.get('hp_per_level', 0)) * (lv - 1)


# ---------------------------------------------------------------- html bits
def kw(*parts):
    """A card's search key: everything you might plausibly type to find it."""
    s = ' '.join(str(p) for p in parts if p)
    return esc(re.sub(r'\s+', ' ', s.lower()))


def lead(label, text):
    """A run-in lead-in: the label sits inside the paragraph, not above it."""
    if not text:
        return ''
    return f'<p class="lead"><i>{esc(label)}</i> {text}</p>'


def reg(pairs):
    """A register: term, dotted leader, figure. The field-book way to show
    numbers, and it survives a phone better than a row of pills."""
    rows = [f'<div class="rg"><span class="rt">{esc(k)}</span>'
            f'<span class="rd"></span>'
            f'<span class="rv">{esc(v)}</span></div>'
            for k, v in pairs if v not in (None, '', [], {})]
    return f'<div class="reg">{"".join(rows)}</div>' if rows else ''


def entry(title, sub='', main='', aside='', key='', cid=None, realm=None,
          klass=None, medal=None):
    ra = (f' data-realm="{realm}"' if realm else '') + \
         (f' data-class="{klass}"' if klass else '')
    i = f' id="{cid}"' if cid else ''
    sb = f'<p class="e-sub">{sub}</p>' if sub else ''
    if medal:
        head = (f'<div class="e-head with-medal">'
                f'<span class="medal"><img src="{medal}" alt=""></span>'
                f'<span><h3>{title}</h3>{sb}</span></div>')
    else:
        head = f'<div class="e-head"><h3>{title}</h3>{sb}</div>'
    return (f'<article class="entry"{i}{ra} data-k="{key}">{head}'
            f'<div class="e-main">{main}</div>'
            f'<div class="e-aside">{aside}</div></article>')


def plate(src, caption='', cls=''):
    if not src:
        return ''
    cp = f'<figcaption>{caption}</figcaption>' if caption else ''
    return (f'<figure class="plate {cls}"><span class="mount">'
            f'<img src="{src}" alt=""></span>{cp}</figure>')


def para(*ps):
    return ''.join(f'<p>{p}</p>' for p in ps if p)


WORDS = ['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven',
         'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen',
         'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen', 'twenty']


def word(n, cap=False):
    """Small counts read better spelt out, and a sentence never opens with a
    numeral. Anything larger stays a figure."""
    w = WORDS[n] if 0 <= n < len(WORDS) else str(n)
    return w[0].upper() + w[1:] if cap else w


def cap_first(s_):
    """Upper-case the first letter and leave the rest alone. str.capitalize()
    lowercases everything after it, which eats proper nouns and any markup."""
    return s_[:1].upper() + s_[1:] if s_ else s_


def comma(items, last='and'):
    items = [str(i) for i in items if i]
    if len(items) <= 1:
        return ''.join(items)
    return f'{", ".join(items[:-1])} {last} {items[-1]}'


def area_span(aid):
    lv = [z['levels'] for z in ZONES.values() if z['area'] == aid and z.get('levels')]
    return (min(l[0] for l in lv), max(l[1] for l in lv)) if lv else None


def class_link(cid):
    n = esc(CLASSES.get(cid, {}).get('name', cid))
    return f'<a href="#class-{cid}">{n}</a>'


# ---------------------------------------------------------------- the world
def sec_world():
    built = sum(1 for z in ZONES.values() if z.get('built'))
    waiting = len(ZONES) - built
    hero = plate(art('world-atlas.png'),
                 'The Emberlands and the six realms around them. '
                 + ('Coloured ground is walkable today; the pale ground is '
                    'surveyed and waiting.' if waiting else
                    'Every realm on it is walkable.'), 'hero')
    intro = para(
        'Emberfall is an old world and an unhelpful one. Nothing marks your '
        'quest on the map, nothing carries you between towns, and when you '
        'die your body stays where it fell with everything you owned still '
        f'on it. You begin in <b>'
        f'{esc(zone_name(CONFIG.get("starting_zone", "emberhold")))}</b> at '
        f'level 1 and you reach level {CONFIG.get("max_level", 50)} on foot.',
        f'There are {len(ZONES)} zones across {len(AREAS)} realms, '
        + ('every one of them built and open. '
           if not waiting else f'{built} of them built and open. ')
        + 'Six realms each belong to one of the elephant '
        'gods, and the deeper you walk into one the less it resembles '
        'anywhere you have been.')
    rows = []
    for aid, a in AREAS.items():
        zs = [z for z in ZONES.values() if z['area'] == aid]
        sp = area_span(aid)
        god = DEITIES.get(a.get('deity') or '', {})
        rows.append(
            f'<tr data-realm="{aid}" data-k="'
            + kw(aid, a['name'], god.get('name'), god.get('title'))
            + f'"><th scope="row"><span class="pen-mark"></span>'
              f'<span class="realm">{esc(a["name"])}</span></th>'
            + f'<td class="num">{f"{sp[0]}&ndash;{sp[1]}" if sp else "&mdash;"}</td>'
            + f'<td class="num">{len(zs)}</td>'
            + '<td>' + (f'{esc(god["name"])}, <i>{esc(god.get("title", ""))}</i>'
                        if god else '<span class="q">no god of its own</span>')
            + '</td></tr>')
    table = ('<table class="register"><caption>The seven realms</caption>'
             '<thead><tr><th scope="col">Realm</th>'
             '<th scope="col" class="num">Levels</th>'
             '<th scope="col" class="num">Zones</th>'
             '<th scope="col">Its god</th></tr></thead>'
             f'<tbody>{"".join(rows)}</tbody></table>')
    return 'world', 'The World', hero + f'<div class="prose">{intro}</div>' + table


# ---------------------------------------------------------------- starting out
PATHCALLERS = [n for n, d in NPCS.items() if d.get('pathcaller')]


def _road_examples():
    """Two real destinations, so the formula means something."""
    fees = [(road_fee(z['id']), z['id']) for z in ZONES.values()
            if teleportable(z['id']) and z.get('levels')
            and z['levels'][1] > 1]
    if not fees:
        return ''
    fees.sort()
    lo, hi = fees[0], fees[-1]
    return (f'{comma(coin_parts(lo[0]))} to {zone_link(lo[1])}, '
            f'{comma(coin_parts(hi[0]))} to {zone_link(hi[1])}.')


def teleportable(zid):
    """World.teleportable: no interiors, no dungeons, nowhere that does not
    respawn you. A zone you have not walked to yourself is never on the road
    either, but that is yours to fix."""
    zf = ZONE_FILES.get(zid) or {}
    return not (zf.get('interior') or zf.get('no_respawn') or zf.get('dungeon'))


def road_fee(zid):
    """World.teleport_fee: the zone's top level squared times the fee, in
    copper; a city has no levels and pays a flat one."""
    lv = (ZONES.get(zid) or {}).get('levels') or []
    if not lv or lv[0] == lv[1] == 1:
        return int(CONFIG.get('teleport_city_fee', 1000))
    return int(CONFIG.get('teleport_fee_per_level_sq', 4)) * int(lv[1]) ** 2


def sec_start():
    c = CONFIG
    combos = sum(len(r.get('classes', [])) for r in RACES.values())
    eb = c.get('elders_blessing') or {}
    sides = ALIGN.get('sides', {})
    fname = lambda f: (FACTIONS.get(f) or {}).get('name', f.replace('_', ' ').title())
    cls_align = '; '.join(
        f'a {esc(CLASSES.get(k, {}).get("name", k).lower())} starts '
        f'{list(v.values())[0]} with the {list(v.keys())[0]} cities'
        for k, v in (ALIGN.get('classes') or {}).items())

    out = [entry(
        'Making a character',
        f'{len(RACES)} races, {len(CLASSES)} classes, {combos} legal pairings',
        para('Choose the race first. It decides the city you wake up in, who '
             'draws a sword when you walk through a gate, and which classes '
             'will take you at all &mdash; not every class is open to every '
             'race.',
             f'Every stat starts at {c.get("stat_base", 75)} before your race '
             f'touches it. You then have {c.get("stat_points", 25)} points to '
             f'place, and no more than {c.get("stat_point_max", 15)} of them '
             'may go into any single stat.'),
        reg([('Races', len(RACES)), ('Classes', len(CLASSES)),
             ('Legal pairings', combos),
             ('Every stat begins at', c.get('stat_base')),
             ('Points to place', c.get('stat_points')),
             ('Most into one stat', c.get('stat_point_max'))]),
        kw('character creation race class stats points', combos)), entry(
        'Levels and experience',
        f'The cap is {c.get("max_level", 50)}',
        para('Experience comes from what you kill, weighted by its level. '
             'Something a little above you pays best; something far below you '
             'pays almost nothing, so there is no farming the first zone to '
             'fifty.',
             'In a group everyone earns as long as the highest and lowest '
             f'members are within {c.get("group_xp_level_gap", 10)} levels. '
             'Outside that gap the low character is simply being carried.',
             (f'Until level {eb.get("until_level")} you carry the Elders&rsquo; '
              f'Blessing and earn {eb.get("xp_pct")}% more.') if eb else '',
             (f'The climb steepens. Up to level {c["xp_curve_from"]} a level '
              'is about the same number of kills as the last; past that, each '
              f'level asks {c["xp_curve_growth"] * 100:.1f}% more again for '
              'every level beyond it &mdash; so level 25 is about '
              f'{1 + (25 - c["xp_curve_from"]) * c["xp_curve_growth"]:.1f}'
              '&times; the work of level 10, and level '
              f'{c.get("max_level", 50)} about '
              f'{1 + (c.get("max_level", 50) - c["xp_curve_from"]) * c["xp_curve_growth"]:.1f}'
              '&times;.') if c.get('xp_curve_from') else ''),
        reg([('Level cap', c.get('max_level')),
             ('Group level gap', c.get('group_xp_level_gap')),
             ('Elders’ Blessing', f'+{eb.get("xp_pct")}% to level '
              f'{eb.get("until_level")}' if eb else '')]),
        kw('levels experience xp group cap elders blessing')), entry(
        'Dying',
        'It costs you, and then it costs you the walk back',
        para(f'Death takes {int(c.get("death_xp_loss", 0.1) * 100)}% of the '
             'experience you had earned toward your next level. '
             + ('Your corpse stays where you fell, holding everything you '
                'were carrying, and you wake at your bind point with nothing. '
                'Getting your things back means walking to the body.'
                if c.get('corpse_runs') else ''),
             'Bind yourself at a bindstone in a city before you travel. That '
             'stone is where you reappear, and how far it is from where you '
             'died is the real penalty.',
             f'A corpse lasts '
             f'{int(c.get("player_corpse_decay_seconds", 3600) / 60)} minutes.'),
        reg([('Experience lost',
              f'{int(c.get("death_xp_loss", 0.1) * 100)}%'),
             ('Corpse lasts',
              f'{int(c.get("player_corpse_decay_seconds", 3600) / 60)} min'),
             ('Back on your feet after', f'{c.get("respawn_delay")} sec')]),
        kw('death dying corpse run bind bindstone penalty')), entry(
        'Getting about',
        ('On foot, mostly' if PATHCALLERS else
         'On foot, and slower than you would like'),
        para('Roads run between zones and a zone line is a place on the '
             'ground you walk across. There is no map marker to click.',
             (f'A Pathcaller stands in {word(len(PATHCALLERS))} of the cities '
              '&mdash; '
              + comma(sorted({zone_link(NPC_ZONE[n]) for n in PATHCALLERS
                              if n in NPC_ZONE}))
              + ' &mdash; and will call the road to anywhere you have already '
                'walked to yourself. Not the Grove, not a room indoors, not a '
                'dungeon, and not while something is fighting you. The first '
                'journey anywhere is always on foot.') if PATHCALLERS else '',
             (f'The road is priced by where it goes: a zone&rsquo;s top level '
              f'squared, times {c.get("teleport_fee_per_level_sq", 4)} copper. '
              + _road_examples() + ' Another city is a flat '
              + comma(coin_parts(c.get('teleport_city_fee', 1000))) + '.')
             if PATHCALLERS else '',
             f'Sprinting is {c.get("sprint_speed_mult", 1.55)} times walking '
             f'pace and drains stamina, of which you have '
             f'{c.get("stamina_base", 100)} at level 1 and '
             f'{c.get("stamina_per_level", 4)} more each level. Run it dry and '
             'you walk until it returns.',
             f'You can carry {c.get("carry_base", 60)} stone, plus '
             f'{c.get("carry_per_level", 3)} a level and '
             f'{c.get("carry_per_str", 3)} for each point of strength. Coin '
             'has weight, which is why bankers exist.'),
        reg([('Sprint', f'{c.get("sprint_speed_mult")}× walking'),
             ('Stamina at level 1', c.get('stamina_base')),
             ('Stamina a level', f'+{c.get("stamina_per_level")}'),
             ('Carried weight', c.get('carry_base')),
             ('Bag slots', c.get('inventory_slots')),
             ('Bank slots', c.get('bank_slots'))]),
        kw('travel movement sprint stamina carry weight inventory bank')), entry(
        'Who trusts you',
        'Every city and every warband keeps its own tally',
        para('Kill something and several tallies move at once: the thing&rsquo;s '
             'kin think worse of you and its enemies think better. At '
             f'{ALIGN.get("hostile", -1500)} a faction is hostile and its '
             'guards attack on sight.',
             'Your race sets the opening position. The good cities are '
             + esc(comma([fname(f) for f in (sides.get('good') or [])]))
             + '; the evil ones are '
             + esc(comma([fname(f) for f in (sides.get('evil') or [])]))
             + '. An evil race begins hostile to the good side and a good or '
               'neutral race to the evil side. Everyone not on a side &mdash; '
               'traders, hermits, the neutral holds &mdash; begins '
               'indifferent and can be won round.',
             f'Some classes carry their own reputation: {cls_align}.',
             'City guards are not a fight you win. They stand at level '
             f'{c.get("max_level", 50) + c.get("guard_levels_over_cap", 20)}, '
             f'{c.get("guard_health_mult", 10):g}&times; the health and '
             f'{c.get("guard_damage_mult", 3):g}&times; the damage of an '
             'ordinary monster that far above you.'),
        reg([('Hostile at', ALIGN.get('hostile')),
             ('Factions tracked', len(FACTIONS)),
             ('Guards stand at level',
              c.get('max_level', 50) + c.get('guard_levels_over_cap', 20)),
             ('Their health', f'{c.get("guard_health_mult", 10):g}\u00d7'),
             ('Their damage', f'{c.get("guard_damage_mult", 3):g}\u00d7')]),
        kw('faction alignment reputation hostile guards good evil')), entry(
        'Guilds',
        f'From level {c.get("guild_min_level", 10)}',
        para('A registrar in any city will charter a guild once you are level '
             f'{c.get("guild_min_level", 10)} and can pay the fee.'),
        reg([('Minimum level', c.get('guild_min_level')),
             ('Charter fee', f'{c.get("guild_fee", 0) // 100} gold')]),
        kw('guild charter registrar fee'))]
    return 'start', 'Starting Out', ''.join(out)


# ---------------------------------------------------------------- races
STATN = {'str': 'Strength', 'sta': 'Stamina', 'agi': 'Agility',
         'wis': 'Wisdom', 'int': 'Intellect'}
ALIGN_WORD = {'good': 'a good people', 'evil': 'an evil people',
              'neutral': 'a neutral people'}


def _tick_scale():
    """How far from the base does any race actually stray? That is the scale."""
    base = CONFIG.get('stat_base', 75)
    d = [abs(v - base) for r in RACES.values()
         for v in (r.get('stats') or {}).values()]
    return max(d) or 1


def ticks(stats_):
    """Five stats against a common baseline. What matters is the deviation,
    so the baseline is drawn and the bar grows out of it either way."""
    base = CONFIG.get('stat_base', 75)
    span = _tick_scale()
    rows = []
    for k, label in STATN.items():
        v = stats_.get(k, base)
        d = v - base
        w = abs(d) / span * 50.0
        pos = f'left:50%;width:{w:.1f}%' if d > 0 else f'left:{50 - w:.1f}%;width:{w:.1f}%'
        bar = f'<i style="{pos}"></i>' if d else ''
        rows.append(f'<div class="tick"><span class="tl">{label}</span>'
                    f'<span class="tt">{bar}</span>'
                    f'<span class="tv">{v}<em>{d:+d}</em></span></div>'
                    if d else
                    f'<div class="tick"><span class="tl">{label}</span>'
                    f'<span class="tt"></span>'
                    f'<span class="tv">{v}<em class="z">&mdash;</em></span></div>')
    return (f'<div class="ticks">{"".join(rows)}'
            f'<p class="tnote">Against the common base of {base}.</p></div>')


def sec_races():
    out = []
    for rid, r in RACES.items():
        open_to = [c for c in r.get('classes', [])]
        shut = [c for c in CLASSES if c not in open_to]
        home = r.get('home', '')
        realm = (ZONES.get(home) or {}).get('area')
        main = (para(esc(r.get('description', '')))
                + lead('Open to', comma([class_link(c) for c in open_to]) + '.')
                + (lead('Closed to', comma([esc(CLASSES[c]['name']) for c in shut])
                        + '.') if shut else '')
                + lead('Trait', esc(r.get('trait_text', ''))))
        out.append(entry(
            esc(r.get('name', rid)),
            f'{ALIGN_WORD.get(r.get("alignment", "neutral"), "")}, '
            f'waking in {esc(zone_name(home))}',
            main, ticks(r.get('stats') or {}),
            kw(rid, r.get('name'), r.get('description'), r.get('alignment'),
               r.get('trait_text'), zone_name(home),
               *[CLASSES.get(c, {}).get('name', c) for c in open_to]),
            cid=f'race-{rid}', realm=realm))
    lead_in = ('<div class="prose">' + para(
        'A race is the one choice you cannot undo. It places you on the map, '
        'sets the five stats you will build on for fifty levels, decides '
        'which classes will have you, and tells every city guard in the world '
        'whether to nod or draw.') + '</div>')
    return 'races', 'Races', lead_in + ''.join(out)


# ---------------------------------------------------------------- the shell
# The look is a field book: the atlas's paper, its ink, its two typefaces.
# Structure is carried by rules and indentation, not by boxes -- a box here
# means something really is a plate laid on the page, which is why the only
# boxed things are pictures. Colour is information: an entry wears its realm's
# ink and nothing wears a colour for decoration.
#
# Deliberately a paper object in one light. color-scheme is pinned so a dark
# browser does not invert a parchment map into a bruise.
CSS = r"""
:root{ color-scheme: light; }
*{box-sizing:border-box}
html{ -webkit-text-size-adjust:100% }
body{
  margin:0;
  background-color:var(--paper);
  background-image:var(--paper-img);
  background-size:512px 512px;
  color:var(--ink);
  font:400 17.5px/1.62 Pagella,"Palatino Linotype",Palatino,"Book Antiqua",Georgia,serif;
  font-feature-settings:"kern" 1,"liga" 1;
}
a{color:var(--ink); text-decoration:underline;
  text-decoration-color:var(--rule); text-underline-offset:2.5px}
a:hover{text-decoration-color:var(--ink)}
:focus-visible{outline:2px solid var(--ink); outline-offset:3px}
.skip{position:absolute; left:-9999px}
.skip:focus{left:14px; top:12px; z-index:60; background:var(--plate);
  border:1px solid var(--ink); padding:8px 14px}

/* ---- masthead ---- */
header.masthead{
  position:sticky; top:0; z-index:20; background:var(--plate);
  border-bottom:1px solid var(--rule); box-shadow:0 2px 0 var(--hair);
}
.mh{max-width:1220px; margin:0 auto; padding:13px 30px 12px;
  display:flex; align-items:baseline; gap:20px; flex-wrap:wrap}
.wordmark{
  font:400 41px/1 Chorus,"Apple Chancery","URW Chancery L",cursive;
  font-style:italic; margin:0; color:var(--ink);
}
.mh-sub{margin:0; font-style:italic; font-size:15px; color:var(--ink-soft)}
.find{margin-left:auto; display:flex; align-items:baseline}
.find label{position:absolute; left:-9999px}
#q{font:inherit; font-size:15.5px; background:transparent; color:var(--ink);
  border:0; border-bottom:1px solid var(--rule); padding:5px 2px; width:262px}
#q::placeholder{color:var(--ink-faint); font-style:italic}
#q:focus{outline:none; border-bottom-width:2px; border-bottom-color:var(--ink);
  padding-bottom:4px}

/* ---- frame: index rail, reading column ---- */
.frame{max-width:1220px; margin:0 auto; padding:0 30px;
  display:grid; grid-template-columns:192px minmax(0,1fr); gap:0 48px}
nav.index{position:sticky; top:calc(var(--mh,88px) + 18px); align-self:start; padding:30px 0 40px}
nav.index ol{list-style:none; margin:0; padding:0}
nav.index button{
  font:inherit; font-size:16px; text-align:left; width:100%; cursor:pointer;
  background:none; border:0; border-left:2px solid transparent;
  padding:5px 4px 5px 13px; color:var(--ink-soft);
  display:flex; justify-content:space-between; align-items:baseline; gap:10px;
}
nav.index button:hover{color:var(--ink)}
nav.index button[aria-current="true"]{color:var(--ink); font-weight:700;
  border-left-color:var(--ink)}
nav.index .n{font-size:12.5px; color:var(--ink-faint);
  font-variant-numeric:tabular-nums; font-weight:400}
main{padding:30px 0 100px; min-width:0}

/* ---- sections ---- */
.sec-title{
  font:400 34px/1.1 Chorus,"Apple Chancery",cursive; font-style:italic;
  margin:0 0 16px; padding-bottom:11px; border-bottom:1px solid var(--rule);
}
.hitnote{margin:0 0 4px; font-style:italic; color:var(--ink-soft);
  font-size:15px}
.hitnote:empty{display:none}
.prose{max-width:64ch; margin:0 0 6px}
.prose p, .e-main p{margin:0 0 .82em}
.prose p:last-child, .e-main p:last-child{margin-bottom:0}

/* ---- an entry: a register line, not a card ---- */
.entry{
  display:grid; grid-template-columns:minmax(0,1fr) minmax(0,296px);
  grid-template-areas:"head head" "main aside";
  column-gap:48px; border-top:1px solid var(--hair); padding:26px 0 30px;
}
.entry{scroll-margin-top:calc(var(--mh,88px) + 26px)}
.e-head{grid-area:head; margin:0 0 14px}
.e-head.with-medal{display:flex; gap:19px; align-items:flex-start}
.medal{flex:0 0 auto; width:94px; height:94px; background:var(--plate);
  padding:5px; border:1px solid var(--rule);
  box-shadow:0 1px 1px rgba(62,44,30,.16)}
.medal img{display:block; width:100%; height:100%;
  border:1px solid var(--hair)}
.e-head h3{margin:0; font:700 22px/1.25 Pagella,Palatino,Georgia,serif}
.e-sub{margin:3px 0 0; font-style:italic; font-size:15.5px;
  color:var(--ink-soft); max-width:52ch}
.e-main{grid-area:main; max-width:58ch}
.e-aside{grid-area:aside}
.lead{margin:0 0 .55em}
.lead i{color:var(--ink-soft)}
.entry[data-realm] .e-head h3,
.entry[data-class] .e-head h3{color:var(--pen-text)}

/* ---- register: term, dotted leader, figure ---- */
.reg{margin:0}
.rg{display:flex; align-items:baseline; gap:7px; font-size:14.5px;
  padding:2.5px 0}
.rt{color:var(--ink-soft)}
.rd{flex:1 1 auto; border-bottom:1px dotted var(--rule);
  position:relative; top:-4px; min-width:14px}
.rv{font-variant-numeric:tabular-nums; white-space:nowrap}

/* ---- the stat scale: deviation from a common base ---- */
.ticks{margin:0}
.tick{display:grid; grid-template-columns:74px minmax(60px,1fr) 66px;
  align-items:center; gap:11px; font-size:13.5px; padding:2.5px 0}
.tl{color:var(--ink-soft)}
.tt{position:relative; height:11px}
.tt::before{content:""; position:absolute; left:0; right:0; top:5px;
  border-top:1px solid var(--hair)}
.tt::after{content:""; position:absolute; left:50%; top:0; bottom:0;
  border-left:1px solid var(--ink-faint)}
.tt i{position:absolute; top:3.5px; height:4px; background:var(--ink)}
.tv{text-align:right; font-variant-numeric:tabular-nums}
.tv em{font-style:normal; font-size:12px; color:var(--ink-soft);
  margin-left:5px}
.tv em.z{color:var(--ink-faint)}
.a-head{margin:20px 0 8px; font:400 15px/1.2 Chorus,"Apple Chancery",cursive;
  font-style:italic; color:var(--ink-soft)}
.tnote{margin:9px 0 0; font-size:12.5px; font-style:italic;
  color:var(--ink-faint)}

/* ---- a plate: the only boxed thing on the page ---- */
figure.plate{margin:0 0 32px}
.plate .mount{display:block; background:var(--plate); padding:9px;
  border:1px solid var(--rule);
  box-shadow:0 1px 1px rgba(62,44,30,.16), 0 10px 26px -14px rgba(62,44,30,.5)}
.plate img{display:block; width:100%; height:auto;
  border:1px solid var(--hair)}
.plate.hero .mount{max-height:76vh; overflow:hidden; display:flex}
.plate.hero img{max-height:calc(76vh - 20px); width:auto; margin:0 auto;
  object-fit:contain}
.plate figcaption{margin:11px 0 0; max-width:56ch;
  font:400 16px/1.45 Chorus,"Apple Chancery",cursive; font-style:italic;
  color:var(--ink-soft)}

/* ---- register table ---- */
.register{width:100%; border-collapse:collapse; font-size:15.5px;
  margin:28px 0 0}
.register caption{text-align:left; padding:0 0 9px;
  font:400 21px/1.2 Chorus,"Apple Chancery",cursive; font-style:italic;
  color:var(--ink)}
.register th[scope=col]{font-weight:400; font-style:italic; font-size:14px;
  color:var(--ink-soft); text-align:left; padding:0 14px 7px 0;
  border-bottom:1px solid var(--rule)}
.register td, .register th[scope=row]{padding:9px 14px 9px 0;
  border-bottom:1px solid var(--hair); text-align:left; font-weight:400}
.register tbody tr:last-child td,
.register tbody tr:last-child th{border-bottom:1px solid var(--rule)}
.num{text-align:right !important; font-variant-numeric:tabular-nums;
  white-space:nowrap; width:1%}
.pen-mark{display:inline-block; width:9px; height:9px; background:var(--pen);
  margin-right:10px; vertical-align:1px}
.realm{font:400 20px/1 Chorus,"Apple Chancery",cursive; font-style:italic;
  color:var(--pen-text)}
.q{font-style:italic; color:var(--ink-soft)}

.grp{margin:0 0 30px}
.grp>h2{font:400 27px/1.15 Chorus,"Apple Chancery",cursive; font-style:italic;
  color:var(--pen-text); margin:36px 0 6px; padding-bottom:9px;
  border-bottom:1px solid var(--rule); display:flex; align-items:baseline;
  justify-content:space-between; gap:16px}
.grp>h2 em{font:italic 400 14px/1 Pagella,Georgia,serif; color:var(--ink-soft);
  white-space:nowrap}
.grp .prose{margin:12px 0 4px}
.grp > .entry:first-of-type{border-top:0; padding-top:20px}
.spells{margin:6px 0 0}
.srow{display:grid; grid-template-columns:58px minmax(0,1fr) 268px;
  gap:0 18px; align-items:baseline; padding:11px 0 12px;
  border-bottom:1px solid var(--hair)}
.srow.head{padding:8px 0 7px; border-bottom:1px solid var(--rule);
  font-style:italic; font-size:14px; color:var(--ink-soft)}
.srow .lv{font-weight:700; font-variant-numeric:tabular-nums}
.srow.head .lv{font-weight:400}
.srow .nm{font-weight:700}
.srow .d{display:block; font-size:14.5px; color:var(--ink-soft);
  max-width:66ch; margin-top:1px}
.srow .fig{display:block; font-size:13.5px; font-style:italic;
  color:var(--ink-faint); max-width:66ch; margin-top:2px}
.srow .cost{display:grid; grid-template-columns:repeat(3,1fr); gap:0 12px}
.srow .cost b{font-weight:400; text-align:right;
  font-variant-numeric:tabular-nums}
.srow.head .cost b{font-weight:400}
/* the skill matrix: 35 rows against eight classes, so it scrolls sideways
   on a narrow screen with the skill names pinned */
.mwrap{overflow-x:auto; margin:6px 0 0; -webkit-overflow-scrolling:touch}
table.matrix{border-collapse:collapse; font-size:15px; min-width:100%}
.matrix th[scope=col]{font-weight:400; font-style:italic; font-size:13.5px;
  color:var(--pen-text); text-align:right; padding:0 0 8px 15px;
  border-bottom:1px solid var(--rule); white-space:nowrap;
  vertical-align:bottom}
.matrix th[scope=col]:first-child{text-align:left; padding-left:0;
  color:var(--ink-soft)}
.matrix th[scope=row]{font-weight:400; text-align:left;
  padding:9px 20px 9px 0; border-bottom:1px solid var(--hair);
  position:sticky; left:0; background-color:var(--paper)}
.matrix td{padding:9px 0 9px 15px; border-bottom:1px solid var(--hair);
  text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap}
.matrix td.none{color:var(--ink-faint)}
.late{display:block; font-size:12.5px; font-style:italic;
  color:var(--ink-soft); white-space:normal; max-width:26ch}

/* a task: what it is, what it wants, what it pays */
.qrow{display:grid; grid-template-columns:minmax(0,1fr) 210px 235px;
  gap:0 26px; align-items:baseline; padding:12px 0 13px;
  border-bottom:1px solid var(--hair)}
.qrow.head{padding:8px 0 7px; border-bottom:1px solid var(--rule);
  font-style:italic; font-size:14px; color:var(--ink-soft)}
.qrow .nm{font-weight:700}
.qrow .d{display:block; font-size:14.5px; color:var(--ink-soft); margin-top:1px}
.qrow .fig{display:block; font-size:13.5px; font-style:italic;
  color:var(--ink-faint); margin-top:2px}
.qrow .qw, .qrow .qp{font-size:15px}
.qrow em{display:block; font-style:italic; font-size:13.5px;
  color:var(--ink-faint); margin-top:3px}
/* a creature: its portrait floated into the description, its numbers beside */
.brow{display:grid; grid-template-columns:minmax(0,1fr) 372px; gap:0 34px;
  padding:16px 0 18px; border-bottom:1px solid var(--hair);
  scroll-margin-top:calc(var(--mh,88px) + 26px)}
.bname{min-width:0}
.bname img{float:left; width:88px; height:88px; margin:3px 18px 6px 0;
  background:var(--plate); border:1px solid var(--rule); padding:4px}
.bname .nm{font:700 19px/1.3 Pagella,Georgia,serif; display:block}
.bname .d{display:block; font-size:14.5px; color:var(--ink-soft);
  margin-top:3px}
.bname .fig{display:block; font-size:13.5px; font-style:italic;
  color:var(--ink-faint); margin-top:4px}
.brow .reg{margin-top:2px; column-count:2; column-gap:26px}
.brow .rg{break-inside:avoid}
.grp > figure.plate{margin:16px 0 8px}
/* an item: what it is on the left, what it does on the right */
.irow{display:grid; grid-template-columns:minmax(0,1fr) 330px; gap:0 32px;
  padding:11px 0 12px; border-bottom:1px solid var(--hair);
  scroll-margin-top:calc(var(--mh,88px) + 26px)}
.iname .nm{font-weight:700}
.iname .shape{float:left; width:74px; height:74px; object-fit:contain;
  margin:-6px 15px 2px -4px}
.iname .lore{display:block; font-size:14.5px; color:var(--ink-soft);
  margin-top:2px}
.iname .fig{display:block; font-size:13.5px; font-style:italic;
  color:var(--ink-faint); margin-top:3px}
.istat span{display:block; font-size:14.5px; color:var(--ink-soft)}
.istat span:first-child{color:var(--ink)}
.soon{border-top:1px solid var(--hair); padding:26px 0 8px;
  max-width:58ch; color:var(--ink-soft)}
.soon h3{margin:0 0 .5em; font:700 22px/1.25 Pagella,Georgia,serif;
  color:var(--ink)}
footer{border-top:1px solid var(--rule); margin:0 auto; max-width:1220px;
  padding:20px 30px 70px; color:var(--ink-soft); font-size:14px;
  max-width:1220px}
footer p{margin:0 0 .4em; max-width:74ch}
footer code{font-family:inherit; font-style:italic}

@media (max-width:920px){
  .mh{padding:9px 16px 8px; gap:10px 14px}
  .wordmark{font-size:27px}
  .mh-sub{display:none}
  .find{margin-left:auto; flex:1 1 150px; min-width:0}
  #q{width:100%; font-size:15px}
  body{font-size:16.5px}
  .frame{grid-template-columns:minmax(0,1fr); gap:0; padding:0 16px}
  nav.index{position:sticky; top:var(--mh,54px); z-index:15; padding:0;
    background-color:var(--paper); background-image:var(--paper-img);
    border-bottom:1px solid var(--rule); margin:0 -16px}
  nav.index ol{display:flex; gap:0; overflow-x:auto; padding:0 12px;
    scrollbar-width:none}
  nav.index ol::-webkit-scrollbar{display:none}
  nav.index li{flex:0 0 auto}
  nav.index button{width:auto; border-left:0; border-bottom:2px solid transparent;
    padding:10px 11px; white-space:nowrap}
  nav.index button[aria-current="true"]{border-bottom-color:var(--ink)}
  main{padding:22px 0 80px}
  .sec-title{font-size:29px}
  .entry{grid-template-columns:minmax(0,1fr);
    grid-template-areas:"head" "main" "aside"; column-gap:0}
  .e-aside{margin-top:18px}
  .medal{width:74px; height:74px}
  .grp>h2{font-size:23px; display:block}
  .grp>h2 em{display:block; margin-top:5px; white-space:normal}
  .spells, .spells tbody{display:block; width:auto}
  .spells thead{display:none}
  /* On a phone a row folds into a little block, its costs on one line
     underneath with each figure named. */
  .srow{display:block; padding:13px 0}
  .srow.head{display:none}
  .srow .lv{display:inline; font-weight:400; font-size:13.5px;
    color:var(--ink-soft)}
  .srow .lv::before{content:"level "; color:var(--ink-faint)}
  .srow .lv:empty{display:none}
  .srow .cost{display:inline}
  .srow .cost b{display:inline; margin-right:15px; font-size:13.5px;
    color:var(--ink-soft)}
  .srow .cost b::before{content:attr(data-l) " "; color:var(--ink-faint)}
  .srow .sp{display:block; margin-bottom:7px}
  .matrix{font-size:14px}
  .matrix th[scope=col]{font-size:12.5px; padding-left:11px}
  .matrix td{padding-left:11px}
  .qrow{display:block; padding:13px 0}
  .qrow.head{display:none}
  .qrow .qw, .qrow .qp{display:block; margin-top:6px; font-size:14.5px}
  .qrow .qw::before{content:"Brings "; color:var(--ink-faint);
    font-style:italic}
  .qrow .qp::before{content:"Pays "; color:var(--ink-faint); font-style:italic}
  .qrow em{display:block; margin-left:0}
  .brow{display:block; padding:15px 0}
  .brow .reg{column-count:1}
  .bname img{width:70px; height:70px; margin:2px 14px 4px 0}
  .brow .bnum{margin-top:10px; clear:both}
  .irow{display:block; padding:12px 0}
  .iname .shape{width:62px; height:62px; margin:-4px 12px 2px -2px}
  .istat{margin-top:5px}
  footer{padding:18px}
}
@media (prefers-reduced-motion:reduce){
  *{transition:none !important; animation:none !important}
}
"""

JS = r"""
const secs = [...document.querySelectorAll('section.sec')];
const tabs = [...document.querySelectorAll('nav.index button')];
const q = document.getElementById('q');

function measure(){
  const h = document.querySelector('header.masthead').offsetHeight;
  document.documentElement.style.setProperty('--mh', h + 'px');
}
addEventListener('resize', measure);
measure();

function show(id, keepHash){
  secs.forEach(s => { s.hidden = s.id !== id; });
  tabs.forEach(t => t.setAttribute('aria-current', String(t.dataset.sec === id)));
  /* Keep the hash when it already names an entry inside this section --
     rewriting it to the section id makes the browser scroll to the top. */
  if (!keepHash) history.replaceState(null, '', '#' + id);
}
tabs.forEach(t => t.onclick = () => { show(t.dataset.sec); window.scrollTo({top:0}); });

function filter(){
  const t = q.value.trim().toLowerCase();
  secs.forEach(s => {
    let hits = 0, seen = 0;
    s.querySelectorAll('[data-k]').forEach(c => {
      seen++;
      const ok = !t || (c.dataset.k || '').includes(t);
      c.hidden = !ok;
      if (ok) hits++;
    });
    const note = s.querySelector('.hitnote');
    if (note){
      note.textContent = !t ? ''
        : hits ? (hits + (hits === 1 ? ' entry matches ' : ' entries match ') + '“' + q.value.trim() + '”.')
               : 'Nothing here matches “' + q.value.trim() + '”. Try a race, a class or a realm.';
    }
    const tab = tabs.find(x => x.dataset.sec === s.id);
    const n = tab && tab.querySelector('.n');
    if (n) n.textContent = (t && seen) ? hits : n.dataset.total;
  });
}
q.addEventListener('input', filter);
q.form.addEventListener('submit', e => e.preventDefault());

/* #race-dwarf and the like open the right section and scroll to the entry. */
function jump(){
  const h = decodeURIComponent(location.hash.slice(1));
  if (!h) return;
  const el = document.getElementById(h);
  if (!el) return;
  const s = el.closest('section.sec');
  if (s && s.hidden) show(s.id, true);
  if (el !== s) el.scrollIntoView({block:'center'});
}
addEventListener('hashchange', jump);
document.addEventListener('click', e => {
  if (e.target.closest('a[href^="#"]')) setTimeout(jump, 0);
});
const start = location.hash.slice(1) && document.getElementById(location.hash.slice(1));
const deep = start && !start.classList.contains('sec');
show(start ? (start.closest('section.sec') || secs[0]).id : secs[0].id, deep);
const toTop = () => window.scrollTo({top: 0});
if (deep) jump();
else { toTop(); requestAnimationFrame(toTop); addEventListener('load', toTop); }
measure();
"""


# ---------------------------------------------------------------- classes
# What a spell does, in a word. The game files use these keys; the guide has
# to say them out loud.
KIND = {
    'damage': 'Damage', 'dot': 'Damage over time', 'heal': 'Healing',
    'buff': 'Blessings', 'pet': 'A servant of its own', 'shot': 'Archery',
    'lifetap': 'Draining life', 'snare': 'Snares', 'root': 'Roots',
    'slow': 'Slowing a fight', 'stun': 'Stuns', 'fear': 'Fear',
    'fear_area': 'Fear, in a crowd', 'taunt': 'Taunts',
    'taunt_area': 'Taunting a crowd', 'cure': 'Curing poison and disease',
    'restore_mana': 'Giving mana back', 'gate': 'Gating home',
    'track': 'Tracking', 'feign_death': 'Playing dead', 'hide': 'Hiding',
    'sneak': 'Sneaking', 'vanish': 'Vanishing', 'evade': 'Slipping aggro',
    'fish': 'Fishing', 'grove': 'The Grove',
}
STAT_LONG = {'str': 'strength', 'sta': 'stamina', 'agi': 'agility',
             'wis': 'wisdom', 'int': 'intellect'}
SLOT_WORD = {'primary': 'in hand', 'secondary': 'in the off hand',
             'range': 'slung', 'chest': 'on the back', 'head': 'on the head',
             'legs': 'on the legs', 'feet': 'on the feet',
             'hands': 'on the hands', 'arms': 'on the arms'}

CLASS_SPELLS = collections.defaultdict(list)   # class -> [(level, spell id)]
for _sid, _sp in SPELLS.items():
    for _c, _lv in (_sp.get('classes') or {}).items():
        CLASS_SPELLS[_c].append((int(_lv), _sid))
for _c in CLASS_SPELLS:
    CLASS_SPELLS[_c].sort()

RACES_FOR = collections.defaultdict(list)      # class -> [race id]
for _rid, _r in RACES.items():
    for _c in _r.get('classes', []):
        RACES_FOR[_c].append(_rid)


def first_of_each_kind(cid):
    """The level a class first gets each sort of magic. This is the shape of
    a class in one list: when the pet arrives, when you can finally gate."""
    first = {}
    for lv, sid in CLASS_SPELLS.get(cid, []):
        k = SPELLS[sid].get('type')
        if k and k not in first:
            first[k] = (lv, sid)
    rows = sorted(first.items(), key=lambda kv: (kv[1][0], KIND.get(kv[0], kv[0])))
    return [(KIND.get(k, k.replace('_', ' ').title()),
             f'level {lv}' if lv > 1 else 'from the start')
            for k, (lv, sid) in rows]


def sec_classes():
    cap = CONFIG.get('max_level', 50)
    out = []
    for cid, c in CLASSES.items():
        spells = CLASS_SPELLS.get(cid, [])
        lvs = [lv for lv, _ in spells]
        hp1 = c.get('hp_base', 0)
        hp50 = hp1 + c.get('hp_per_level', 0) * (cap - 1)
        mp1 = c.get('mana_base', 0)
        mp50 = mp1 + c.get('mana_per_level', 0) * (cap - 1)
        cast = c.get('caster_stat')

        # the sub-line: how much there is to learn, and over what span. The
        # data marks an ability apart from a spell, and a warrior would object
        # to being told he has thirty spells.
        abil = sum(1 for _, sid in spells if SPELLS[sid].get('ability'))
        magic = len(spells) - abil
        if not spells:
            what = 'Nothing to learn'
        elif not magic:
            what = f'{abil} abilities'
        elif not abil:
            what = f'{magic} spells'
        else:
            what = f'{magic} spells and {abil} abilities'
        if not spells:
            sub = what
        elif len(set(lvs)) == 1:
            sub = f'{what}, all from the start'
        else:
            sub = f'{what}, learned between levels {min(lvs)} and {max(lvs)}'
        if cast:
            sub += f', cast on {STAT_LONG.get(cast, cast)}'

        kit = []
        for slot, iid in (c.get('starting_items') or {}).items():
            kit.append(f'{esc(item_name(iid))} {SLOT_WORD.get(slot, "")}'.strip())
        for iid, n in (c.get('starting_pack') or {}).items():
            what = item_name(iid).lower()
            if n > 1 and not what.endswith('s'):
                what += 's'
            kit.append(f'{n} {esc(what)}')

        races = [f'<a href="#race-{r}">{esc(RACES[r]["name"])}</a>'
                 for r in RACES_FOR.get(cid, [])]
        shut = [esc(RACES[r]['name']) for r in RACES
                if r not in RACES_FOR.get(cid, [])]
        keys = [STAT_LONG.get(k, k) for k in c.get('key_stats', [])]

        arch = c.get('archery') or {}
        main = (para(esc(c.get('description', '')))
                + lead('Open to', comma(races) + '.')
                + (lead('Closed to', comma(shut) + '.') if shut else '')
                + lead('Leans on', comma(keys) + '.')
                + (lead('Starts with', comma(kit) + '.') if kit else '')
                + (lead('With a bow',
                        f'{int((arch.get("dmg", 1) - 1) * 100)}% more damage '
                        f'and {int((arch.get("range", 1) - 1) * 100)}% more '
                        'reach than anyone else.') if arch else ''))

        nums = [('Health at level 1', hp1),
                ('Health at level ' + str(cap), hp50)]
        if mp50:
            nums += [('Mana at level 1', mp1),
                     ('Mana at level ' + str(cap), mp50)]
        else:
            nums += [('Mana', 'none')]
        nums += [('Armour, before gear', f'{c.get("ac_base", 0) + 1} to '
                                         f'{c.get("ac_base", 0) + cap}'),
                 ('Weapon skill', f'{c.get("melee_skill", 1):g}×')]
        for what, v in (c.get('crit') or {}).items():
            nums.append((f'{what.title()} critical',
                         f'{v[0] * 100:.0f}% to {(v[0] + v[1] * cap) * 100:.0f}%'))
        nums += [('Health regained a tick', c.get('hp_regen')),
                 ('Mana regained a tick', c.get('mana_regen') or None)]

        kinds = first_of_each_kind(cid)
        aside = reg(nums) + (
            f'<h4 class="a-head">What arrives, and when</h4>{reg(kinds)}'
            if kinds else '')

        out.append(entry(
            esc(c.get('name', cid)), sub, main, aside,
            kw(cid, c.get('name'), c.get('description'), sub,
               *[RACES[r]['name'] for r in RACES_FOR.get(cid, [])],
               *keys, *[k for k, _ in kinds]),
            cid=f'class-{cid}', klass=cid))

    lead_in = ('<div class="prose">' + para(
        'Eight trades, and the one you pick decides how a fight feels for '
        'fifty levels: whether you stand in front of it, heal the person who '
        'does, or make sure it never reaches either of you. Health, mana and '
        'armour below are what the class gives you before a single piece of '
        'gear goes on.') + '</div>')
    return 'classes', 'Classes', lead_in + ''.join(out)



# ---------------------------------------------------------------- the gods
def cut_deity_portraits():
    """The game keeps the nine faces on one 512px sheet and cuts them at run
    time. Do the same here, so the guide shows the portraits the character
    sheet shows and nobody has to export anything by hand."""
    src = os.path.join(ROOT, 'assets', 'deities', 'deities_128.png')
    if not os.path.exists(src):
        return
    try:
        from PIL import Image
    except Exception:
        return
    sheet = None
    for did, d in DEITIES.items():
        at = d.get('portrait')
        if not at:
            continue
        out = os.path.join(OUT, 'art', f'god_{did}.png')
        if os.path.exists(out) and os.path.getmtime(out) > os.path.getmtime(src):
            continue
        sheet = sheet or Image.open(src).convert('RGBA')
        os.makedirs(os.path.dirname(out), exist_ok=True)
        sheet.crop((at[0], at[1], at[0] + 128, at[1] + 128)).save(out)


# What a god's gift actually moves, said in words rather than a data key.
BONUS = {
    'hp_regen': 'Health regained a tick', 'hp_pct': 'Maximum health',
    'mana_pct': 'Maximum mana', 'dmg': 'Melee damage',
    'run_speed_pct': 'Running speed', 'xp_loss_pct': 'Experience lost on death',
    'notice_pct': 'How soon a monster notices you',
    'dot_pct': 'Damage over time',
}

REALM_OF = {a.get('deity'): aid for aid, a in AREAS.items() if a.get('deity')}
ALIGN_PLURAL = {'good': 'good', 'evil': 'evil', 'neutral': 'neutral'}


def sec_gods():
    cut_deity_portraits()
    out = []
    for did, d in DEITIES.items():
        aid = REALM_OF.get(did)
        area = AREAS.get(aid or '', {})
        span = area_span(aid) if aid else None
        zs = [z for z in ZONES.values() if z['area'] == aid] if aid else []

        sides = d.get('alignments') or []
        only = d.get('races') or []
        if only:
            who = comma([esc(RACES[r]['name']) for r in only if r in RACES])
            takes = f'Only {who}.'
        elif sides:
            allowed = [r for r, rr in RACES.items()
                       if rr.get('alignment', 'neutral') in sides]
            barred = [esc(RACES[r]['name']) for r in RACES if r not in allowed]
            takes = (comma([ALIGN_PLURAL.get(s, s) for s in sides]).capitalize()
                     + ' races only'
                     + (f', so not {comma(barred)}.' if barred else '.'))
        else:
            takes = 'Anyone at all, whatever their race or reputation.'

        sub = esc(d.get('title', ''))
        if area:
            sub += f', over {esc(area["name"])}'
        else:
            sub += ', with no realm of their own on the map'

        main = (para(esc(d.get('description', '')))
                + lead('Grants', esc(d.get('bonus_text', '')))
                + lead('Takes', takes)
                )

        nums = [('Realm', esc(area['name']) if area else 'none on the map'),
                ('Its levels', f'{span[0]}\u2013{span[1]}' if span else None),
                ('Its zones', len(zs) or None)]
        for k, v in (d.get('bonus') or {}).items():
            nums.append((BONUS.get(k, k.replace('_', ' ').capitalize()),
                         f'{v:+g}%' if k.endswith('_pct') else f'{v:+g}'))
        aside = reg(nums)

        out.append(entry(
            esc(d.get('name', did)), sub, main, aside,
            kw(did, d.get('name'), d.get('title'), d.get('description'),
               d.get('bonus_text'), area.get('name'), takes),
            cid=f'god-{did}', realm=aid, medal=art(f'god_{did}.png')))

    hero = plate(art('zone_the_grove.jpg'),
                 'The Grove, where the nine are. No road reaches it.')
    named = sum(1 for d in DEITIES.values() if d.get('alignments'))
    lead_in = ('<div class="prose">' + para(
        f'{word(len(DEITIES), True)} elephant gods, and you choose one when '
        f'you make a character. {word(len(REALM_OF), True)} of them '
        'hold a realm on the map and the rest are '
        'older or stranger than that. What a god gives you is small and '
        'permanent: a little more health, a little more mana, a lighter '
        'death. What they ask is nothing, which should worry you.',
        f'{word(named, True)} of the {word(len(DEITIES))} will not take an '
        'evil race. The rest do not care what you are.') + '</div>')
    return 'gods', 'Gods', hero + lead_in + ''.join(out)



# ---------------------------------------------------------------- spells
BUFF_STAT = {'hp': 'health', 'ac': 'armour', 'dmg': 'damage',
             'haste': 'attack speed', 'hp_regen': 'health regeneration',
             'mana_regen': 'mana regeneration', 'str': 'strength',
             'sta': 'stamina', 'stamina': 'stamina', 'agi': 'agility',
             'wis': 'wisdom', 'int': 'intellect', 'mana': 'mana'}
TARGET_WORD = {'enemy': 'a foe', 'self': 'yourself', 'friendly': 'a friend',
               'group': 'your group', 'pet': 'your pet'}


def dur_words(sec):
    sec = float(sec)
    if sec >= 60 and sec % 60 == 0:
        m = int(sec // 60)
        return f'{m} minute' + ('s' if m > 1 else '')
    return f'{sec:g} seconds'


def spell_figures(sp):
    """The numbers the description leaves out. The written descriptions are
    already good and often carry the figures themselves, so anything the
    description has already said is dropped rather than repeated."""
    t = sp.get('type')
    per = sp.get('per_level')
    d = (sp.get('desc') or '').lower()
    said_plus = bool(re.search(r'[+\u2212-]\s?\d', d))
    said_time = 'second' in d or 'minute' in d
    said_pct = '%' in d
    out = []
    if sp.get('min') is not None:
        what = {'heal': 'healed', 'lifetap': 'drained'}.get(t, 'damage')
        f = f'{sp["min"]}–{sp["max"]} {what}'
        if per:
            f += f', +{per:g} a level'
        out.append(f)
    elif sp.get('tick'):
        f = f'{sp["tick"]} a tick for {sp["ticks"]} ticks'
        if per:
            f += f', +{per:g} a level'
        out.append(f)
    if sp.get('shot_mult') and not said_pct:
        n = int(sp.get('shots', 1))
        out.append((f'{word(n)} arrows at ' if n > 1 else 'an arrow at ')
                   + f'{sp["shot_mult"] * 100:.0f}% of a normal shot')
    if sp.get('slow') and not said_pct:
        out.append(f'{sp["slow"]}% slower')
    if sp.get('stun_chance') and not said_pct:
        out.append(f'{sp["stun_chance"] * 100:.0f}% to stun')
    if sp.get('splash_pct') and not said_pct:
        out.append(f'{sp["splash_pct"] * 100:.0f}% of it to anything nearby')
    st = sp.get('stats') or {}
    if st and not said_plus:
        out.append(comma([f'{v:+g} {BUFF_STAT.get(k, k)}' for k, v in st.items()]))
    if sp.get('duration') and not said_time:
        out.append(f'for {dur_words(sp["duration"])}')
    if sp.get('requires') and 'requires' not in d and 'needs' not in d:
        out.append(f'needs a {esc(sp["requires"])} in hand')
    for it, n in (sp.get('reagent') or {}).items():
        out.append(f'burns {n} {esc(item_name(it)).lower()}')
    return '; '.join(out)


def spell_rows(pairs, show_level=True):
    """pairs: [(level or None, spell id)] already in the order to print.

    These are rows of a grid rather than a real table. A table cell insists on
    behaving like a table cell however it is styled, and on a phone each row
    has to fold into a little block; a grid with the table roles kept gives
    the same columns on a wide screen and folds without a fight."""
    rows = []
    for lv, sid in pairs:
        sp = SPELLS[sid]
        fig = spell_figures(sp)
        mana = sp.get('mana') or 0
        cast = sp.get('cast_time') or 0
        recast = sp.get('recast') or 0
        who = TARGET_WORD.get(sp.get('target'), sp.get('target'))
        rows.append(
            '<div class="srow" role="row" data-k="'
            + kw(sid, sp.get('name'), sp.get('desc'), fig, sp.get('type'),
                 sp.get('skill'), who, *(sp.get('classes') or {}),
                 *[CLASSES[c]['name'] for c in (sp.get('classes') or {})
                   if c in CLASSES]) + '">'
            + (f'<span class="lv" role="cell">{lv}</span>' if show_level
               else '<span class="lv" role="cell"></span>')
            + '<span class="sp" role="cell"><span class="nm">'
            + esc(sp.get('name', sid)) + '</span>'
            + (f'<span class="d">{esc(sp.get("desc", ""))}</span>'
               if sp.get('desc') else '')
            + (f'<span class="fig">{fig}</span>' if fig else '')
            + '</span>'
            + '<span class="cost" role="cell">'
            + f'<b data-l="mana">{mana if mana else "—"}</b>'
            + f'<b data-l="cast">{f"{cast:g}s" if cast else "instant"}</b>'
            + f'<b data-l="again after">'
              f'{f"{recast:g}s" if recast else "—"}</b>'
            + '</span></div>')
    return ''.join(rows)


def spell_table(pairs, show_level=True):
    head = ('<div class="srow head" role="row">'
            + f'<span class="lv" role="columnheader">'
              f'{"Level" if show_level else ""}</span>'
            + '<span class="sp" role="columnheader">Spell</span>'
            + '<span class="cost" role="columnheader"><b>Mana</b>'
              '<b>Cast</b><b>Again after</b></span></div>')
    return (f'<div class="spells" role="table">{head}'
            f'{spell_rows(pairs, show_level)}</div>')


def sec_spells():
    groups = []
    for cid, c in CLASSES.items():
        pairs = CLASS_SPELLS.get(cid, [])
        if not pairs:
            continue
        abil = sum(1 for _, sid in pairs if SPELLS[sid].get('ability'))
        magic = len(pairs) - abil
        note = (f'{magic} spells and {abil} abilities' if magic and abil
                else f'{abil} abilities' if abil else f'{magic} spells')
        groups.append(f'<div class="grp" data-class="{cid}">'
                      f'<h2>{esc(c["name"])}<em>{note}</em></h2>'
                      f'{spell_table(sorted(pairs))}</div>')

    loose = sorted((SPELLS[sid].get('name', sid), sid) for sid in SPELLS
                   if not SPELLS[sid].get('classes'))
    if loose:
        groups.append(
            '<div class="grp"><h2>Cast by other things'
            f'<em>{len(loose)}, and none of them yours</em></h2>'
            '<p class="prose">Potions, poisons, traps and what the monsters '
            'throw at you. They are here because you will meet them.</p>'
            + spell_table([(None, sid) for _, sid in loose], show_level=False)
            + '</div>')

    lead_in = ('<div class="prose">' + para(
        f'Every spell and ability in the world, {len(SPELLS)} of them, under '
        'the class that learns it and the level it arrives. A spell shared by '
        'several classes appears under each, at that class&rsquo;s own level '
        '&mdash; a wizard has Root at 4 and a magician waits until 10.',
        'Mana, casting time and the wait before you can use it again are '
        'what the spell costs you. The line in italics is the part the '
        'description leaves out.') + '</div>')
    return 'spells', 'Spells', lead_in + ''.join(groups)



# ---------------------------------------------------------------- zones
# A zone's "kind" is the one word the layout uses for its character.
KIND_WORD = {
    'city': 'a city', 'outpost': 'an outpost', 'water': 'water country',
    'plain': 'open plain', 'field': 'farmed field', 'wood': 'woodland',
    'fog': 'fogbound', 'burn': 'burnt ground', 'terrace': 'terraced',
    'waste': 'wasteland', 'sanctuary': 'a sanctuary', 'wild': 'open wild',
}
# Landmarks worth naming. Props and signposts are scenery, not places.
LANDMARK_WORD = {
    'ruins': 'ruins', 'camp': 'a camp', 'outpost': 'an outpost',
    'watchtower': 'a watchtower', 'waystation': 'a waystation',
    'market': 'a market', 'obelisk': 'an obelisk', 'bridge': 'a bridge',
    'windmill': 'a windmill', 'vent': 'steam vents', 'cave': 'a cave',
    'sun_shrine': 'a sun shrine', 'stilt_city': 'a stilt city',
    'stilt_village': 'a stilt village', 'sail_tower': 'a sail tower',
    'orchard': 'an orchard', 'cabin': 'a cabin', 'house': 'houses',
    'spider_nest': 'a spider nest', 'lizard_camp': 'a lizard camp',
    'wall_ring': 'a ring wall', 'grove': 'a grove', 'pond': 'a pond',
    'sunken_ruins': 'sunken ruins', 'dawn_plaza': 'the dawn plaza',
    'hearth_plaza': 'the hearth plaza', 'crypt_room': 'a crypt',
    'tavern_room': 'a tavern',
}
COMPASS = ['north', 'east', 'south', 'west']
BESTIARY_READY = True


def mob_link(mid, title=True):
    n = esc(mob_name(mid, title))
    return f'<a href="#mob-{mid}">{n}</a>' if BESTIARY_READY else n


def zone_link(zid):
    n = esc(zone_name(zid))
    return f'<a href="#zone-{zid}">{n}</a>' if zid in ZONES else n


BORDERS = collections.defaultdict(list)    # zone -> [(edge, other zone)]
for _l in LAYOUT.get('links', []):
    BORDERS[_l['a']].append((_l.get('a_edge'), _l['b']))
    BORDERS[_l['b']].append((_l.get('b_edge'), _l['a']))

QUESTS_IN = collections.defaultdict(list)  # zone -> [quest id]
for _qid, _q in QUESTS.items():
    _z = NPC_ZONE.get(_q.get('giver'))
    if _z:
        QUESTS_IN[_z].append(_qid)


def mob_level(mid):
    lv = (MOBS.get(mid) or {}).get('level') or []
    if not lv:
        return ''
    return str(lv[0]) if lv[0] == lv[1] else f'{lv[0]}–{lv[1]}'


def sec_zones():
    out = []
    order = sorted(AREAS, key=lambda a: (area_span(a) or (99, 99))[0])
    for aid in order:
        area = AREAS[aid]
        zs = [z for z in ZONES.values() if z['area'] == aid]
        zs.sort(key=lambda z: (z['levels'][0], z['levels'][1], z['name']))
        god = DEITIES.get(area.get('deity') or '', {})
        span = area_span(aid)
        entries = []
        for z in zs:
            zid = z['id']
            zf = ZONE_FILES.get(zid, {})
            kind = KIND_WORD.get(z.get('kind'), z.get('kind', ''))
            lv = z['levels']
            lvs = str(lv[0]) if lv[0] == lv[1] else f'{lv[0]}–{lv[1]}'
            lvw = ('level ' if lv[0] == lv[1] else 'levels ') + lvs

            # which way out, and into what
            ways = []
            for c in COMPASS:
                for edge, other in BORDERS.get(zid, []):
                    if edge == c:
                        ways.append(f'{c} into {zone_link(other)}')
            if z.get('door_in'):
                ways.append(f'down from {zone_link(z["door_in"])}')
            if not ways:
                out_line = ('No road reaches it. You arrive by spell, or not '
                            'at all.' if z.get('reached') == 'teleport'
                            else 'Nothing borders it.')
            else:
                out_line = cap_first(comma(ways)) + '.'
                if z.get('reached') == 'teleport':
                    out_line = out_line[:-1] + ', though no road runs there.'

            lms = []
            for lm in (zf.get('landmarks') or []):
                w = LANDMARK_WORD.get((lm or {}).get('type')) if isinstance(lm, dict) else None
                if w and w not in lms:
                    lms.append(w)

            pool = ZONE_POOL.get(zid) or collections.Counter()
            top = pool.most_common(8)
            named = [m for m in pool if (MOBS.get(m) or {}).get('named')]

            people = [n for n in ZONE_NPCS.get(zid, [])
                      if (NPCS.get(n) or {}).get('title')]
            trades = collections.Counter()
            for n in ZONE_NPCS.get(zid, []):
                for role in ('merchant', 'banker', 'guildmaster',
                             'guild_registrar', 'binds'):
                    if (NPCS.get(n) or {}).get(role):
                        trades[role] += 1

            water = []
            if zf.get('lakes'):
                water.append(f'{word(len(zf["lakes"]))} lake'
                             + ('s' if len(zf['lakes']) > 1 else ''))
            if zf.get('rivers'):
                water.append('a river' if len(zf['rivers']) == 1 else 'rivers')
            if zf.get('fish'):
                water.append('fishing')
            if zf.get('rain'):
                water.append('rain')
            if zf.get('terraces'):
                water.append('cut terraces')

            main = (
                lead('Out of here', out_line)
                + (lead('On the ground', comma(lms) + '.') if lms else '')
                + (lead('Water and weather', cap_first(comma(water)) + '.')
                   if water else '')
                + (lead('Worth speaking to',
                        comma([f'{esc(NPCS[n]["name"])}, '
                               f'{esc(NPCS[n]["title"])}'
                               for n in people[:6]])
                        + ('.' if len(people) <= 6
                           else f', and {word(len(people) - 6)} more.'))
                   if people else '')
                + (lead('What lives here',
                        comma([f'{mob_link(m, False)} ({mob_level(m)})'
                               for m, _ in top])
                        + ('.' if len(pool) <= 8
                           else f', and {word(len(pool) - 8)} more.'))
                   if top else ''))

            nums = [('Levels' if lv[0] != lv[1] else 'Level', lvs),
                    ('Ground', f'{z["size"]} m across'),
                    ('Borders', len(BORDERS.get(zid, [])) or None),
                    ('Creatures', len(pool) or None),
                    ('Of them named', len(named) or None),
                    ('People', len(ZONE_NPCS.get(zid, [])) or None),
                    ('Tasks begin here', len(QUESTS_IN.get(zid, [])) or None),
                    ('Bindstone', 'yes' if zf.get('bindstone') else None),
                    ('Merchants', trades.get('merchant') or None),
                    ('Guildmasters', trades.get('guildmaster') or None),
                    ('Bank', 'yes' if trades.get('banker') else None)]

            entries.append(entry(
                esc(z['name']),
                cap_first(f'{kind}, {lvw}') if kind else cap_first(lvw),
                main, reg(nums),
                kw(zid, z['name'], area['name'], kind, lvs,
                   *[LANDMARK_WORD.get(l, '') for l in lms],
                   *[mob_name(m) for m, _ in top],
                   *[NPCS[n]['name'] for n in people]),
                cid=f'zone-{zid}', realm=aid))

        note = (f'levels {span[0]}–{span[1]}' if span else '')
        if god:
            note += f', under {esc(god["name"])}'
        entries_html = ''.join(entries)
        out.append(f'<div class="grp" data-realm="{aid}">'
                   f'<h2>{esc(area["name"])}<em>{note}</em></h2>'
                   f'{entries_html}</div>')

    lead_in = ('<div class="prose">' + para(
        f'{word(len(ZONES), True)} zones, laid out on a grid you can walk '
        'across without a loading screen asking your permission. Each one '
        'names the zones it borders and which way you leave to reach them; '
        'follow those far enough in any direction and you will run out of '
        'world.',
        'Level ranges are what the zone is built for, not a wall. Nothing '
        'stops you walking into the Boneyard at level 6 except what lives '
        'there.') + '</div>')
    return 'zones', 'Zones', lead_in + ''.join(out)



# ---------------------------------------------------------------- skills
def skill_cap_level(per, cap):
    """game_data.skill_cap: per x (level + 1), never past 100. So the level a
    class finally holds a skill at 100 is the number worth printing."""
    for lv in range(1, cap + 1):
        if per * (lv + 1) >= 100:
            return lv
    return None


def sec_skills():
    cap = CONFIG.get('max_level', 50)
    groups = (load(D('skills.json')).get('groups')
              or sorted({v.get('group', '') for v in SKILLS.values()}))
    flat = {k: v for k, v in SKILLS.items() if v.get('flat')}
    out = []
    for g in groups:
        rows = [(k, v) for k, v in SKILLS.items()
                if v.get('group') == g and not v.get('flat')]
        if not rows:
            continue
        head = ('<tr><th scope="col">Skill</th>'
                + ''.join(f'<th scope="col" class="num" data-class="{c}">'
                          f'<span>{esc(CLASSES[c]["name"])}</span></th>'
                          for c in CLASSES) + '</tr>')
        body = []
        for sid, sk in rows:
            caps = sk.get('caps') or {}
            frm = sk.get('from') or {}
            cells = []
            for c in CLASSES:
                per = caps.get(c)
                if not per:
                    cells.append('<td class="num none">&mdash;</td>')
                    continue
                lv = skill_cap_level(per, cap)
                cells.append(f'<td class="num" data-class="{c}">'
                             + (str(lv) if lv else
                                f'{per * (cap + 1)}%') + '</td>')
            by_lv = collections.defaultdict(list)
            for c, l in frm.items():
                by_lv[l].append(esc(CLASSES[c]['name'].lower()) + 's')
            late = comma([f'{comma(v)} not before level {l}'
                          for l, v in sorted(by_lv.items())], last='and')
            body.append(
                '<tr data-k="' + kw(sid, sk.get('name'), g, late,
                                    *[CLASSES[c]['name'] for c in caps])
                + f'"><th scope="row">{esc(sk.get("name", sid))}'
                + (f'<span class="late">{late}</span>' if late else '')
                + '</th>' + ''.join(cells) + '</tr>')
        out.append(f'<div class="grp"><h2>{esc(g)}'
                   f'<em>the level each class holds it at 100</em></h2>'
                   '<div class="mwrap"><table class="matrix">'
                   f'<thead>{head}</thead><tbody>{"".join(body)}</tbody>'
                   '</table></div></div>')

    if flat:
        out.append(
            '<div class="grp" data-k="' + kw('tradeskills',
                                             *[v['name'] for v in flat.values()])
            + f'"><h2>Tradeskills<em>open to everyone</em></h2>'
            '<p class="prose">'
            + cap_first(comma([esc(v['name']) for v in flat.values()]))
            + ' are not gated by class or level. Anyone can raise any of them '
              'to 100; the only thing in your way is practice and materials.'
              '</p></div>')

    lead_in = ('<div class="prose">' + para(
        'A skill goes up by using it, and how high it can go depends on your '
        'class and your level: the cap is a little higher every level until '
        'it reaches 100. The number below is the level at which a class '
        'finally holds that skill at 100 &mdash; lower is better, and a dash '
        'means the class never learns it at all.',
        'Nothing here is a choice you make. You raise a skill by swinging, '
        'casting, hiding or cooking, and the cap is what stops you running '
        'ahead of your level.') + '</div>')
    return 'skills', 'Skills', lead_in + ''.join(out)


# ---------------------------------------------------------------- quests
def coin_parts(copper):
    """The game's own purse: 1000 copper to the platinum, 100 to the gold,
    10 to the silver (World.coin_text). Returned in pieces so the caller can
    put them in one list with the experience rather than nesting two 'and's."""
    copper = int(copper or 0)
    if not copper:
        return []
    parts = [(copper // 1000, 'platinum'), ((copper // 100) % 10, 'gold'),
             ((copper // 10) % 10, 'silver'), (copper % 10, 'copper')]
    return [f'{n} {nm}' for n, nm in parts if n]


def faction_name(fid):
    return (FACTIONS.get(fid) or {}).get('name', fid.replace('_', ' ').title())


def plural(name, n):
    name = name.lower()
    if n == 1:
        return f'{"an" if name[0] in "aeiou" else "a"} {name}'
    return f'{n} {name}' if name.endswith('s') else f'{n} {name}s'


def sec_quests():
    by_zone = collections.defaultdict(list)
    for qid, q in QUESTS.items():
        by_zone[NPC_ZONE.get(q.get('giver'))].append(qid)

    def zone_sort(zid):
        z = ZONES.get(zid or '')
        return (z['levels'][0], z['name']) if z else (99, zid or 'zzz')

    out = []
    for zid in sorted(by_zone, key=zone_sort):
        qids = sorted(by_zone[zid], key=lambda q: QUESTS[q]['name'])
        z = ZONES.get(zid or '')
        area = AREAS.get(z['area'], {}) if z else {}
        title = zone_name(zid) if zid else 'Givers with no home'
        lv = z['levels'] if z else None
        note = (f'{esc(area.get("name", ""))}, levels {lv[0]}–{lv[1]}'
                if z and lv and lv[0] != lv[1] else
                esc(area.get('name', '')) if z else '')
        rows = []
        for qid in qids:
            q = QUESTS[qid]
            wants = comma([plural(item_name(i), n)
                           for i, n in (q.get('wants') or {}).items()])
            r = q.get('reward') or {}
            pays = []
            if r.get('xp'):
                pays.append(f'{r["xp"]} experience')
            pays += coin_parts(r.get('coin'))
            rep = [f'{esc(faction_name(k))} {v:+d}'
                   for k, v in (q.get('faction') or {}).items()]
            first = first_items(q)
            nxt = q.get('next')
            rows.append(
                '<div class="qrow" role="row" data-k="'
                + kw(qid, q.get('name'), npc_name(q.get('giver')),
                     zone_name(zid) if zid else '', q.get('start_keyword'),
                     *[item_name(i) for i in (q.get('wants') or {})],
                     *[item_name(i) for i in first])
                + '"><span class="qn" role="cell">'
                + f'<span class="nm" id="quest-{qid}">{esc(q["name"])}</span>'
                + f'<span class="d">From {esc(npc_name(q.get("giver")))}'
                + (f', in {zone_link(zid)}' if zid else '') + '.'
                + (f' Ask about &ldquo;{esc(q["start_keyword"])}&rdquo;.'
                   if q.get('start_keyword') else '') + '</span>'
                + (f'<span class="fig">Then: '
                   f'<a href="#quest-{nxt}">{esc(QUESTS[nxt]["name"])}</a>'
                   f'</span>' if nxt in QUESTS else '')
                + '</span>'
                + f'<span class="qw" role="cell">{esc(wants) if wants else "&mdash;"}'
                + ('<em>repeatable</em>' if q.get('repeatable') else '')
                + '</span>'
                + '<span class="qp" role="cell">'
                + (comma(pays) or '&mdash;')
                + (f'<em>first time: '
                   f'{comma([esc(item_name(i)) for i in first], last="or")}'
                   + (', by class' if len(first) > 1 else '') + '</em>'
                   if first else '')
                + (f'<em>{comma(rep)}</em>' if rep else '')
                + '</span></div>')
        ra = f' data-realm="{z["area"]}"' if z else ''
        out.append(f'<div class="grp"{ra}>'
                   f'<h2>{esc(title)}<em>{note}</em></h2>'
                   '<div class="qrow head" role="row">'
                   '<span role="columnheader">Task</span>'
                   '<span role="columnheader">Brings</span>'
                   '<span role="columnheader">Pays</span></div>'
                   + ''.join(rows) + '</div>')

    rep = sum(1 for q in QUESTS.values() if q.get('repeatable'))
    lead_in = ('<div class="prose">' + para(
        f'{word(len(QUESTS), True)} tasks, under the town or the wilderness '
        'where the person who wants them stands. Nobody has a mark over their '
        'head: you hail them, and you ask about the thing in brackets. The '
        'words to say are printed with each task.',
        f'{word(rep, True)} of them can be done again, for '
        f'{int(CONFIG.get("quest_repeat_xp", 0.5) * 100)}% of the experience '
        'the first time paid. The item a task hands over is given once.')
        + '</div>')
    return 'quests', 'Quests', lead_in + ''.join(out)



# ---------------------------------------------------------------- bestiary
# A named creature throws its own hp_base away: Mob.setup gives it the typical
# health of its level times config's named_health. These two mirror
# GameData.typical_hp / typical_dps so the guide prints the fight you get.
_TYP_HP, _TYP_DPS = [], []


def _build_typical():
    by_hp, by_dps = collections.defaultdict(list), collections.defaultdict(list)
    for d in MOBS.values():
        if d.get('named') or 'hp_base' not in d or 'level' not in d:
            continue
        for l in range(int(d['level'][0]), int(d['level'][1]) + 1):
            by_hp[l].append(float(d['hp_base']) + float(d['hp_per_level']) * (l - 1))
            by_dps[l].append((float(d['dmg_min']) + float(d['dmg_max']) + l // 2)
                             * 0.5 / float(d['attack_delay']))
    for src, out in ((by_hp, _TYP_HP), (by_dps, _TYP_DPS)):
        for l in range(71):
            vals = sorted(v for k in range(l - 1, l + 2) for v in src.get(k, []))
            out.append(vals[len(vals) // 2] if vals else -1.0)
        for l in range(1, 71):
            if out[l] < 0:
                out[l] = out[l - 1]


def typical_hp(level):
    if not _TYP_HP:
        _build_typical()
    return _TYP_HP[max(1, min(int(level), 70))]


def typical_dps(level):
    if not _TYP_DPS:
        _build_typical()
    return _TYP_DPS[max(1, min(int(level), 70))]


HOME_ZONE = {}      # mob -> the shallowest zone it is found in
for _mid, _zs in SPAWNS_IN.items():
    HOME_ZONE[_mid] = min(
        _zs, key=lambda z: ((ZONES.get(z) or {}).get('levels', [99])[0],
                            zone_name(z)))


def sec_bestiary():
    cfg_hp = float(CONFIG.get('named_health', 2.0))
    cfg_dmg = float(CONFIG.get('named_damage', 1.2))
    by_zone = collections.defaultdict(list)
    for mid in MOBS:
        by_zone[HOME_ZONE.get(mid)].append(mid)

    def zone_sort(zid):
        z = ZONES.get(zid or '')
        return (z['levels'][0], z['levels'][1], z['name']) if z else (99, 99, '')

    out = []
    for zid in sorted(by_zone, key=zone_sort):
        mids = sorted(by_zone[zid],
                      key=lambda m: (MOBS[m].get('level', [0])[0],
                                     MOBS[m].get('level', [0, 0])[1],
                                     mob_name(m)))
        z = ZONES.get(zid or '')
        area = AREAS.get(z['area'], {}) if z else {}
        rows = []
        for mid in mids:
            m = MOBS[mid]
            lv = m.get('level') or [1, 1]
            top = int(lv[1])
            named = bool(m.get('named'))
            tough = float(m.get('toughness', 1.0))

            if named:
                hp = int(typical_hp(top) * cfg_hp * tough)
                dps = typical_dps(top) * cfg_dmg * tough
                hits = None
            else:
                hp = hp_at(m, top)
                lo, hi = int(m['dmg_min']), int(m['dmg_max']) + top // 2
                hits = f'{lo}–{hi}'
                dps = (lo + hi) * 0.5 / float(m['attack_delay'])

            t = []
            if named:
                t.append(f'A named creature: {cfg_hp:g}× the health of an '
                         'ordinary monster its level, and it hits about '
                         f'{cfg_dmg:g}× as hard.')
            if m.get('min_players'):
                t.append(f'Not meant for fewer than '
                         f'{word(int(m["min_players"]))}.')
            if m.get('aggressive'):
                r = m.get('aggro_radius') or 0
                t.append(f'Comes for you from {r:g} m away.' if r
                         else 'Attacks on sight.')
            else:
                t.append('Leaves you alone unless you start it.')
            if m.get('social'):
                t.append('Brings its friends.')
            if m.get('flees'):
                t.append('Runs when it is badly hurt.')
            pr = m.get('proc') or {}
            if pr.get('spell') in SPELLS:
                t.append(f'Sometimes {esc(SPELLS[pr["spell"]]["name"])} '
                         f'({pr.get("chance", 0) * 100:.0f}% of its hits).')
            if m.get('weapon'):
                t.append(f'Carries {esc(item_name(m["weapon"]))}.')
            if m.get('xp_bonus'):
                t.append(f'Worth {m["xp_bonus"]:g}× the usual experience.')

            loot = [f'{esc(item_name(e["item"]))} '
                    f'({e.get("chance", 0) * 100:.0f}%)'
                    for e in (m.get('loot') or []) if e.get('item')]
            elsewhere = [zone_link(o) for o in sorted(SPAWNS_IN.get(mid, []))
                         if o != zid]

            nums = [('Level', str(lv[0]) if lv[0] == lv[1]
                     else f'{lv[0]}–{lv[1]}'),
                    ('Health', f'{hp:,}'),
                    ('Hits for', hits),
                    ('Damage a second', f'{dps:.0f}'),
                    ('Armour', m.get('ac')),
                    ('Swings every', f'{float(m["attack_delay"]):g}s'),
                    ('Faction', faction_name(m.get('faction', ''))),
                    ('Purse', comma(coin_parts((m.get('coin') or [0, 0])[1]))
                     or None)]

            pic = art(f'mob_{mid}.jpg')
            rows.append(
                '<div class="brow" data-k="'
                + kw(mid, mob_name(mid), m.get('faction'),
                     'named' if named else '', zone_name(zid) if zid else '',
                     *[item_name(e['item']) for e in (m.get('loot') or [])
                       if e.get('item')])
                + f'" id="mob-{mid}"><div class="bname">'
                + (f'<img src="{pic}" alt="" loading="lazy">' if pic else '')
                + f'<span class="nm">{esc(mob_name(mid))}</span>'
                + f'<span class="d">{" ".join(t)}</span>'
                + (f'<span class="fig">Drops {comma(loot)}.</span>'
                   if loot else '')
                + (f'<span class="fig">Also in {comma(elsewhere)}.</span>'
                   if elsewhere else '')
                + '</div><div class="bnum">' + reg(nums) + '</div></div>')

        if z:
            title = esc(z['name'])
            note = (f'{esc(area.get("name", ""))}, '
                    f'{len(mids)} of the {len(ZONE_POOL.get(zid, {}))} that '
                    'walk here')
        else:
            title = 'Summoned, and other things'
            note = f'{len(mids)} that no zone spawns on its own'
        hero = plate(art(f'zone_{zid}.jpg') if zid else None, '')
        ra = f' data-realm="{z["area"]}"' if z else ''
        out.append(f'<div class="grp"{ra}><h2>{title}<em>{note}</em></h2>'
                   f'{hero}{"".join(rows)}</div>')

    named_n = sum(1 for m in MOBS.values() if m.get('named'))
    drawn = sum(1 for mid in MOBS if art(f'mob_{mid}.jpg'))
    lead_in = ('<div class="prose">' + para(
        f'Every creature in the world, {len(MOBS)} of them, filed under the '
        'shallowest zone it is found in and listed by level. Where one walks '
        'in more than one place, its entry says so.',
        f'{word(named_n, True)} of them are named: a named creature throws '
        'away its own health and takes the typical health of its level '
        f'{cfg_hp:g} times over, so the numbers here are what you will '
        f'actually fight. {word(drawn, True)} have had their portrait taken '
        'so far.') + '</div>')
    return 'bestiary', 'Bestiary', lead_in + ''.join(out)



# ---------------------------------------------------------------- items
SOLD_BY = collections.defaultdict(set)      # item -> {npc id}
for _nid, _n in NPCS.items():
    for _it in ((_n.get('merchant') or {}).get('sells') or []):
        SOLD_BY[_it].add(_nid)

ITEM_STAT = [('str', 'strength'), ('sta', 'stamina'), ('agi', 'agility'),
             ('wis', 'wisdom'), ('int', 'intellect'), ('hp', 'health'),
             ('mana', 'mana'), ('hp_regen', 'health regeneration'),
             ('haste', '% attack speed')]
SLOT_GROUP = [
    ('primary', 'In hand'), ('secondary', 'Off hand'),
    ('range', 'Bows and slings'), ('head', 'Head'), ('chest', 'Chest'),
    ('arms', 'Arms'), ('hands', 'Hands'), ('legs', 'Legs'), ('feet', 'Feet'),
    ('waist', 'Waist'), ('neck', 'Neck'), ('ring', 'Rings'),
]


def item_group(iid, it):
    slot = it.get('slot')
    if slot:
        return slot
    if it.get('bag'):
        return 'bag'
    if it.get('ammo_type'):
        return 'ammo'
    if it.get('use'):
        return 'use'
    if it.get('recipes') or it.get('combine'):
        return 'craft'
    if it.get('stack'):
        return 'stock'
    return 'odd'


EXTRA_GROUP = [('bag', 'Bags'), ('ammo', 'Arrows, bolts and stones'),
               ('use', 'Things you use'), ('craft', 'Tools of a trade'),
               ('stock', 'Trade goods and components'),
               ('odd', 'Oddments')]


def _shapes_drawn():
    return any(art(f'model_{i.get("model") or i.get("projectile")}.png')
               for i in ITEMS.values() if i.get('model') or i.get('projectile'))


def sec_items():
    groups = collections.defaultdict(list)
    for iid, it in ITEMS.items():
        groups[item_group(iid, it)].append(iid)

    out = []
    for gid, label in SLOT_GROUP + EXTRA_GROUP:
        iids = groups.get(gid) or []
        if not iids:
            continue
        # ordinary gear first, in the order you would meet it; the handful
        # of relics that scale with you have no level of their own, so they
        # go at the end rather than pretending to be starter kit.
        iids.sort(key=lambda i: (1 if ITEMS[i].get('level_scaled') else 0,
                                 ITEMS[i].get('rec_level') or 0,
                                 ITEMS[i].get('value') or 0, item_name(i)))
        rows = []
        for iid in iids:
            it = ITEMS[iid]
            lines = []

            # what it does in a fight, or on your back
            what = ('a shield' if it.get('shield')
                    else f'a {esc(SKILLS[it["skill"]]["name"])} weapon'
                    if it.get('skill') in SKILLS else '')
            nums = []
            if it.get('dmg') and it.get('delay'):
                d, dl = float(it['dmg']), float(it['delay'])
                nums.append(f'{it["dmg"]:g} damage every {dl:g} seconds, '
                            f'about {d / dl:.1f} a second')
            elif it.get('dmg'):
                nums.append(f'{it["dmg"]:g} damage a shot')
            if it.get('ac'):
                nums.append(f'{it["ac"]} armour')
            if what and nums:
                lines.append(f'{cap_first(what)}: {comma(nums)}.')
            elif what or nums:
                lines.append(cap_first(what or comma(nums)) + '.')

            bonus = [f'+{it[k]:g} {w}' if k != 'haste'
                     else f'+{it[k]:g}% attack speed'
                     for k, w in ITEM_STAT if it.get(k)]
            if bonus:
                lines.append(cap_first(comma(bonus)) + '.')

            if it.get('level_scaled'):
                lines.append('Grows stronger as you do.')
            pr = it.get('proc') or {}
            if pr.get('spell') in SPELLS:
                lines.append(f'Sometimes {esc(SPELLS[pr["spell"]]["name"])} '
                             f'({pr.get("chance", 0) * 100:.0f}% of hits).')
            us = it.get('use') or {}
            if us.get('spell') in SPELLS:
                lines.append(f'Casts {esc(SPELLS[us["spell"]]["name"])} when '
                             'used'
                             + (f', again after {dur_words(us["recast"])}'
                                if us.get('recast') else '') + '.')

            hold = []
            if it.get('rec_level'):
                hold.append(f'level {it["rec_level"]}')
            cls = it.get('classes') or []
            if cls:
                hold.append(comma([esc(CLASSES[c]['name'].lower()) + 's'
                                   for c in cls if c in CLASSES]) + ' only')
            if hold:
                lines.append('Wants ' + comma(hold) + '.')

            keep = []
            if it.get('no_drop'):
                keep.append('never leaves you')
            if it.get('lore'):
                keep.append('only one at a time')
            if it.get('unique'):
                keep.append('unique')
            if it.get('stack'):
                keep.append(f'stacks to {it["stack"]}')
            if it.get('bag'):
                keep.append(f'holds {it["bag"]}')
            if it.get('weight_reduction'):
                keep.append(f'lightens what it holds by '
                            f'{it["weight_reduction"] * 100:.0f}%')
            worth = comma(coin_parts(it.get('value')))
            if worth:
                keep.append(f'worth {worth}')
            if keep:
                lines.append(cap_first(comma(keep)) + '.')

            # where it comes from
            src = []
            mobs = sorted(DROPS_FROM.get(iid, []))
            qs = sorted(QUEST_WANTS.get(iid, set()) | QUEST_GIVES.get(iid, set()))
            if mobs:
                src.append('Dropped by ' + comma(
                    [mob_link(m, False) for m in mobs[:6]])
                    + (f' and {word(len(mobs) - 6)} more' if len(mobs) > 6
                       else ''))
            if qs:
                give = [q for q in qs if q in QUEST_GIVES.get(iid, set())]
                want = [q for q in qs if q in QUEST_WANTS.get(iid, set())]
                if give:
                    src.append('given for ' + comma(
                        [f'<a href="#quest-{q}">{esc(QUESTS[q]["name"])}</a>'
                         for q in give[:4]]))
                if want:
                    src.append('wanted for ' + comma(
                        [f'<a href="#quest-{q}">{esc(QUESTS[q]["name"])}</a>'
                         for q in want[:4]]))
            shops = sorted(SOLD_BY.get(iid, []))
            if shops:
                src.append('sold by ' + comma(
                    [f'{esc(npc_name(n))}'
                     + (f' in {zone_link(NPC_ZONE[n])}' if n in NPC_ZONE else '')
                     for n in shops[:3]]))
            if it.get('from'):
                src.append(f'carried out of {esc(it["from"])}')

            shape = it.get('model') or it.get('projectile')
            pic = art(f'model_{shape}.png') if shape else None
            rows.append(
                '<div class="irow" data-k="'
                + kw(iid, it.get('name'), label, it.get('skill'),
                     *[c for c in cls],
                     *[mob_name(m) for m in mobs[:6]])
                + f'" id="item-{iid}"><div class="iname">'
                + (f'<img class="shape" src="{pic}" alt="" loading="lazy">'
                   if pic else '')
                + f'<span class="nm">{esc(it.get("name", iid))}</span>'
                + (f'<span class="lore">{esc(it["desc"])}</span>'
                   if it.get('desc') else '')
                + (f'<span class="fig">{cap_first(comma(src))}.</span>'
                   if src else '')
                + '</div><div class="istat">'
                + ''.join(f'<span>{l}</span>' for l in lines)
                + '</div></div>')
        out.append(f'<div class="grp"><h2>{esc(label)}'
                   f'<em>{len(iids)}</em></h2>{"".join(rows)}</div>')

    nd = sum(1 for i in ITEMS.values() if i.get('no_drop'))
    lead_in = ('<div class="prose">' + para(
        f'Everything you can pick up, {len(ITEMS)} of them, under the place '
        'it goes or the reason you carry it. Where an item comes from is '
        'printed with it: what drops it, who asks for it, and which shop '
        'keeps one.',
        f'{word(nd, True)} are marked never leaves you: once it is yours it '
        'cannot be traded, sold or left on a corpse for someone else.',
        ('Where a weapon has a picture, that is the model the game puts in '
         'your hand &mdash; rendered from the same file the game loads. '
         'Weapons share their models, so every arming sword in the world '
         'looks like the one beside Rusty Short Sword, because in the game '
         'it does.') if _shapes_drawn() else '')
        + '</div>')
    return 'items', 'Items', lead_in + ''.join(out)


SECTIONS = [sec_world, sec_start, sec_races, sec_classes,
            sec_gods, sec_spells, sec_zones, sec_skills,
            sec_quests, sec_bestiary, sec_items]

# The order the guide reads in, whatever order the sections got written in.
ORDER = ['world', 'start', 'races', 'classes', 'gods', 'spells', 'skills',
         'quests', 'items', 'bestiary', 'zones']

PENDING = [
]

COUNTS = {'world': len(AREAS), 'races': len(RACES), 'classes': len(CLASSES),
          'gods': len(DEITIES), 'spells': len(SPELLS), 'skills': len(SKILLS),
          'quests': len(QUESTS), 'items': len(ITEMS), 'bestiary': len(MOBS),
          'zones': len(ZONES)}


def build():
    import wiki_theme
    os.makedirs(os.path.join(OUT, 'art'), exist_ok=True)
    src = os.path.join(ROOT, 'docs', 'world-atlas.png')
    dst = os.path.join(OUT, 'art', 'world-atlas.png')
    if os.path.exists(src) and (not os.path.exists(dst)
                                or os.path.getmtime(src) > os.path.getmtime(dst)):
        import shutil
        shutil.copy2(src, dst)

    built = [f() for f in SECTIONS]
    for sid, label, what in PENDING:
        n = COUNTS.get(sid)
        built.append((sid, label,
                      f'<div class="soon" data-k="{kw(label, what)}">'
                      f'<h3>{esc(label)}</h3>'
                      f'<p>Not written yet: {esc(what)}. All {n} of them are '
                      'already in the game data, waiting for this section to '
                      'read them the way every other page here does.</p></div>'))

    built.sort(key=lambda b: ORDER.index(b[0]) if b[0] in ORDER else 99)
    nav, body = [], []
    for sid, label, htm in built:
        n = COUNTS.get(sid)
        cnt = f'<span class="n" data-total="{n}">{n}</span>' if n else ''
        nav.append(f'<li><button data-sec="{sid}">'
                   f'<span>{esc(label)}</span>{cnt}</button></li>')
        title = '' if sid == 'world' else f'<h2 class="sec-title">{esc(label)}</h2>'
        body.append(f'<section class="sec" id="{sid}" aria-label="{esc(label)}"'
                    f' hidden>{title}<p class="hitnote"></p>{htm}</section>')

    doc = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Emberfall</title>'
        '<meta name="description" content="A player\'s guide to Emberfall, '
        'generated from the game\'s own data.">'
        f'<style>{wiki_theme.build()}{CSS}</style></head><body>'
        '<a class="skip" href="#main">Skip to the guide</a>'
        '<header class="masthead"><div class="mh">'
        '<p class="wordmark">Emberfall</p>'
        '<p class="mh-sub">a guide to the world, written by the world</p>'
        '<form class="find" role="search">'
        '<label for="q">Search the guide</label>'
        '<input id="q" type="search" autocomplete="off" '
        'placeholder="a race, a realm, a creature&hellip;"></form>'
        '</div></header>'
        '<div class="frame">'
        '<nav class="index" aria-label="Guide sections"><ol>'
        + ''.join(nav) + '</ol></nav>'
        '<main id="main">' + ''.join(body) + '</main>'
        '</div>'
        '<footer><p>Every word, number and colour on this page is read out of '
        'Emberfall&rsquo;s own data by <code>tools/wiki.py</code> when the page '
        'is built. Nothing here is typed by hand, so the guide cannot drift '
        'from the game.</p>'
        '<p>Lettered in TeX Gyre Pagella and Chorus, the two faces the world '
        'atlas is drawn with, on the atlas&rsquo;s own paper and ink.</p>'
        '</footer>'
        f'<script>{JS}</script></body></html>')

    p = os.path.join(OUT, 'index.html')
    open(p, 'w').write(doc)
    return p, len(doc)



def audit():
    """What the game knows that the guide does not.

    The generator cannot drift on anything it reads. It can drift badly on
    anything it does not: when the Pathcallers arrived, every number on the
    page stayed right while one sentence of hand-written prose went on
    insisting there was no fast travel. So after each build, look at the
    settings, the roles and the data files the game has grown and say which
    ones this file has never heard of. It is not a test; it is a list of
    things to go and read."""
    src = open(os.path.abspath(__file__)).read()
    missed = []

    unseen = [k for k in CONFIG if f"'{k}'" not in src and f'"{k}"' not in src]
    if unseen:
        missed.append(('settings in config.json', unseen))

    roles = set()
    for d in NPCS.values():
        roles.update(k for k, v in d.items() if v is True)
    unseen = sorted(r for r in roles if f"'{r}'" not in src)
    if unseen:
        missed.append(('things an NPC can be', unseen))

    keys = collections.Counter()
    for d in ITEMS.values():
        keys.update(d.keys())
    unseen = sorted(k for k, n in keys.items() if n >= 5 and f"'{k}'" not in src)
    if unseen:
        missed.append(('item fields on five or more items', unseen))

    keys = collections.Counter()
    for d in MOBS.values():
        keys.update(d.keys())
    unseen = sorted(k for k, n in keys.items() if n >= 5 and f"'{k}'" not in src)
    if unseen:
        missed.append(('creature fields on five or more creatures', unseen))

    known = {os.path.basename(f) for f in glob.glob(D('*.json'))}
    unseen = sorted(f for f in known if f[:-5] not in src)
    if unseen:
        missed.append(('files in data/ nothing here opens', unseen))

    if not missed:
        print('the guide reads everything the game currently has')
        return
    print('\nthe guide has not heard of:')
    for what, items in missed:
        print(f'  {what}:')
        print('    ' + ', '.join(items))



if __name__ == '__main__':
    path, n = build()
    print(f'{path}  ({n / 1024:.0f} KB)')
    audit()
