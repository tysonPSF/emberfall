# Adding a city, a race's home, or god-related content

## Every starting city gets a bag quest

A starting city is any race's `"home"` in `data/races.json`. Each one
needs its own early bag quest line: about three steps, from an NPC in
the city or its beginner ground, using that ground's own drops, ending
in a 10-slot NO DROP bag. Emberhold, Rainhold and Lanternhold have one
(`data/items/bag_quests.json`). If you make a city a starting city, or
move a race's home, add one in the same change.
*Tyson 2026-09-28: "make sure we add one every time we add a city as a
starting city"* — Rainhold and Lanternhold starters had gone without.

## A beginner ground needs enough calm monsters to share

A race's first zone should hold at least ~20 non-aggressive monsters of
levels 1-5 (the lowest back in 30 s), spread over its starting area: a
server's new players all hunt there at once. The Wallow and Duskwood
shipped with 12 each and felt empty; Duskwood had nothing calm past
level 4 but its wolves and bones. Autotest `starter_spawns` counts them.
And don't lean on the stepped `terraces` design for new zones: High
Terrace lost its steps (their risers were walls, and too many zones
shared the look). *Tyson 2026-09-29.*

## A zone's whole map should have monsters

Run `python3 tools/zones/spawn_fill.py` after building or changing a zone:
it reports ground more than ~65 m from any spawn and `--write` fills it
with the nearest ordinary spawn's monsters (a generator calls `fill()`).
High Terrace and most 30-50 zones had a third to half of their ground
empty and felt deserted. *Tyson 2026-09-29.*

## Gear must get better with the zone

A reward or a drop from a harder zone must beat one from an easier one.
Run `python3 tools/item_curve.py` after adding items, rewards or mob gear:
it fits each slot's score to zone level and flags rewards under 70% of
the curve, and mobs whose random gear is more than 12 levels below them.
Give generic mob gear a `"ladders"` rung in loot.json (it climbs with the
mob's level) rather than a fixed low item; flavor gear stays off ladders.
*Tyson 2026-09-29: a Sunward Steps ring was worse than an earlier zone's:
the shared `rings` table served levels 1-28.*

## The gods belong to another game too

The five deities come from Tyson's other game, Elephant Grove
(`../elephant-grove`, `src/core/world/zones.ts`): Prabhagaj the
Dawn-Tusk (light), Jalendra the Tide-Trunked (water), Agnavar the
Ember-Tusked (fire), Vayuketh He Who Breathes the Plains (wind), Timiraj
the Unlit (dark). Their names, titles and portraits
(`assets/deities/deities_128.png`) must stay consistent with that game —
don't rename or restyle them here alone. Merrick, the pond NPC, is also
from Elephant Grove.

## Names

Our own names only — see [../conventions.md](../conventions.md).
