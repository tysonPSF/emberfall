# Who does what

- **Repo:** github.com/tysonPSF/emberfall, **public**, default branch
  `main`. Anything committed is visible to the world — no secrets, no
  account hashes, no server data.
- **Tyson** designs and builds most features. **Nick** runs the live
  server (a Linux box he owns; players connect remotely) and co-develops.

## Decisions that are Nick's

**Instancing and the Greenmoor cave dungeon.** Behind the cave at
(-150, -30) Nick is building a quest dungeon that runs as an
**instance** (a copy per group). The server has no instancing yet:
`main.gd` keeps exactly one copy of each zone id in `_server_zones`.
Don't build the dungeon, its quest, or instancing unless Tyson asks, and
if your change touches zone loading or `_server_zones`, leave room for
Nick's design rather than picking one. *Tyson 2026-09-25.*

## The server only changes when Nick updates it

Merging to `main` changes nothing online. Nick pulls and restarts the
server (or the update timer does — see `docs/server-updates.md`). Until
then:

- anything the **rules** decide (new commands, combat changes, new
  zones' ground shape, anything in `World` on the server) is not live;
- a client built from newer `main` may not work against the older
  server at all — see [../net/protocol.md](../net/protocol.md).

So "it's merged" is not "it's live". Say which one you mean.

## Server-side files you must not commit

Accounts, characters, `guilds.json` and `admins.json` live in the
server's `--data` folder on Nick's machine, never in the repo.
`admins.json` (`["account", ...]`) is what makes `/grove` and other
test commands work online; it is re-read on each use, no restart.
