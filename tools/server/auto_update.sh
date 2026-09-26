#!/bin/sh
# Brings the server up to date with GitHub's main, when there is something new.
# Run by emberfall-update.timer every few minutes (or by hand, or by deploy.sh).
#   DATA=/path/to/data NOW=1 tools/server/auto_update.sh
# It warns everyone online (a "restart_notice" file the server watches), waits
# a minute (not with NOW=1), pulls, then asks the server to save and restart
# ("restart_now"); systemd (Restart=always) starts it again on the new code.
set -e
cd "$(dirname "$0")/../.."
DATA="${DATA:-$HOME/emberfall-data}"
WAIT=60
[ -n "$NOW" ] && WAIT=10
git fetch -q origin main
if [ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ]; then
	[ -n "$NOW" ] && echo "Already up to date: $(git log -1 --format='%h %s')"
	exit 0
fi
echo "Updating to $(git log -1 --format='%h %s' origin/main)"
echo "$WAIT" > "$DATA/restart_notice"
sleep "$WAIT"
git merge -q --ff-only origin/main
touch "$DATA/restart_now"
echo "Pulled; the server restarts in a few seconds."
