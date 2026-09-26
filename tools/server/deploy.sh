#!/bin/sh
# From a developer's machine: update the server now, without waiting for its timer.
#   EMBERFALL_SERVER=user@host tools/server/deploy.sh
# Needs your SSH key on the server (in the server user's ~/.ssh/authorized_keys).
# EMBERFALL_DIR (default: emberfall, in that user's home) is the server's checkout.
set -e
: "${EMBERFALL_SERVER:?set EMBERFALL_SERVER=user@host}"
DIR="${EMBERFALL_DIR:-emberfall}"
ssh "$EMBERFALL_SERVER" "cd $DIR && NOW=1 DATA=\${DATA:-\$HOME/emberfall-data} tools/server/auto_update.sh"
