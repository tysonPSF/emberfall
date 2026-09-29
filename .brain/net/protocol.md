# Changing what client and server say to each other

## Client and server must run the same `main`

There is no compatibility layer. Two ways a mismatch fails:

- **New client, old server:** `Player.apply_self` copies every listed
  key with `d[key]` (strict). Add a key to `Net._send_self` and to that
  list, and a newer client talking to an older server errors on **every**
  self update (five a second) — the HUD stops updating, nothing says why.
- **New RPC or changed arguments:** Godot drops or errors on RPCs whose
  signature the other side doesn't have. Changed argument lists (e.g.
  `_c_create_character` gained `gender` and `hair` with defaults) can
  seem to work until someone uses the new path.

## Bump `PROTOCOL` when a message changes

`Net.PROTOCOL` (scripts/autoload/net.gd) is checked at login; a mismatch
turns the client away with a clear message instead of the silent
breakage above. That is its whole job.

It went from 16 to 18 on 2026-09-29 (quest sharing's `quest_offered`
signal); 17 is taken by the `alignment` branch, so whichever of them is
merged second must bump again. Before that it sat at 16 through player
trading, emotes, the Grove, guilds and the swing timer, so clients older
than those got no warning against a newer server.

Checklist when you touch the wire: new `@rpc` func, new/changed RPC
arguments, a new key in `_send_self` / `apply_self`, a new `_s_ui`
signal the client must handle → bump `PROTOCOL`, and tell Nick the
server and every client must update together.
