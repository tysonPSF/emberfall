# Changing a zone

Read `docs/zone-implementation.md` before creating or connecting one —
borders are derived from `docs/world-layout.json`, never typed by hand
(`CLAUDE.md` says why). These are the traps that brief doesn't cover.

## The zone files are the source; their generators are gone

Almost every zone JSON (and its NPCs in `data/npcs.json`) was written by
a one-off Python generator in a Claude session's scratchpad, and **those
generators were never committed.** Only The Grove's is in the repo
(`tools/zones/the_grove.py`). So edit the zone JSON directly — there is
nothing to regenerate from. For The Grove, change the generator and
rerun it; its gods' positions must stay on their daises.

When you write a new generator, commit it under `tools/zones/`.

## Opening a sealed pass leaves a ridge

Unbuilt borders were sealed with a `"rockslide"` landmark. Every
landmark flattens the ground around its position (`Zone.height_at`,
`_flat_spots`). Swap the rockslide for a zone line and that flat spot
goes with it — the pass can come back as a ridge you can't walk over.
Fix: put a `signpost` landmark (or another light landmark) in the pass
to hold the ground level. *Found 2026-09-27 building the Boneyard.*

## Terraces are steeper than a body can climb

A terrace riser runs 45-56 degrees; a character walks up 45 at most. Roads
get a ramp automatically where they cross a step (`RAMP_PER_METER`,
2026-09-29) — but only roads. Anything else players must reach uphill
(a camp, a quest NPC, a field) needs a road to it, or it sits behind a
wall. `"ramps": false` (Vayuketh's Step) keeps the plain edge for a
stair built onto it.
