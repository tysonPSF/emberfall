# Working alongside other agents and people

The brain is committed and edited by everyone. That is the point, and
also how it rots.

## Where things go — ask "who else needs this?"

| Kind of thing | Home | Committed? |
|---|---|---|
| Constraint / trap / decision an agent needs mid-task | `.brain/<area>/` + an INDEX row | yes |
| Architecture reference: what a system is and how it hangs together | `CLAUDE.md` | yes |
| A document a person reads deliberately (the world layout, the zone brief, server setup) | `docs/` | yes |
| Plans, task lists, run notes, in-flight state | your own Claude memory or an untracked scratch file | **no** |
| How a function works | nowhere — read the code | — |

The test is audience, not format: would someone else have to read this,
or redo the work without it? If not, it's personal.

## Before adding to the brain

The bar is "someone loses an afternoon without this." Most things fail
it, deliberately. Then **add the INDEX row**, keyed on the action that
should trigger reading it. A file nothing routes to is never opened.

Write for someone with the same problem in six months: the constraint,
what breaks if you ignore it (especially if it breaks **silently**), the
why if it isn't obvious, and a date and name ("Tyson 2026-09-28").

## When the brain is wrong

Fix it in place, in the commit that proved it wrong. If you're unsure,
say so in the file ("may no longer hold as of <date>: X behaved
differently") rather than deleting it.

## Parallel agents and shared files

Don't let two agents write the same file. For the brain that means add
a file rather than extend someone else's; `INDEX.md` is the exception,
and each edit should touch only its own row.

**The same goes for shared data files.** On 2026-09-28 a subagent told to
"leave `data/models.json` as you found it" restored its snapshot
byte-for-byte and silently wiped entries the lead agent had added in the
meantime. Give subagents their own files; have them *report* lines for
shared files (`models.json`, `npcs.json`, `CLAUDE.md`) and add those
yourself, after they finish.
