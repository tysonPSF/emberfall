# Emberfall — the world layout

37 zones, 6 areas, levels 1–50, a city in every area. **This is the layout
table only** — no zone files are written yet. Passes and zone lines are derived
from the grid by `tools/world_layout.py`, never typed.

## How to read it

A zone is a square `size` metres across ringed by mountains, with up to four
`passes` — gaps at its north, south, east and west edges — each carrying a
`zone_line` to the neighbour. So the world is a grid and a border is a door in
a shared wall. `cell` is `[gx, gy]` with **gy rising north**; the engine's +z is
south, so `gy` negates into `z`.

**A zone with `cell: null` is not on the grid at all.** It has no neighbours, so
it gets no passes and no zone lines, and nothing can walk to it. The Grove is
the only one today.

## The areas

| Area | Deity | City | Zones | Levels | Where |
| --- | --- | --- | --- | --- | --- |
| **The Emberlands** | — *the start* | Emberhold | 6 | 1–15 | south, home |
| **The Dawnstair** | light | Lanternhold | 7 | 1–24 | east, climbing (Dewstep, its beginner ground, 1–10) |
| **The Long Monsoon** | water | Rainhold | 6 | 20–30 | west, and rising water |
| **The Ashfall** | fire | Forgehold | 6 | 26–38 | due north of home |
| **The Standing Sky** | wind | Galehold | 6 | 32–44 | north-west, high and open |
| **The Boneyard** | dark | Barrowhold | 6 | 40–50 | the top of the world |

## A city ends in -hold

Emberhold was already named that way, so the rule is taken rather than
invented — and it means a player can tell a city from a wild zone by its name
alone, on the map, in the compass and in the zone line prompt. The Dawnstair's
`Dawnhold` was an outpost, not a city, and is renamed **Dawnwatch** so the
suffix keeps meaning one thing. `world_layout.py` enforces it.

**A city is safe ground**, so it is exempt from the level-gap check. Walking
into a town twenty levels above you is not a death, it is an errand: guards,
merchants, a bind point and a long run home.

| City | Area | Cell | Why there |
| --- | --- | --- | --- |
| Emberhold | The Emberlands | `[0, 0]` | already built |
| Lanternhold | The Dawnstair | `[3, 2]` | beside Sunward Steps, the zone you arrive in |
| Rainhold | The Long Monsoon | `[-1, 1]` | the cell the Grove left; touches Greenmoor too |
| Forgehold | The Ashfall | `[1, 5]` | swapped forward with Smokewood — see below |
| Galehold | The Standing Sky | `[-2, 5]` | swapped forward with Stonesail — beside Tidemouth |
| Barrowhold | The Boneyard | `[2, 7]` | touches The Unlit and Timiraj's Table, so two ways in |

### Rainhold is the interesting one

It took the cell the Grove vacated, which touches **Greenmoor** as well as The
Weeping Throat. So a level 5 character can run to the water city and live —
the oldest rite of passage this genre has — and the Monsoon gains a second
entrance from the start area without a second wilderness border.

### Forgehold came forward

The first layout put Forgehold at `[3, 5]`, past Agnavar's Hearth: every cell
touching Cinderpass, The Burn and Blackglass was taken, so the fire city sat
five zones deep. When it was built it **swapped cells with Smokewood**. At
`[1, 5]` it touches Blackglass, Dawnwatch, Agnavar's Hearth and the Boneyard's
Ivory Field, so it's a hub rather than a dead end, and a city is safe ground,
so the level gaps across its gates don't count. Smokewood (33–37) went to
`[3, 5]`, past the Hearth, where it touches only the Hearth.

### Galehold came forward too

Like Forgehold, Galehold first sat past its realm's zones, west of Stonesail,
three zones up to 41 from anything built. It **swapped cells with Stonesail**:
at `[-2, 5]` it borders Tidemouth, The Long Grass and Vayuketh's Step, and
Stonesail (37–41) lies past it at `[-3, 5]`.

## The zones

| Zone | Area | Levels | Size | Cell | Kind |
| --- | --- | --- | --- | --- | --- |
| Emberhold **(built)** | The Emberlands | city | 224 m | `[0, 0]` | city |
| Greenmoor **(built)** | The Emberlands | 1–7 | 384 m | `[0, 1]` | field |
| The Grove | The Emberlands | sanctuary | 256 m | *none — teleport* | sanctuary |
| Harrowfield **(built)** | The Emberlands | 3–9 | 384 m | `[1, 1]` | field |
| Thornwood Vale **(built)** | The Emberlands | 6–14 | 512 m | `[0, 2]` | wood |
| Hollowmere **(built)** | The Emberlands | 10–15 | 448 m | `[1, 2]` | water |
| Lanternhold **(built)** | The Dawnstair | city | 224 m | `[3, 2]` | city |
| Dewstep **(built)** | The Dawnstair | 1–10 | 384 m | `[3, 1]` | field |
| Sunward Steps **(built)** | The Dawnstair | 14–18 | 448 m | `[2, 2]` | terrace |
| The Bleach **(built)** | The Dawnstair | 16–21 | 512 m | `[2, 3]` | waste |
| High Terrace **(built)** | The Dawnstair | 18–23 | 512 m | `[1, 3]` | terrace |
| Mirror Flats **(built)** | The Dawnstair | 20–24 | 512 m | `[2, 4]` | waste |
| Dawnwatch **(built)** | The Dawnstair | 22–24 | 448 m | `[1, 4]` | outpost |
| Rainhold **(built)** | The Long Monsoon | city | 224 m | `[-1, 1]` | city |
| The Weeping Throat **(built)** | The Long Monsoon | 20–24 | 448 m | `[-1, 2]` | water |
| Reedmere **(built)** | The Long Monsoon | 22–26 | 512 m | `[-2, 2]` | water |
| The Silted Reach **(built)** | The Long Monsoon | 24–28 | 512 m | `[-2, 3]` | water |
| Drownfast **(built)** | The Long Monsoon | 26–30 | 512 m | `[-1, 3]` | water |
| Tidemouth **(built)** | The Long Monsoon | 28–30 | 448 m | `[-2, 4]` | outpost |
| Forgehold **(built)** | The Ashfall | city | 224 m | `[1, 5]` | city |
| Cinderpass **(built)** | The Ashfall | 26–30 | 448 m | `[0, 3]` | burn |
| The Burn **(built)** | The Ashfall | 29–33 | 512 m | `[0, 4]` | burn |
| Blackglass **(built)** | The Ashfall | 31–35 | 512 m | `[0, 5]` | burn |
| Smokewood **(built)** | The Ashfall | 33–37 | 512 m | `[3, 5]` | wood |
| Agnavar's Hearth **(built)** | The Ashfall | 35–38 | 512 m | `[2, 5]` | burn |
| Galehold **(built)** | The Standing Sky | city | 224 m | `[-2, 5]` | city |
| Windbreak **(built)** | The Standing Sky | 32–36 | 448 m | `[-1, 4]` | plain |
| The Long Grass **(built)** | The Standing Sky | 34–38 | 512 m | `[-1, 5]` | plain |
| Stonesail **(built)** | The Standing Sky | 37–41 | 512 m | `[-3, 5]` | plain |
| Hollow Air **(built)** | The Standing Sky | 39–43 | 512 m | `[-1, 6]` | plain |
| Vayuketh's Step **(built)** | The Standing Sky | 42–44 | 448 m | `[-2, 6]` | outpost |
| Barrowhold **(built)** | The Boneyard | city | 224 m | `[2, 7]` | city |
| Fogfall **(built)** | The Boneyard | 40–43 | 512 m | `[0, 6]` | fog |
| The Ivory Field **(built)** | The Boneyard | 42–45 | 512 m | `[1, 6]` | fog |
| The Unlit **(built)** | The Boneyard | 44–47 | 512 m | `[2, 6]` | fog |
| Lastwalk **(built)** | The Boneyard | 46–49 | 512 m | `[0, 7]` | fog |
| Timiraj's Table **(built)** | The Boneyard | 48–50 | 512 m | `[1, 7]` | fog |

## Dewstep, added later

The first layout gave only Emberhold (Greenmoor) and Rainhold (Greenmoor, next
door) a beginner field, so a character whose home is Lanternhold (high elves)
had nowhere at their own level. Dewstep, 1–10, takes the cell **south** of
Lanternhold, `[3, 1]`: the bottom of the Dawnstair, terraced tea gardens under
the city walls. It touches **only** Lanternhold, so no wilderness border drops a
newcomer anywhere deep; they leave through the city toward Sunward Steps. The
Dawnstair is the one area with seven zones, and `world_layout.py` allows it.

## The Grove is off the grid

It holds no cell, so it has no edges, no passes and no borders — **nothing can
walk to it**, by construction rather than by a rule somewhere. It is reached by
teleport, and `world_layout.py` asserts the isolation rather than tolerating it:
every other zone must be walkable from Emberhold, *and* the Grove must not be.

## Where the areas touch

A web, not a hub: six of the nine area pairings are between two deity areas, so
most places have more than one way in.

| From | Edge | To |
| --- | --- | --- |
| Greenmoor (The Emberlands) | west | Rainhold (The Long Monsoon) |
| Thornwood Vale (The Emberlands) | west | The Weeping Throat (The Long Monsoon) |
| Hollowmere (The Emberlands) | east | Sunward Steps (The Dawnstair) |
| High Terrace (The Dawnstair) | south | Hollowmere (The Emberlands) |
| Dawnwatch (The Dawnstair) | north | Forgehold (The Ashfall) |
| Dawnwatch (The Dawnstair) | west | The Burn (The Ashfall) |
| Drownfast (The Long Monsoon) | north | Windbreak (The Standing Sky) |
| Tidemouth (The Long Monsoon) | east | Windbreak (The Standing Sky) |
| Cinderpass (The Ashfall) | south | Thornwood Vale (The Emberlands) |
| Cinderpass (The Ashfall) | east | High Terrace (The Dawnstair) |
| Cinderpass (The Ashfall) | west | Drownfast (The Long Monsoon) |
| The Burn (The Ashfall) | west | Windbreak (The Standing Sky) |
| Blackglass (The Ashfall) | north | Fogfall (The Boneyard) |
| Blackglass (The Ashfall) | west | The Long Grass (The Standing Sky) |
| Agnavar's Hearth (The Ashfall) | north | The Unlit (The Boneyard) |
| Agnavar's Hearth (The Ashfall) | south | Mirror Flats (The Dawnstair) |
| Galehold (The Standing Sky) | south | Tidemouth (The Long Monsoon) |
| Fogfall (The Boneyard) | west | Hollow Air (The Standing Sky) |
| The Ivory Field (The Boneyard) | south | Forgehold (The Ashfall) |

## Thornwood's three reserved passes

`CLAUDE.md` says the north, east and west passes are `rockslide` landmarks and
*"a future zone replaces one with a zone line"*. All three are used, and each
opens onto a different area:

- **north** → Cinderpass, The Ashfall (26–30) — a door you are not ready for
- **east** → Hollowmere, The Emberlands (10–15) — the graded way on
- **west** → The Weeping Throat, The Long Monsoon (20–24)

## Not decided here

- Terrain, spawns, landmarks, roads, rivers or music for any new zone.
- What is *in* each city: which classes train there, who binds, which merchants.
- Whether any city is hostile to some players — faction is untouched here.
- Which zones carry dungeons.
- How the Grove is reached — spell, item, or a bind point of its own.
