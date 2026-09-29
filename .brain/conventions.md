# Conventions — the non-negotiables

Read once per session. The architecture rules (World `request_*`,
`_remote`, `World.say`, content as data) are in `CLAUDE.md`; these are
the ones that aren't visible from the code at all.

## American English, everywhere

Identifiers, comments, player-facing text, NPC dialogue, docs, commit
messages. color, gray, armor, meter, center, canceled, toward, behavior.
"Dialogue" for NPC speech is fine; UI boxes are "dialogs".
*Tyson 2026-09-23: "everything we develop is made in America."* Fix
British spellings in passing when you touch old text.

## Our own names, never EverQuest's

EverQuest-style **mechanics** are the point; EverQuest **proper nouns**
are not allowed: no "froglok", no "Tagar's Insects", no EQ zone, god or
NPC names. Invent names in Emberfall's own theme (the five elephant
gods, the Emberlands, Dawnstair, Long Monsoon, Ashfall, Standing Sky,
Boneyard). Genre words (Kick, Root, Gate, Backstab, Feign Death) are fine.
*Tyson 2026-09-26.* 40 EQ-coined spell names were renamed 2026-09-27
(display names only — ids like `tagars_insects` stayed, so don't
"fix" the id to match). Some item and monster names still sound EQ
(gnoll pups, Rat Whiskers, Bone Chips, Cloth Cap) and were never reviewed.

## Test only what you changed

Run the autotest section(s) for the feature you touched, not the whole
playthrough — a full run takes minutes and replays everything. New
checks go in their own `_t_<name>` section. See
[testing/running-tests.md](testing/running-tests.md). *Tyson 2026-09-23.*

## Branch, and pull first

Nick commits too. Pull before starting; put anything bigger than a
one-line fix on a branch and merge when it's done. See
[workflow/team.md](workflow/team.md).
