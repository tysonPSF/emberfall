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
