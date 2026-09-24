# Emberfall

A classic-EverQuest-style RPG in Godot 4.7: slow, dangerous, group-oriented. This is the solo vertical slice.

## Setup

1. Install **Godot 4.7** (standard build, not .NET). **Blender 5.2** is only needed to regenerate the creatures and props in `tools/blender/`.
2. Clone and open:

   ```sh
   git clone https://github.com/tysonPSF/emberfall.git
   cd emberfall
   godot --path . --import   # first run: imports the art into .godot/ (not in git)
   godot --path .            # play; or open the folder in the Godot editor and press F5
   ```

   On macOS, `godot` is `/Applications/Godot.app/Contents/MacOS/Godot`.

3. Check a change before pushing:

   ```sh
   godot --headless --path . --import                   # parse/compile check
   godot --path . -- --autotest --shots=/tmp/shots      # plays itself, saves screenshots, quits
   godot --path . -- --lineup=gnoll,rat --shots=/tmp/l  # art check: models side by side
   ```

Your character saves to Godot's `user://character.json` (per machine, not in git). `CLAUDE.md` has the architecture rules.

## Controls

| | |
|---|---|
| W/S, A/D | Forward/back, strafe (arrow keys turn) |
| Shift | Hold while moving forward to run; drains stamina (the green bar), which refills once you ease off |
| Mouse / wheel | Look / zoom (zoom all the way in for first person) |
| Alt | Hold for the mouse cursor; it also returns while any window is open |
| Right-click, Tab, F1 | Target what's under the crosshair, nearest enemy, self |
| Left-click | Start attacking your target (the ring on the crosshair fills as the next swing comes up) |
| Q | Auto attack on / off |
| 1–8 | Abilities / spells (moving interrupts casting); learn more from your guildmaster |
| C | Consider (con colors: gray, green, blue, white, yellow, red) |
| X | Sit / stand (much faster regen) |
| L / double-click | Loot corpse |
| E / double-click | Hail a townsperson (click gold [keywords] in their reply) |
| G | Interact with your target: a merchant's shop, the bank, or a give window for quest turn-ins |
| I, H, Esc | Inventory, help, clear target / interrupt / close |

## What's in the slice

- **Emberhold**: the first city, a walled town around an undying hearth-fire (the bind point). Guards, Keeper Maelin (ask about the [Emberfall]), a market with Tovin (provisions, buys your loot) and Garrow (weapons, armor), Banker Odile at the Watch hall, and class guildmasters (Sergeant Brask, Sister Anwen, Magister Coyle) who teach new spells as you level, and a north gate whose pass leads to Greenmoor.
- **Greenmoor**: one zone with a bind obelisk, rats and gnoll pups nearby, fire beetles to the southeast, aggressive skeletons at the ruins (west-northwest), and a gnoll camp (northeast) with a rare named mob, Grubnak the Mangy. The road south runs past Warden Holt's watch house to the pass to Emberhold.
- **Warden Holt** at the watch house by the obelisk: hail him, ask about [gnoll fangs], and trade him four for a repeatable bounty (a sword the first time). Quests are data in `data/quests.json`, NPC dialogue in `data/npcs.json`.
- **Faction**: The Watch, Citizens of Emberhold, Blackpaw Gnolls, the Restless Dead (see the inventory window). Killing gnolls earns the Watch's favor; hated enough, even gnoll pups attack on sight. Townsfolk refuse you at Dubious or worse. You may attack NPCs (press Q twice), but they fight back, the guards come running, and your standing pays for it; at Scowls, guards attack on sight.
- **3 classes**: Warrior (kick, taunt; later bind wound, bash, battle cry), Cleric (heal, strike; later courage, light healing, smite, hearthward), Wizard (nuke, gate; later burning embers, minor shielding, root, fire bolt). Spells in `data/spells.json` list which classes learn them at what level and cost.
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
2. Night and darkness, more quest givers, mob pathfinding.
3. Real art: swap `Entity.make_visual` for models; navmesh pathing for mobs.
4. **Grouping + multiplayer**: headless Godot server that runs `World`; `request_*` calls become RPCs; group XP split, heal and taunt aggro already work.
5. Persistence server (Postgres), accounts, more classes and zones.
