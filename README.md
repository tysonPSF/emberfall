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

## Playing together

One machine runs the **server**, which holds the world, the rules, and everyone's accounts and characters. Everyone else plays a normal copy of the game: type the server's address into the **Server** box on the title screen and press **Connect**, then log in (the first time, **Create account**) and pick or create a character. Your offline character can be brought over once. Camping returns you to character select. Tick **Remember password** to skip typing it next time: the game keeps a hash of it in `settings.json` (never the password itself), per server and account; untick it to forget. Anyone with that file could still log in to that game account, so don't tick it on a shared computer.

**Running the server** (Linux or macOS, no screen needed):

```sh
git pull
tools/server/run_server.sh                 # GODOT=/path/to/godot PORT=7777 to override
```

- It listens on **UDP port 7777**. Open that port in the server's firewall and, if it's behind a router, forward it.
- `tools/server/emberfall.service` is a systemd unit that keeps it running. With `emberfall-update.timer` the server also updates itself from `main` (players get a minute's warning); `tools/server/deploy.sh` updates it now over SSH. Setup: `docs/server-updates.md`.
- Players must run the same version as the server; after pulling on the server, restart it and have everyone pull too. An older client is turned away with a message.
- Options: `--port=7777`, `--data=<dir>` (accounts and characters; the run script defaults to `~/emberfall-data`: **back this folder up**), `--zone=greenmoor` (where new characters start; default is the starting city).
- The server saves everyone every 30 seconds and whenever they camp, zone or disconnect.

**What works so far** (multiplayer phases 1 and 2): everyone sees each other, fights the same mobs, loots, trades with NPCs, shops, banks, trains and camps, and each zone runs on its own, so players can be in different zones at once. For now:
- Groups work EQ-style: up to 6, a leader, experience split by level among members in the zone (with a small bonus per member, and nothing for anyone far below the group's highest), faction and loot rights for the group that did the most damage (3 minutes, then anyone), coin split on loot, and group spells (Clerics: Circle of Mending at 5, Hearthbond at 6).

For testing on one machine: run the server (add `--data=/tmp/efdata` to keep test accounts out of the way), then `godot --path . -- --nettest=Alpha --port=7777` and `--nettest=Bravo` in two more terminals (`--autotest --only=remember_login --login-port=<port>` checks Remember password against it) (`--dev-loot` on the server makes every mob drop everything).

## Controls

| | |
|---|---|
| W/S, A/D | Forward/back, strafe (arrow keys turn) |
| Shift | Hold while moving forward to run; drains stamina (the green bar), which refills once you ease off |
| Mouse / wheel | Look / zoom (zoom all the way in for first person) |
| Alt | Hold for the mouse cursor; it also returns while any window is open |
| Right-click, Tab, F1 | Target what's under the crosshair, nearest enemy, self |
| T | Cycle townsfolk and corpses (Tab only walks the living mobs) |
| O | Settings. Turning **Mouse controls** off keeps the cursor out and puts turning back on A/D, so the game plays without a mouse |
| Left-click | Start attacking your target (the ring on the crosshair fills as the next swing comes up) |
| Q | Auto attack on / off |
| 1–8 | Abilities / spells (moving interrupts casting); learn more from your guildmaster |
| C | Consider (con colors: gray, green, blue, white, yellow, red) |
| X | Sit / stand (much faster regen) |
| L / double-click | Loot corpse |
| I | Inventory, EQ-style: your equipment around your character, stats and coin, standing on the bag bar (your 8 general slots; right-click a bag to open it). Its **?** button lists the item controls and **Faction +** unfolds your standings. **Click** picks an item up onto the cursor and puts it down (or swaps); **Ctrl-click** takes one from a stack; **Shift-click** equips (or sells, banks, offers, depending on the open window) |
| B | Open every bag you carry, or close them all (Esc closes open bags too) |
| E / double-click | Hail a townsperson (click gold [keywords] in their reply) |
| G | Interact with your target: a merchant's shop (click buys one; **Buy 20** beside arrows, stones and other small stackables; Shift-click a full stack), the bank, or a give window for quest turn-ins |
| I, H, Esc | Inventory, help, clear target / interrupt / close |
| K | Skills: weapon, offense/defense, dodge/parry/block, abilities and casting schools. They rise as you use them, up to a cap set by class and level |
| Right-click an item | Item window: full stats, a turning 3D look, **Use** for click effects, **Link in chat** (the link opens the same window for anyone who clicks it) |
| F2–F6 | Target your groupmates (the group window on the left does the same) |
| Enter, / | Chat. Plain text is `/say` (and talks to a targeted NPC). `/shout` (zone), `/ooc` (server), `/tell name msg`, `/r`, `/who`, `/who all`, `/lfg`, `/random`, `/loc`, `/camp`, `/help`. Groups: `/invite [name]`, `/accept`, `/decline`, `/g`, `/disband`, `/kick`, `/makeleader`, `/assist [name]`, `/follow` |

## What's in the slice

- **Emberhold**: the first city, a walled town around an undying hearth-fire (the bind point). Guards, Keeper Maelin (ask about the [Emberfall]), a market with Tovin (provisions, buys your loot) and Garrow (weapons, armor), Banker Odile at the Watch hall, and class guildmasters (Sergeant Brask, Sister Anwen, Magister Coyle) who teach new spells as you level, and a north gate whose pass leads to Greenmoor.
- **Greenmoor**: one zone with a bind obelisk, rats and gnoll pups nearby, fire beetles to the southeast, aggressive skeletons at the ruins (west-northwest), and a gnoll camp (northeast) with a rare named mob, Grubnak the Mangy. The road south runs past Warden Holt's watch house to the pass to Emberhold.
- **Thornwood Vale**: through Greenmoor's north pass (the road runs from Emberhold's gate all the way there). A 512 m forest valley for levels 6-14: timber and dire wolves, black bears, venomous thornback spiders and their Broodmother, the Bloodtusk orc camp and its Warchief, and the Hollow Watch, skeleton knights haunting a ruined watchtower under Captain Veyl. Sergeant Harlan patrols the south road from the obelisk over the bridge to the crossroads and back: run to him and he'll take on what's chasing you, and he clears aggressive beasts that stray near the road. Elowen the Hermit keeps the obelisk: two quests (wolf pelts; spider silk and venom), and she sells arrows. A river runs across the southern vale (wade it, or take the road's bridge); the watchtower stands ruined over the Hollow Watch's courtyard, and the Broodmother's nest is hung with webs. Its east pass leads to Hollowmere; the north and west passes are closed by rockslides until the next zones.
- **A cave** at the foot of Greenmoor's western mountains: torches at a timber-braced mouth and a tunnel into the dark. The dungeon beyond is coming.
- **Warden Holt** at the watch house by the obelisk: hail him, ask about [gnoll fangs], and trade him four for a repeatable bounty (a sword the first time). A repeatable quest pays full experience the first time and half after that (`quest_repeat_xp` in `data/config.json`, or `repeat_xp` on a quest); coin and faction stay the same. Quests are data in `data/quests.json`, NPC dialogue in `data/npcs.json`.
- **Faction**: The Watch, Citizens of Emberhold, Blackpaw Gnolls, the Restless Dead (Faction + in the inventory window). Killing gnolls earns the Watch's favor; hated enough, even gnoll pups attack on sight. Townsfolk refuse you at Dubious or worse. You may attack NPCs (press Q twice), but they fight back, the guards come running, and your standing pays for it; at Scowls, guards attack on sight.
- **3 classes**: Warrior (kick, taunt; later bind wound, bash, battle cry), Cleric (heal, strike; later courage, light healing, smite, hearthward), Wizard (nuke, gate; later burning embers, minor shielding, root, fire bolt). Spells in `data/spells.json` list which classes learn them at what level and cost.
- **Mob AI**: wander, aggro radius, social assist (trains!), flee at low health (unless others of their kind are still fighting nearby), leash home.
- **Compare gear**: hover an item (or right-click it for the item window) to see it against what you wear in that slot: every stat that changes, gains in green and losses in red; weapons compare delay too.
- **Gear quality shows**: Crude gear looks dull, Fine has a faint green sheen, Superior a blue-steel one, Masterwork a soft purple glow, on you, other players and monsters wearing their loot.
- **Visible gear**: armor shows on your character the way EverQuest reskinned it. Tunics, sleeves, gloves, pants, boots and helmets swap in the matching KayKit parts (plate from the knight, leather from the rogue, linen from the ranger, hoods and hats from the skeletons), mapped in `data/models.json` `"body_parts"`. Monsters show the loot they will drop the same way.
- **Ranged weapons for pulling**: a Range slot for a bow (warriors, Archery, shoots arrows from your pack) or a sling (anyone, Throwing, slings stones). Press R to fire at your target: hit or miss, it comes to you. Now and then an arrow or stone that hits stays in the monster, and you can loot it back from the corpse. Bows drop too: gnoll scouts and Bloodtusk raiders sometimes carry a shortbow (raiders now and then an Ashwood Recurve) and a handful of arrows; Warchief Grolthar often carries the recurve, and Broodmother Silkfang can drop the Silkstring Longbow, whose arrows carry her venom. Range and line of sight are checked. Garrow sells the bow and arrows, Tovin the sling and stones; shift-click in a shop buys a whole stack.
- **Quest line: A Proper Pack**: ask Tovin in Emberhold about a [proper pack]. Rat whiskers for cord, then Warden Holt in Greenmoor stitches Blackpaw pelts (gnoll drops) with it, then fire beetle eyes for the clasp: Tovin's Trail Pack, a 10-slot bag.
- **Giving items to NPCs**: press G at a quest giver to open a trade (at a merchant, G opens a trade instead of the shop once you carry what their quest needs), or pick an item up and click the NPC to hand it over, as in EverQuest.
- **Dropping items**: pick something up onto your cursor and click the ground: it lands at your feet (bags keep their contents) for anyone to pick up with a click, and rots away after 15 minutes. NO DROP items can't be dropped.
- **Music**: an original theme for the title screen and each zone (Emberhold's lute waltz, Greenmoor's pastoral harp and flute), looping and crossfading as you travel, in the spirit of classic EverQuest's zone music. When something has you on its hate list, a driving combat theme fades in, and the zone's returns a few seconds after the fight. Music starts at 25%; the volume slider is in the Esc menu and Settings (O, or `[` / `]`).
- **Spells and abilities to level 15**: warriors learn Heroic Strike (11), Rally (13, group) and Shield Wall (15, needs a shield); clerics Healing (11), Blessed Armor (12), Circle of Renewal (13) and Hallowed Strike (15); wizards Frost Lance (11), Emberstorm (12), Greater Shielding (13) and Ice Comet (15). Train them at your guildmaster in Emberhold.
- **Level cap 20** (`max_level` in `data/config.json`), with three new abilities or spells per class at 16, 18 and 20: warriors Provoke (taunts everything near), Defensive Stance and Cleave (hits nearby foes too); clerics Greater Healing, Divine Aura (8 seconds untouchable) and Sunfire; wizards Lightning Bolt, Frost Snare (half speed) and Fireball (hits everything near the target); rogues Assassinate (from hiding, from behind), Blind (5 seconds unable to act) and Deadly Poison. Guards are always 15 levels above the cap (`guard_levels_over_cap`), so they rise with it.
- **Blessing of the Elders**: every new character has it until level 15, the level cap: +15% experience from everything (kills, group shares, quests). It fades, with a message, when you reach 15 (`elders_blessing` in `data/config.json`).
- **Spell effects**: spells show where they land (frost and fire bursts, rising heals, golden buff rings, lingering embers and venom, roots at the feet, a swirling gate) and casters glow while casting, for everyone watching. Kick and Bash have their own moves: a front kick and a shield-first lunge.
- **Buff window**: your buffs on the right of the screen, each with its icon, name and time left (hover for what it does); it moves aside when the inventory is open.
- **Debuff window**: under it, in red, whatever is hurting or holding you: poison, burns, frost, roots, with time left and the damage per tick; each tick names its source in the log ("You take 3 damage from Thornback Venom").
- **Rainhold**: the Long Monsoon's city, through Greenmoor's west pass (the road forks west at the obelisk), or from The Weeping Throat's south pass. A stilt city over a rain-swept lagoon: piers and rope-railed walkways link timber halls with sweeping thatch roofs, and at its heart stands the shrine of Jalendra, the Tide-Trunked: a stone elephant pouring water from her raised trunk into her basin, the city's bindstone. Tidepriest Nalini gives her followers the Tide-Trunk's Blessing (+30 HP, +3 health and mana regeneration for half an hour, once an hour) and asks for the Heart of the Storm; all four guildmasters keep the Halls of the Tide and of Rain; Banker Oduya (the same bank as Emberhold), Armorer Kaveh (tidesteel, rainsilk and sharkskin for 20-25), Weaponsmith Ifeoma, Fisher Oji (poles, worms, and snapper wanted) and Hunter Asha (troll tusks, Gorrak's crown, Graveljaw's tooth), guarded by the tidewatch. It always rains.
- **The Weeping Throat**: through Thornwood's west pass, or north from Rainhold. A 448 m rain jungle for levels 20-24: huge trees, a winding river and a side stream, waterfalls off the cliffs, and the root-choked temple of Jalendra, where water elementals and the Weeping Storm rage (more elementals walk in the rain at night). Mudtooth river trolls, who heal as fast as you cut them, keep a hut camp on the river's east bank under Gorrak Mudtooth; giant poison frogs hop the undergrowth; crocodiles bask on the banks, and Old Graveljaw lurks in the southwest swamp. Its own theme plays there; the west (Reedmere) and north (Drownfast) are closed by rockslides for now.
- **Magician** and **Necromancer**, the pet classes (pick them at character creation, with any deity). A pet fights at your side, EverQuest style: it follows, attacks what you're fighting or whatever hits either of you, taunts, and answers the pet window's buttons or /pet (attack, back off, follow, guard, sit, taunt, health, leave). It comes with you when you zone and log out, its kills and experience are yours, and it grows stronger as you do.
  - **Magicians** call elementals: earth (a slow, tough rock golem that holds a monster's attention), water (its blows chill), fire (fragile but burns hard), air (quick, and its gusts stagger), and at 23 a primal storm elemental. Renew Elements and Greater Renewal heal it; Burnout, Elemental Bond, Primal Fury and Elemental Aegis make it faster, tougher, fiercer or untouchable for a moment. Trained by Elementalist Corvane in Emberhold, Sunforger Aurelia in Lanternhold and Tidecaller Nuru in Rainhold.
  - **Necromancers** raise a skeleton that grows from a minion to a knight, and at 25 a Skeletal Knight. They drain life (Lifetap, Siphon Life, Soul Rend), rot foes with Disease Cloud and Venom Bolt, feed on them with Bond of Death, root and snare them, send them fleeing with Dread and Mass Dread (named foes don't scare), and Feign Death when it all goes wrong. Their Emberhold guild meets in a crypt under a mausoleum in the northwest of the city (Morvath the Pale); Mortician Vesk and Bonewright Ilo teach in Lanternhold and Rainhold.
- **Hotbars you arrange**: two rows of ten, keys 1-0 and Shift+1-0. Open your spellbook (P) and drag spells, abilities and actions (attack, ranged, sit, consider, hail, loot, and your pet's commands) onto any slot; pick up a potion, a meal or a click item and click a slot to make it a hotkey that shows how many you have left; drag slots to swap them, drag one off or right-click it to clear it, and lock the bars so nothing moves by accident. Each character keeps its own layout, online and off.
- **Tradeskills**, EverQuest style: Cooking, Tailoring, Alchemy and Smithing, open to every class and raised by use up to 100. Put ingredients into a container and press Combine: ovens, looms, brew barrels and forges stand in each city's crafters' corner (Emberhold's northwest yard, Lanternhold's southwest quarter, Rainhold's platform by the fishers' dock), campfires cook simple meals out in the wild, and a sewing kit or a mortar and pestle is a bag you craft in anywhere. Each recipe has a trivial: below it you may fail (and lose the ingredients, but never your smithy hammer) and each try can teach you something; at or above it you rarely fail and learn nothing more. Provisioners sell the supplies (flour, spices, tanning salts, thread, herbs, vials, ore, flasks, arrow shafts) and four recipe books whose pages show in their tooltip. Beasts now drop raw meat and frog legs. Cook meals (one at a time, forty minutes of HP, regeneration or stats), tan hides and sew leather armor, bags and a crocscale jerkin, brew healing and mana potions, antidotes and tonics (right-click to drink; healing potions share a 10-second cooldown), and smelt iron and steel into arrows, blades, shields and a greataxe.
- **Fishing**: equip a fishing pole, face open water with a can of worms in your pack, and right-click the pole (or type /fish). Each cast uses a worm; your Fishing skill (every class has it) sets the odds, and each water has its own catch: trout and carp anywhere, snapper, eels and the rare rainbow koi in Rainhold's lagoon, catfish in the Throat, and now and then an old boot.
- **Level cap 25**, with three more abilities per class at 21, 23 and 25: warriors Shield Slam (stuns more often than Bash), Battle Fury (30% faster swings) and Whirlwind; clerics Healing Tide (group heal), Word of Awe (a stun) and Armor of Faith (group AC, HP and regeneration); wizards Chain Lightning, Arcane Harvest (a burst of mana) and Meteor; rogues Crippling Poison (hits may snare), Eviscerate and Vanish (drop every foe's anger and hide, mid-fight).
- **Lanternhold**: the Dawnstair's city, through Sunward Steps' east pass at the top of the climb. A walled city of lanterns (strung across every street, glowing gold at night) round the stone shrine of Prabhagaj, the Dawn-Tusk: a giant elephant raising the sun in its trunk, ringed by sun pillars. The shrine is the Dawnstair's bindstone, and Dawnpriest Amaru gives the Dawn-Tusk's Blessing (+12 AC, +40 HP for half an hour, once an hour) to his followers. All four guildmasters (Captain Idris, High Keeper Solenne, Magus Orrin, Kestrel), Banker Tamsyn (the same bank as Emberhold), Armorer Bex (steel, dawnweave and shadowleather for levels 14-20) and Weaponsmith Varro, guarded by the Lanternhold wardens.
- **The Bleach**: through Sunward Steps' north pass. A 512 m sun-bleached salt waste for levels 16-21: blinding white salt flats, cracked badlands, mesas, a dry riverbed and a dead oasis, with the bones of a titan lying in the salt. Salt traders keep a caravan camp by the south entry (Caravan-Master Suri: scorpion stingers, repeatable, and the Salt-Wolf's warhorn; Saltmaster Ibrem: supplies, and the Heart of the Titan). Giant scorpions roam the waste and nest in the east salt pan round the Salt Queen; salt basilisks stare travelers stiff on the flats; bone giants rise from the titan's ribcage round the Bone Titan, and more walk at night; the Salt Raiders hold a camp of stolen wagons in the east under Vashti the Salt-Wolf. Its own theme plays there. The north (Mirror Flats) and west (High Terrace) are closed by rockslides for now.
- **Sunward Steps**: through Hollowmere's east pass, the first land of the Dawnstair (Prabhagaj, the Dawn-Tusk). A 448 m climb for levels 14-18: broad golden terraces rising east in seven steps, with a pilgrims' waystation and obelisk at the bottom (Pilgrim-Mother Ysolde: pilgrims' tokens, repeatable, and Sahkrin's scarab; Quartermaster Dov: supplies, and the False Sun), shrines of the Dawn-Tusk on the terraces kept by stone guardians, and the Great Temple at the top under the Dawn Colossus. Mountain rams graze the steps and sunhawks hunt the high terraces; a false-sun cult holds the south terraces under Hierophant Vaur; the sun-scorched dead of the Pilgrims' Rest walk at night with their high priest, Sahkrin the Unrisen. Its own theme plays there. Its east pass leads up to Lanternhold; its north pass leads to The Bleach.
- **Harrowfield**: through Greenmoor's new east pass (the road forks east at the obelisk), or down from Hollowmere's south pass. A 384 m farmland for levels 3-9: wheat fields fenced in split rails, each with its scarecrow, a windmill turning on a rise, an orchard, and the hamlet of Harrow's Rest round a green and a well: Farmer Oswin (boar tusks, repeatable; and Garrick's ledger), Widow Marta (Old Tatters) and Tilda the grocer (bread, arrows, stones), with Watchman Pell walking the west road. Wild boars root in the fields (Old Bristleback in the orchard); the Harrowfield Brigands under Garrick the Red hold an abandoned farm in the southwest and prey on the west road; after dark the scarecrows climb off their posts, and Old Tatters walks the south field. Its own theme plays there.
- **Hollowmere**: through Thornwood's east pass. A 448 m misty lake basin for levels 10-15: a wide mere with three islands, reed shores and drowned ruins half-sunk in the south shallows. Fishers live on a stilt village of boardwalks and huts out over the water on the east shore, by the obelisk: Elder Tamsin (two quests: Old Snapjaw, the great turtle of the middle island, and the Drowned Bell) and Brina the Netmaker (sells ammo, bait and smoked perch; pays for Mirescale scales), guarded by a Mere Sentry. Mire toads, bog leeches and snapping turtles fill the shores; the Mirescale lizardfolk (a kill-on-sight tribe with shamans and Chieftain Ssrakka) keep a reed-hut camp in the western marsh; the drowned walk the ruins, many more after dark, when Captain Maren rises. Its own theme plays there. Its south pass leads to Harrowfield and its east pass to Sunward Steps; the north pass is closed by a rockslide until High Terrace is built.
- **Night and day**: a game day lasts 72 real minutes (3 minutes an hour, EverQuest's pace), read off the real clock so everyone online shares it. The sun rises around 6:00 and sets around 20:00, crossing east to west with golden dawns and dusks; from 21:00 to 5:00 a blue moon lights the land. After dusk Emberhold's windows glow and the Watch carries torches. Some spawns come out only at night (skeletons roaming Greenmoor's western fields, wolf packs and skeleton knights in Thornwood) and go back at dawn unless they're in a fight. `/time` tells the hour.
- **Rogue** (the fourth class): trained by Vessa Nightwhisper in the back corner of Emberhold's tavern. Backstab (from behind, with a dagger; double damage as an opener from hiding), Hide (unseen by monsters not already after you; moving without Sneak, attacking or another ability ends it), Sneak (half speed, stay hidden), Evade (sheds anger), Envenom Blade (hits may poison), Rake (a bleed), Bind Wound, and Dual Wield and Double Attack at 13 and 15. Hidden, you are a ghost to yourself and invisible to others.
- **Dual Wield and Double Attack** (warriors and rogues, at levels 13 and 15): place a one-handed weapon (sword, axe, club, dagger) in the off-hand slot to swing it on its own timer as the Dual Wield skill allows, trading the shield's armor, block and Bash for damage; Double Attack sometimes swings the main hand twice. Both rise with use, and the character sheet shows the off hand's damage and delay.
- **Bow shots**: firing a bow puts the sword and shield away, raises the bow in your left hand, draws and looses (`Bow_Shoot`, built in `tools/blender/anims.py`); a sling throws with an empty hand. Everyone nearby sees it.
- **Encumbrance**, EverQuest-style: everything you wear and carry has a weight (a dagger 1.5, a sword 4, plate far more than cloth, a pelt 1.5, arrows and rings 0.1), and so does coin: 0.1 per coin, counted as the fewest coins (1 platinum = 10 gold), so pocket change is light and a fortune is heavy. Coin in the bank weighs nothing. Good bags lighten what's inside (a leather backpack by 25%, Tovin's Trail Pack by 50%). Your limit grows with level and STR; past it you slow down, 10% for every 10% over (never below 40%), and far past it you can't sprint. The character sheet shows Weight carried / limit, red when over; tooltips show each item's weight.
- **Bag bar**: your eight general slots sit over the hotbar, so you rarely need the inventory window: they work just like it (click, Ctrl-click to split, Shift-click, right-click a bag to open it). Each bag shows how full it is (4/6) and the bar how many slots are free; rest the mouse on a bag to peek inside; "+3 Wolf Pelt" notes float up when loot comes in; items a quest of yours wants carry a gold "!" (and "Warden Holt wants 4 (you have 2)" in the tooltip); the Ranged button counts your arrows or stones.
- **Hotbar**: one row of square gems for your spells and abilities (1-8) plus Attack (Q), Ranged (R) and Sit (X). Each shows a cooldown sweep, dims when you can't use it (mana, target, range) and glows while a toggle is on. Consider, Skills and Inventory are the small icons beside the gear, top right.
- **Group chat window**: while you're in a group, a second chat window beside the main one shows only group chat and group events, so it doesn't scroll away in a fight (the lines stay in the main window too). Its Talk button switches your chat line to /g.
- **Chat channels stick**: after /g (or /ooc, /sh, /t Name, /r) plain lines keep going there until you switch; /s goes back to say. The chat line shows where you're talking.
- **EQ-style rules**: 6-second regen ticks, sit to meditate, con colors, no XP from gray mobs, XP loss on death, **corpse runs** (your gear stays on your corpse).
- Auto-saves to `user://character.json` every 30s and on quit.

## Layout

```
data/             all tunable content (JSON): classes, spells, mobs, items, zones, config
scripts/autoload  GameData (content), Controls (key bindings), World (all game rules), Net (server/client)
scripts/entities  Entity base, Player, Mob, Corpse
scripts/world     Zone builder (terrain/props from seed), SpawnPoint
scripts/ui        HUD, title screen, shared UI styling
```

## Roadmap

1. **Now**: play it, tune numbers in `data/*.json` until the loop feels right.
2. ~~Night and darkness~~ and ~~mob pathfinding~~ (done: monsters and guards path around trees, rocks, walls, fences and huts), more quest givers.
3. Real art: swap `Entity.make_visual` for models; navmesh pathing for mobs.
4. **Multiplayer**: done through EQ grouping (dedicated server, zones side by side, accounts and characters on the server, chat, groups). Later: corpse dragging and consent, raids.
5. Persistence server (Postgres), accounts, more classes and zones.
