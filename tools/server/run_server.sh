#!/bin/sh
# Runs the Emberfall dedicated server from a checkout of the repo.
#   GODOT=/path/to/godot PORT=7777 tools/server/run_server.sh
# Pull first to update; players need the same version as the server.
set -e
cd "$(dirname "$0")/../.."
GODOT="${GODOT:-godot}"
PORT="${PORT:-7777}"
"$GODOT" --headless --path . --import          # imports new or changed art (quick when nothing changed)
exec "$GODOT" --headless --path . -- --server --port="$PORT"
