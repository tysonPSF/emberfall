# Opening the Grove: the gods' questlines

Status 2026-10-03: Prabhagaj's line and the Dawnreach are built (branch
`grove-dawn`, generator `tools/zones/realm_dawnreach.py`, test `dawn_line`); the
other four gods follow its pattern. Read this before building any god's line or realm.

## What it's for

The Grove is the endgame's carrot. A new player can't reach it; a level 50
who has walked their god's line can. Opening it is where the story starts:
past it, content is for groups and guilds (the gods' trials, raids, raid gear).
A level 50 can still solo for rare loot, but nobody solos their way in.

## The shape of every god's line

- **Who:** followers of that god only (`Player.deity`), level 46 and up.
- **Started by** the god's shrine priest in their city (Prabhagaj: Dawnpriest
  Amaru in Lanternhold). Hailing them at 46+ adds "I've felt something
  [stirring]"; below 46, or following another god, they don't mention it.
- **Five steps** across the endgame zones, each soloable but hard at 50:
  a relic from a named (rare spawns: you camp them), sometimes with lesser
  drops, handed to someone in that zone who knows its story.
- **Step six is the god's realm:** the priest opens the way for you and your
  group. The realm is group content: its last fight needs three or more
  (`min_players`). The boss gives the seed's heart; the god's avatar in the
  realm turns it into the **Grove Seed** and the god comes to your dais in the
  Grove (`reward.grove_deity`).
- **Guild value:** whoever holds the seed brings their group along when they
  walk to the Grove; guildmates already see the gods each other has earned.

## Realms

Each god has a realm, off the 45-zone grid (like Duskhold or the Grove), and a
realm is a **region**: it starts as one zone and grows (more zones linked by
zone lines inside it, raid zones later). In `tools/world_layout.py` a realm is
an area of its own (`REALMS`: id, god, zones, entry), never a grid cell.
Zone ids: `<realm>` for the first, `<realm>_<part>` for the rest.

| God | Realm | Mood |
|---|---|---|
| Prabhagaj (light) | the Dawnreach | peaks above a sea of cloud in an endless sunrise; gold-roofed temples; the Dawn-Tusk's light fading at the edges |
| Jalendra (water) | to come | a drowned sky-sea |
| Agnavar (fire) | to come | the god's inner forge, molten halls |
| Vayuketh (wind) | to come | open sky, broken stair-islands |
| Timiraj (dark) | to come | the hall beyond the Table, starless |

The evil races' gods (Makarosh, Mahishra, Tantuvi, Dipanti) aren't Grove gods;
their followers' road to the Grove is still to design.

## Prabhagaj's line: "The Last Dawn"

1. **A Stirring at the Shrine** (Amaru, Lanternhold). The Dawn-Tusk's light
   is failing somewhere beyond the world. In the Ivory Field the ghosts of the
   great herds still remember him: bring the **Grandmother of Herds' Memory**
   (the Grandmother of Herds, 46) and 4 **dawn-pale motes** (ghost elephants).
   Hand-in: Sister Imelda at Tuskwatch, who reads the memory.
2. **The Sunstone of Ysmoor** (Imelda). Ysmoor's queens kept a stone that
   held a sunrise: **Ysmoor's Sunstone** from Queen Ismay (Fogfall, 44, at
   night). Hand-in: Loremaster Evander at the Lanternwatch.
3. **A Lamp in the Unlit** (Evander). The last lamp lit from the god's own
   fire went into the dark: **the Last Dawn-Lamp** from the Pale Keeper (the
   Unlit, 48). Hand-in: Lampwarden Solenne, who relights it.
4. **The Champion's Spear** (Solenne). The Dawn-Tusk's champion stands
   turned to stone on Lastwalk with his spear: **the Dawnspear's Head** from
   the Unmoving Champion (Lastwalk, 50). Hand-in: Relic-Keeper Wilhelmina.
5. **The Way Opened** (Wilhelmina sends you home to Amaru with the lamp,
   stone and spear). Amaru opens the way: say "dawn" to him and he walks you,
   and your group beside you, into the Dawnreach.
6. **The Dawn-Eater** (in the Dawnreach). A hunger from outside the world is
   eating the god's light: the Dimming (level 52, `min_players` 3, a group
   boss with a court) at the realm's heart drops **the Ember of First Light**.
   The Dawn-Tusk's avatar takes it: the **Grove Seed** (NO DROP), and
   Prabhagaj comes to his dais in the Grove.

Each step pays experience like the zone's own quests; the finale also gives a
level-scaled reward (to design with the realm).

## What the build needs

- Quests: `"deities": [god]` and `"min_level"` (refused politely otherwise;
  no "!" for those who can't take it).
- Group walks: `World._go_grove` and the priest's realm walk take every
  groupmate within 30 m in the same zone along (each gets their own
  `grove_return`).
- `tools/world_layout.py`: `REALMS`; the realm zone file and its npcs and
  mobs written by one generator (`tools/zones/realm_dawnreach.py`), as the
  Grove's are.
- Tests: the line end to end (`dawn_line`), the group walk, refusing other
  gods' followers.
