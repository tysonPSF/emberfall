# Building a zone from the world layout

Read this before creating or connecting any zone. The layout it implements is
`docs/world-layout.json` (human version: `docs/world-layout.md`, picture:
`docs/world-map.png`).

**The layout is the source of truth for where a zone is and who it borders.**
It is not the source of truth for what is *in* a zone — terrain, spawns,
landmarks, roads and music are authored per zone as usual.

## What the layout gives you

36 zones in 6 areas, levels 1–50. Per zone: `id`, `name`, `area`, `levels`,
`size`, `cell`, `kind`, plus `existing` and `reached`. And a `links` array: one
entry per border, already reciprocal.

```json
{ "a": "thornwood", "a_edge": "north",
  "b": "cinderpass", "b_edge": "south", "cross_area": true }
```

`cell` is `[gx, gy]` with **gy rising north**. The engine's **+z is south**, so
`gy` negates into `z`. A zone with `cell: null` is off the grid entirely — no
neighbours, no passes, no zone lines. The Grove is the only one, and it is
reached by teleport.

## The rule that matters most

**A border is four things that must agree, and none of them may be typed by
hand.** Derive all four from the layout:

| | on zone A | on zone B |
|---|---|---|
| the gap in the mountains | `passes` entry on A's edge | `passes` entry on B's opposite edge |
| the trigger | `zone_lines` entry pointing at B | `zone_lines` entry pointing at A |

Miss one and you get a one-way door, a trigger with a mountain behind it, or a
player materialising inside rock. These are the failures the layout exists to
prevent, so generate them from `links` and never author them per zone.

## Deriving a border

Let `half = size / 2`. Edges: **north is `z = -half`, south is `z = +half`,
east is `x = +half`, west is `x = -half`.**

For a border between A (edge `e`) and B (edge `opposite(e)`), with a chosen
cross-axis offset `k` (use `0` unless there is a reason):

1. **Pass on each side.** Half-width `9`, which makes an 18 m gap.
   - A north → `[k, -halfA, 9]` · A south → `[k, +halfA, 9]`
   - A east → `[+halfA, k, 9]` · A west → `[-halfA, k, 9]`
   - B takes the same `k` on its opposite edge. **`k` must be inside both
     zones' half-extent** — they are different sizes, and a pass at `k = 200`
     on a 512 m zone has no facing wall on a 448 m neighbour.

2. **Trigger box, 11 m inside the edge, exactly as wide as the pass.**
   - north/south → `pos: [k, ∓(half - 11)]`, `size: [18, 8]`
   - east/west → `pos: [±(half - 11), k]`, `size: [8, 18]`

   (The 18 is `2 × 9`, the pass width. The east/west orientation is derived —
   no shipped zone line uses one yet, so verify it in game the first time.)

3. **`arrive` is in the TARGET zone, 25 m inside ITS matching edge.**
   Coming through A's north edge, you appear just inside B's south edge:
   `arrive: [k, +halfB - 25]`.

4. **`arrive_face` is a further ~40 m inward along the same axis**, so the
   player is looking into the zone rather than back at the wall.

### Worked example, against shipped data

Greenmoor (384, `half` 192) north → Thornwood Vale (512, `half` 256):

```jsonc
// greenmoor.json
"passes":     [[0, -192, 9]],
"zone_lines": [{ "pos": [0, -181], "size": [18, 8], "to": "thornwood",
                 "arrive": [0, 228], "arrive_face": [0, 190] }]
// thornwood.json
"passes":     [[0, 256, 9]],
"zone_lines": [{ "pos": [0, 245], "size": [18, 8], "to": "greenmoor",
                 "arrive": [0, -168], "arrive_face": [0, -100] }]
```

### Measured off the three shipped zones

Every constant above is read off what already ships, not invented:

| | Emberhold (city) | Greenmoor | Thornwood |
|---|---|---|---|
| `size` / `half` | 224 / 112 | 384 / 192 | 512 / 256 |
| pass half-width | 9 | 9 | 9 |
| trigger `size` | `[18, 8]` | `[18, 8]` | `[18, 8]` |
| trigger inset | **15** | 11 | 11 |
| arrive depth *into* it | **66** | 24 | 28, 24 |

**Cities are the exception, and deliberately so.** You arrive at Emberhold 66 m
in — at a plaza, not against the wall — and its trigger sits 15 m inside rather
than 11. Do the same for the five new cities: bring the player to somewhere
that reads as a gate, not to the mountain face. For wilderness, 11 in and 25
deep is the shipped pattern.

Thornwood's east and west passes sit at `k = -20` and `k = +40`. Its north and
south are at `k = 0`, as are Greenmoor's and Emberhold's.

## Thornwood's three rockslides

`CLAUDE.md`: the north, east and west passes are `"rockslide"` landmarks and
*"a future zone replaces one with a zone line"*. The passes already exist. When
you build the neighbour:

1. **Remove the `rockslide` landmark** for that edge from `thornwood.json`.
2. Add the `zone_lines` entry. The `passes` entry is already there — do not add
   a second.

| Thornwood edge | opens onto |
|---|---|
| north | Cinderpass, The Ashfall (26–30) |
| east | Hollowmere, The Emberlands (10–15) **(built: the rockslide is gone, zone lines both sides)** |

Hollowmere's south pass opens onto Harrowfield (built), and Greenmoor gained an east pass to Harrowfield; Hollowmere's east and north are rockslides.
| west | The Weeping Throat, The Long Monsoon (20–24) |

The existing east and west passes sit at `k = -20` and `k = +40`, not 0. Use
those same offsets on the neighbour — and check they fall inside the
neighbour's half-extent, since Hollowmere (448) and The Weeping Throat (448)
are smaller than Thornwood (512).

## Cities

Six of them, and **a city ends in `-hold`** — Emberhold, Lanternhold, Rainhold,
Forgehold, Galehold, Barrowhold. `world_layout.py` enforces the suffix. Do not
name a wilderness zone `-hold`, and do not rename a city off it.

A city is **safe ground** and is exempt from the level-gap rule: Rainhold at
20–30 borders Greenmoor at 1–7 on purpose, so a low character can run to the
water city and live. Do not "fix" that border.

Each city still needs its own decisions — who trains, who binds, which
merchants, whether it is hostile to anyone. **None of that is in the layout.**

## Order of work for a new zone

1. Read its row in `docs/world-layout.json` — `size`, `levels`, `cell`, `kind`,
   `area`.
2. Create `data/zones/<id>.json` with terrain, `seed`, `music`, `bind_point`
   and the usual fields. Copy the shape of `greenmoor.json` for a field zone or
   `thornwood.json` for a wild one; `thornwood.json` also shows `rivers`,
   `tree_mix`, `groves`, `fog_*` and `sun_energy`.
3. Generate **every** border it has from `links` — both sides, all four pieces.
4. Mobs in `data/mobs.json`, factions in `data/factions.json`, NPCs in
   `data/npcs.json`, loot tables in `data/loot.json`. Zone data references them.
5. A new music theme needs a builder in `tools/audio/music.py`; without one,
   reuse an existing `"music"` value rather than naming a track that does not
   exist.

## Verify

```sh
python3 tools/world_layout.py     # the layout's own checks still pass
/Applications/Godot.app/Contents/MacOS/Godot --headless --path . --import
/Applications/Godot.app/Contents/MacOS/Godot --path . -- --autotest --shots=<dir>
```

Then walk the border **both ways** in game. A one-way door passes every static
check there is.

## Do not

- **Do not add a zone, move a cell, or invent a border.** The grid is
  verified — contiguous areas, everything reachable from Emberhold, no zone
  over four passes, no lethal wilderness border. Changing it outside
  `tools/world_layout.py` breaks a check that is not run per zone.
- **Do not give The Grove a pass, a zone line or a cell.** Its isolation is
  asserted, not incidental.
- **Do not hand-write `arrive` coordinates.** That is how a player ends up in a
  mountain.
- **Do not decide what is in a city, or which zones carry dungeons.** Both are
  open, and both are Tyson's call.
  Decided so far: the Greenmoor cave at (-150, -30) leads to Nick's quest
  dungeon, an instance. Like the tavern interior it is off the grid: reached by
  a zone line inside the cave's tunnel, never by a pass.
