# Brief: adopt the Forge's unique weapons

The Elder Dragon set and the two Endless Nightmare swords are modelled in the
Elephant Grove Forge and have never existed in Emberfall. The seventeen items
that should wear them currently point at generic KayKit shapes, so the
Dragonfang Sword is drawn as a plain arming sword and the Dragonmaw Mace as the
Ashfall's ember hammer.

Stage one is done: `tools/forge_bake.py` takes the geometry out of the Forge's
live page and writes `assets/forge_raw/*.glb`. **This brief is stage two** —
turn those raw bakes into shipped assets through `tools/blender/creatures.py`,
register them, and point the items at them.

The Forge stays the source of truth for the *shape*. Emberfall owns the
*asset*. Nothing here should be hand-modelled; if a shape is wrong, fix it in
the Forge and re-bake.

## What you are given

`assets/forge_raw/` — seventeen GLBs and `forge_bake.json`, which carries for
each one its Forge id, the Emberfall item that should wear it, the generic
model it replaces, its materials and its triangle count.

They are raw in four specific ways, and each one is a job below:

| | raw | wanted |
|---|---|---|
| scale | Forge units, about 2x | Emberfall units |
| origin | model root | the grip, where the hand closes |
| triangles | 5,200–13,500 | in line with the 46 weapons already shipped (200–3,000) |
| materials | three.js PBR, emissive baked into `emissiveFactor` | the `props.py` palette |

## The Blender step

Per weapon, in `tools/blender/creatures.py`, as a `build_<name>()` registered in
the builder dict near the end of the file — the same shape as `_ember_hammer`
and `build_court_maul`, except these import a mesh instead of assembling
primitives. `BODIES` already does exactly this with KayKit `.glb` copies, so
follow that pattern rather than inventing one.

1. **Import** `assets/forge_raw/<forge_id>.glb`.
2. **Scale by 0.49.** The bow is the one exception at **0.70** — it is modelled
   along Z and is stubby at the common scale. Check the result in hand against
   the generic it replaces; do not trust a number over your eyes.
3. **Re-origin to the grip.** Emberfall pins a weapon to a hand bone, so the
   origin must sit where the hand closes, not at the model root. The haft runs
   along +Y in the bake with the grip at the low end.
4. **Decimate** to the house budget. Most of the count is in the flame and
   ember shards; decimate those hard and the blades lightly.
5. **Materials** — each mesh is named for its part (`blade`, `guard`, `grip`,
   `wrap`, `fuller`, `flame`, `ember`, `horn`, `bone`, `boneDark`, `socket`,
   `teeth`, `eye`). Repaint through `props.py` so these match the world's
   palette rather than the Grove's. Keep `flame` and `ember` emissive.
6. **Export** to `assets/creatures/<name>.glb`.

### The floating embers

Several weapons carry small flame shards sitting well clear of the weapon —
they are in the Forge too, so they are intentional, not a bake artefact. But
they inflate the bounding box badly (the great flail measures 7.06 with them
and 4.27 without), which will throw off any scale you derive by measuring.
**Hide `flame` and `ember` before measuring anything.** Whether they survive
into the game is your call: they read as magic at rest and as clutter in a
swing. Parenting them to the blade so they follow it is the middle road.

## Naming: this decides the swing animation

`Entity.swing_for()` picks the attack animation **by substring match on the
models.json weapon id**, so what you name these is load-bearing. The order is:

```
exact id in [bow, wand, fishing_pole, torch, shield_badge, shield_round,
             shield_round_barbarian]        -> "attack"
contains dagger|rapier|spear|trident|glaive -> "thrust"
skill starts with "1h"                      -> "slash"
contains 2handed|maul|greathammer|greatsword|staff|slab|spade|titan -> "chop"
otherwise                                   -> "slash"
```

Most of the set is fine. **Three groups are not**, and all three are silent
wrong-animation bugs rather than errors:

- **`dragonwing_bow` and `dragoneye_wand`** — the "attack" rule is an *exact*
  id match, so any uniquely named bow or wand falls past it. The bow would
  swing like a sword. Add the two new ids to that array, or leave these two
  items on the generic models.
- **The great axe, great mace and great flail** — none of `great_axe`,
  `great_mace`, `great_flail` contains a chop keyword, so all three would swing
  one-armed. Adding `great` to the chop list is the clean fix: the
  `skill.begins_with("1h")` check runs first, so a one-handed weapon with
  "great" in its name is already safe.
- **`dragonclaw_fists`** carries the piercing skill but no thrust keyword, so
  it slashes. That may well be right for claws — decide rather than inherit it.

Whichever way you go, the choice belongs in `swing_for()` or in the model
names, not in both.

## Registration

1. `data/models.json` → `weapons`: `"<name>": "res://assets/creatures/<name>.glb"`.
2. `data/models.json` → `grips`: only if it does not sit right in the hand. The
   existing entries (`axe_1handed`, `bow`) show the form; `@l` is the off hand.
3. `data/items/grove.json` → set each item's `model` to the new id. The
   mapping is in `assets/forge_raw/forge_bake.json`; all seventeen items
   already exist, none need inventing.

## Checking it

- In game, equip one of each and watch the swing — that is the only way to
  catch a bad grip or a wrong animation.
- `python3 tools/wiki.py` regenerates the guide. The weapon pictures come from
  whatever `model` points at, so the Items section is a fast visual diff of
  all seventeen at once: run it before and after.
- Expect the guide's weapon-picture count to **fall**. 148 items currently
  share eleven generic shapes; once these seventeen have their own, the
  honest number drops, which is the point.

## Known

- **Tide-Horn is not in this set.** It is the one weapon of the Forge's 108
  with no Smooth-3D definition — `D3()` throws for it, and selecting it in 3D
  silently leaves the previous weapon on screen, so it bakes as a duplicate of
  the Endless Nightmare sword. `forge_bake.py` skips it. No Emberfall item
  wants it, so nothing is blocked, but the Forge's own `check_forge.py` has no
  check for 3D coverage and should.
- `sword_of_the_endless_nightmare` already points at `barrow_lord_sword`, which
  is a real custom model rather than a KayKit generic. Compare the two before
  replacing it — the existing one may be the better fit.
- `dragonbone_arrow` has no slot and no model today. It is ammunition; give it
  a model only if ammunition is drawn in flight.
