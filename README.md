# Emberfall

A classic-EverQuest-style RPG in Godot 4.7: slow, dangerous, group-oriented. This is the solo vertical slice.

## Run it

Open the folder in Godot (`/Applications/Godot.app`) and press F5, or:

```sh
/Applications/Godot.app/Contents/MacOS/Godot --path ~/Desktop/Claudesploration/emberfall
```

Smoke test (plays itself, saves screenshots, quits):

```sh
/Applications/Godot.app/Contents/MacOS/Godot --path . -- --autotest --shots=/tmp/shots
```

## Controls

| | |
|---|---|
| W/S, A/D | Forward/back, turn (A/D strafe while holding right mouse) |
| Right-drag / wheel | Look / zoom (zoom all the way in for first person) |
| Left-click, Tab, F1 | Target, nearest enemy, self |
| Q | Auto attack |
| 1–4 | Abilities / spells (moving interrupts casting) |
| C | Consider (con colors: gray, green, blue, white, yellow, red) |
| X | Sit / stand (much faster regen) |
| L / double-click | Loot corpse |
| I, H, Esc | Inventory, help, clear target / interrupt / close |

## What's in the slice

- **Greenmoor**: one zone with a bind obelisk, rats and gnoll pups nearby, fire beetles to the southeast, aggressive skeletons at the ruins (west-northwest), and a gnoll camp (northeast) with a rare named mob, Grubnak the Mangy.
- **3 classes**: Warrior (kick, taunt), Cleric (heal, strike), Wizard (nuke, gate).
- **Mob AI**: wander, aggro radius, social assist (trains!), flee at low health, leash home.
- **EQ-style rules**: 6-second regen ticks, sit to meditate, con colors, no XP from gray mobs, XP loss on death, **corpse runs** (your gear stays on your corpse).
- Auto-saves to `user://character.json` every 30s and on quit.

## Layout

```
data/             all tunable content (JSON): classes, spells, mobs, items, zones, config
scripts/autoload  GameData (content), Controls (key bindings), World (all game rules)
scripts/entities  Entity base, Player, Mob, Corpse
scripts/world     Zone builder (terrain/props from seed), SpawnPoint
scripts/ui        HUD, title screen, shared UI styling
```

## Roadmap

1. **Now**: play it, tune numbers in `data/*.json` until the loop feels right.
2. Vendors (sell the fangs and eyes), a guard NPC or two, a second zone joined by a zone line.
3. Real art: swap `Entity.make_visual` for models; navmesh pathing for mobs.
4. **Grouping + multiplayer**: headless Godot server that runs `World`; `request_*` calls become RPCs; group XP split, heal and taunt aggro already work.
5. Persistence server (Postgres), accounts, more classes and zones.
