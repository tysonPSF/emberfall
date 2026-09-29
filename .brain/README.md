# `.brain` — shared codebase memory

A committed knowledge base for the people and AI agents working on
Emberfall (Tyson and Nick, mostly through Claude Code). It holds the
constraints, traps and decisions you **cannot** see by reading the code,
so the next person starts where the last one finished instead of
rediscovering them.

**Start at [INDEX.md](INDEX.md).** It is a routing table: find the row
for what you are about to do, read those files, stop. Do not load the
whole tree.

## Why it exists

Until 2026-09-29 this knowledge lived in two places: a per-machine
Claude memory store only Tyson's sessions could see, and `CLAUDE.md`,
which every session loads in full. The first is invisible to Nick; the
second costs every session its whole length whether the task needs it
or not. The brain is the middle: shared, but loaded only on demand.

## What belongs here

Things someone would otherwise **lose an afternoon** rediscovering:

- non-obvious constraints ("bump PROTOCOL when a message changes")
- traps that fail **silently** or confusingly
- decisions that look wrong without their reason, dated and attributed

## What does not

- **How code works.** Read the code; a copy here drifts.
- **Feature inventories** ("zones so far…"). The data files are the truth.
- **Personal state**: task lists, plans, what you did today. Those stay
  in your own Claude memory or an untracked scratch file.

## Structure

```
.brain/
  INDEX.md        ← routing table; read first
  conventions.md  ← always-read: the non-negotiables
  workflow/       ← how Tyson, Nick and their agents work together
  net/            ← client/server versions and the wire
  data/           ← editing data/*.json safely
  world/          ← zones and the world grid
  content/        ← rules for new cities, names, deities
  testing/        ← running autotests and nettests
  debugging/      ← diagnosing problems that don't show in the code
```

`CLAUDE.md` at the root still holds the architecture reference (what
each system is and how it hangs together). The brain is for what bites.

When an entry turns out wrong, fix it in place, in the same commit as
whatever proved it wrong. A confident wrong entry is worse than none.
