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

It went unbumped at 16 from 2026-09-26 through several wire changes
(trading, emotes, the Grove, guilds, the swing timer). On 2026-09-29 two
branches bumped it at once (the Blackwater to 17, quest sharing to 18);
the Blackwater merged second and took **19**. When two branches both
touch the wire, the one merged last bumps past the other. 20: deleting
a character (`_c_delete_character`).

Checklist when you touch the wire: new `@rpc` func, new/changed RPC
arguments, a new key in `_send_self` / `apply_self`, a new `_s_ui`
signal the client must handle → bump `PROTOCOL`, and tell Nick the
server and every client must update together.
