# Running autotests and nettests

Commands are in `CLAUDE.md` ("Verify changes"). These are the traps.

## Windowed runs: in the background, and they sometimes stall

Launch any test window with `open -g -n -a /Applications/Godot.app
--args --log-file <out.txt> --path <repo> -- --autotest --only=<x>`,
poll the log for `AUTOTEST DONE`, then `pkill -f "log-file <out.txt>"`.
**Never `--always-on-top`**: the person may be playing on the server in
another window, and a test that grabs focus hijacks their screen.
*Tyson 2026-09-27.*

A windowed run occasionally prints the engine banner and then nothing,
forever (seen 2026-09-26 with the display asleep, and once on
2026-09-28 with a play client open). Cause unconfirmed. Kill it and run
again. For anything that doesn't need screenshots, run headless
(`--headless`) instead — it doesn't stall. macOS has no `timeout`
command, so background the run and poll.

## Zone changes in a test are silently dropped mid-change

`main._on_zone_change` returns at once while `_changing_zone` is true.
Emit `World.zone_change` during another change (say, right after a walk
through a zone line) and nothing happens, no error — your test then
measures the wrong zone. Wait until `main._changing_zone` is false, and
check `main.zone.zone_id` before trusting anything. Border tests chain
their legs for the same reason: each leg starts in the zone the last
one ended in.

## A nettest client can't teleport itself

Nettests (`--nettest=<Name> --<mode>`) need a local dedicated server
(`--headless -- --server --port=<p> --zone=greenmoor --data=<dir>`).
The server snaps a client back if it moves further than it could run
(`Net._c_move`), so a test that sets its own `global_position` next to a
monster ends up where it started ("too far away"). Walk there with
`move_forward`, or import the character at the right spot (`"zone"`,
`"position"` in `Net.import_character`). Characters persist in the
server's `--data`, so use a fresh data dir per run.

Online test commands (`/grove`, …) need `<data>/admins.json` listing the
test account (lower-case), e.g. `["alpha"]`.

## Sped-up runs: count physics steps, not timers

Under `Engine.time_scale`, `get_tree().create_timer(x)` ends on the next
frame after `x` — so each wait overshoots by up to a frame of *scaled*
time, and the error grows with the speed and with CPU load. The balance
sim timed fights that way until 2026-09-29: its kill times read ~10%
short at 20x and ~45% short at 60x, and a pet's "1.5 s" head start
stretched when the machine was busy. Anything that measures or paces game
time in a sped-up run should await `physics_frame` and add
`time_scale / physics_ticks_per_second` per step (`balance_sim._sim_wait`).
