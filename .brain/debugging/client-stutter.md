# A player sees stutter or hitches

*Tyson 2026-09-28: a hitch every 2 s that Nick never saw took an
afternoon to find.* What would have saved it:

## Measure before guessing

Branch `stutter-log` (not on `main`) adds `--hitchlog`: launch a client
with `-- --hitchlog` and it logs every frame over 25 ms, the ping every
5 s, stalls per 10 s, window focus changes, and how long the server's
messages took. Merge it into a scratch branch with whatever you're
testing.

**`Performance.TIME_PROCESS` reports the previous frame.** Read it in
the frame after a stall and you see a normal number while the stall's
own work — including the multiplayer poll at the start of the frame —
is invisible. Time suspect code directly with `Time.get_ticks_usec()`.

## Ask where the game was started from

`scripts/dev/reloader.gd` (the "Update ready — press F9" notice) only
runs when the game is started from the project folder, not in tests
and not in an exported build. It scans ~1,600 files every 2 s; on the
main thread that was a 120 ms freeze (now on a worker thread). Any dev
convenience that runs in normal play but not in autotests is invisible
to every test — suspect those first when a player sees something tests
don't. A regular period (exactly 2.0 s) points at a timer, not the
network or the GPU.

## 120 Hz screens

Physics runs at 60 Hz. The local player's model and camera are drawn
between physics steps (`Player._smooth_motion`), so running is smooth on
a 120 Hz Mac. Running physics at 120 Hz instead was tried and cost
about 25% of the frame rate — don't.
