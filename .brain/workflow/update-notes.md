# Commit messages and pull requests are the update notes

Nick's server updates (the roll-outs players and he see) are described from
what we push: the commit message (`tools/server/auto_update.sh` logs
`git log -1 --format='%h %s'`) and the pull request a branch was merged
through. A one-line subject with no body, or a branch merged locally with no
PR, leaves the update with nothing to say. Nick asked for fuller descriptions,
2026-10-03 (Tyson relaying).

## Every commit to main

- **Subject:** one line, under about 72 characters, saying what changed in
  plain words ("Stuns and roots now hold players").
- **Blank line, then a body** with these sections, each a few bullets in
  plain, player-facing words (no function names in the player part):
  - **What's new / what changed:** what a player will see or feel, one
    bullet per thing.
  - **For the server:** protocol bump (and that every client must update
    with it), new zones or data, anything to rerun or set up, anything
    that changes saves.
  - **Tested:** which autotest sections or nettests ran and what they
    showed; what wasn't tested (online, by hand).
- Then the co-author line.

Write the body with `git commit -F <file>` (or a heredoc) so the newlines
survive; `-m "..."` with one paragraph is what produced the bare one-liners.

## Branches go in through a pull request

Merge a branch with `gh pr create --base main --head <branch> --title
"<subject>" --body-file <notes>` and then `gh pr merge --merge`, not a local
`git merge`: the PR's description is where the fullest notes live. Use the
same sections as the commit body, and add screenshots' findings if any.

Small fixes committed straight to main still get the full body above.
