# Brain index — read this first, then only what you need

A routing table, not documentation. Find the row matching what you are
**about to do**, read the linked file(s), and stop. Do not pre-load the
tree. If no row matches, nothing here applies: go ahead, and add a note
afterwards if you learned something the hard way.

What each system is and how it fits together is in `CLAUDE.md`. This is
for what bites.

---

## ALWAYS — once per session

| File | Why |
|---|---|
| [conventions.md](conventions.md) | American English, our own names (never EverQuest's), test only what changed, branch and pull first |
| [workflow/team.md](workflow/team.md) | What's Nick's (instancing, the cave dungeon, the server), and why "merged" isn't "live" |

Everything below is conditional. Don't read it speculatively.

---

## BEFORE YOU TOUCH — triggered by action

### The wire (client ↔ server)

| About to… | Read |
|---|---|
| Add an `@rpc`, change an RPC's arguments, or add a key to `_send_self` / `apply_self` | [net/protocol.md](net/protocol.md) — **bump `PROTOCOL`**; a newer client silently breaks on an older server; at 22 since 2026-09-29 |
| Tell someone a feature works online, or plan a release | [workflow/team.md](workflow/team.md) — nothing is live until Nick updates the server |
| Touch zone loading, `_server_zones`, or anything per-group in zones | [workflow/team.md](workflow/team.md) — instancing is Nick's |

### Data and content

| About to… | Read |
|---|---|
| Edit `data/*.json` with a script (Python, `json.dump`) | [data/editing-json.md](data/editing-json.md) — 20 files don't survive a dump; you'd rewrite the whole file |
| Make a city a starting city, or change a race's `"home"` | [content/new-content.md](content/new-content.md) — it needs its own bag quest |
| Build or change a beginner zone, or plan a zone's terrain | [content/new-content.md](content/new-content.md) — ~20 calm level 1-5 monsters to share; avoid the stepped terraces |
| Add items, quest rewards, or a mob's gear | [content/new-content.md](content/new-content.md) — run `tools/item_curve.py`; gear must beat easier zones' |
| Name or restyle a god, or use Merrick | [content/new-content.md](content/new-content.md) — they're shared with Elephant Grove |
| Name anything new (monster, spell, item, place) | [conventions.md](conventions.md) — our own theme, no EverQuest proper nouns |

### World and zones

| About to… | Read |
|---|---|
| Edit a zone, or look for the script that made it | [world/zones.md](world/zones.md) — the generators were never committed (except The Grove's) |
| Open a sealed pass (swap a `rockslide` for a zone line) | [world/zones.md](world/zones.md) — it can leave a ridge; hold the ground with a signpost |
| Put something players must reach on a terrace | [world/zones.md](world/zones.md) — risers are too steep to climb; only roads ramp |

### Testing

| About to… | Read |
|---|---|
| Launch any test game window (autotest, lineup, nettest) | [testing/running-tests.md](testing/running-tests.md) — in the background, never on top; windowed runs can stall |
| Write a test that changes zones | [testing/running-tests.md](testing/running-tests.md) — a zone change mid-change is silently dropped |
| Speed up a test or sim with `Engine.time_scale`, or time anything in one | [testing/running-tests.md](testing/running-tests.md) — timers overshoot under time scale; count physics steps |
| Write a nettest that moves the player | [testing/running-tests.md](testing/running-tests.md) — the server snaps back a client that teleports itself |

### Debugging

| About to… | Read |
|---|---|
| Chase a stutter, hitch or low frame rate a player reports | [debugging/client-stutter.md](debugging/client-stutter.md) — the hitch logger branch, and why `TIME_PROCESS` misleads |
| Change physics rate or how the local player's model/camera move | [debugging/client-stutter.md](debugging/client-stutter.md) |

### Working with others

| About to… | Read |
|---|---|
| Hand work to a subagent that touches shared files (`models.json`, `npcs.json`, `CLAUDE.md`) | [workflow/collaborating.md](workflow/collaborating.md) — a subagent "restoring" a file wiped concurrent edits |
| Write something down (a plan, a note, a brain entry) | [workflow/collaborating.md](workflow/collaborating.md) — where it goes; most of it isn't committed |

---

## Adding to the brain

Add a file when you learn something another person would otherwise
lose an afternoon rediscovering: a constraint, a trap with a silent
failure, a decision that looks wrong without its reason. Then **add a
row above**, keyed on the action that should trigger reading it. Keep
files under a screen. Details: [workflow/collaborating.md](workflow/collaborating.md);
what the brain is and why: [README.md](README.md).
