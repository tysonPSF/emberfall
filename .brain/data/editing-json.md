# Editing `data/*.json` with a script

Many edits here are made by Python one-offs (adding NPCs, spells, zone
entries). The trap: **not every file survives a load-and-dump.**

Checked 2026-09-29: 63 data files come back byte-identical from
`json.dumps(d, indent=2) + "\n"`; these 20 do **not** — they're
hand-formatted (one entry per line, arrays kept on one line):

`models.json`, `spells.json`, `config.json`, `loot.json`; items
`armor`, `weapons`, `rewards`, `containers`, `monsoon`, `tradeskills`,
`jewelry`, `drops`, `lanternhold`; zones `greenmoor`, `thornwood`,
`harrowfield`, `hollowmere`, `sunward_steps`, `the_bleach`,
`weeping_throat`.

Dumping one of those rewrites the whole file: a diff of thousands of
lines for a one-entry change, and a merge conflict with anyone else who
touched it. Nothing fails — you only find out in review, or when Nick
can't merge.

**How to edit them:** splice text in (insert the new entry after a
known anchor line, then `json.loads` the result to prove it still
parses), or use the Edit tool. Before dumping any other file, check it
round-trips first. `models.json` in particular: add lines beside a
neighbor entry, one entry per line, like the rest of the file.

Remember JSON numbers load as floats in GDScript — cast with `int()`
(also in `CLAUDE.md`).
