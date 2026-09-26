# Updating the server remotely

**For Nick.** Tyson wants the server to stay current without either of you
logging in to update it. Two parts, both optional and independent. Each is a
one-time setup on the server box, about 10 minutes in all.

## 1. The server updates itself (recommended)

A systemd timer checks GitHub's `main` every 5 minutes. When there is a new
commit it:

1. Warns everyone online in game: *"The server will restart in 60 seconds for
   an update. You can log right back in afterward."*
2. Waits a minute, then pulls. It uses `git merge --ff-only`, so a checkout
   with local changes is left alone and the run fails loudly.
3. Drops a `restart_now` file in the data folder. The server saves everyone
   and exits with code 3, and systemd starts it again on the new code.

No sudo is involved after setup: the game restarts itself. So **merging to
`main` is deploying**, and whatever lands on main is live within about 6
minutes.

Setup, assuming the server already runs from `tools/server/emberfall.service`:

```sh
cd ~/emberfall && git pull          # brings the new files and the updated unit
# If your paths differ from /home/emberfall/..., edit User, WorkingDirectory
# and DATA in all three unit files first.
sudo cp tools/server/emberfall.service tools/server/emberfall-update.service \
        tools/server/emberfall-update.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart emberfall                        # picks up Restart=always
sudo systemctl enable --now emberfall-update.timer
```

To check it:

- `systemctl list-timers emberfall-update` shows the next run.
- `journalctl -u emberfall-update` shows what each run did. A run with
  nothing new says nothing.
- `journalctl -u emberfall -f` is the game server's log. After an update you
  will see `Restarting for an update`, then it starting up again.

`emberfall.service` changed from `Restart=on-failure` to `Restart=always`.
That change is what brings the server back after it quits for an update.

## 2. SSH, so a developer can update or look at logs on demand

Add Tyson's public key, and your own if you like, to the server user's
`~/.ssh/authorized_keys`. Tyson can send his key: on his Mac it is the output
of `cat ~/.ssh/id_ed25519.pub`. If he has none yet, `ssh-keygen -t ed25519`
makes one.

Then, from either of your machines:

```sh
EMBERFALL_SERVER=emberfall@your.server.address tools/server/deploy.sh
```

This updates immediately, with a 10-second in-game warning instead of 60. It
does the same thing the timer does, just now. Tyson's Claude can also run it,
or read `journalctl` over SSH, when something needs checking.

## What to send back to Tyson

- Whether the timer is on.
- The address and user for SSH, if you did part 2.

## Rolling back

Revert the bad commit on `main` and push. The next timer run deploys the
revert.

For an emergency stop:

```sh
sudo systemctl stop emberfall-update.timer
cd ~/emberfall && git checkout <good-commit> && sudo systemctl restart emberfall
```

Later, `git checkout main` and start the timer again.
