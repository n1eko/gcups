#!/bin/sh
set -eu

# Both the settings script and the app run on Electron's bundled Node runtime;
# the app is started in its headless "service" context, so no X server is needed.
export ELECTRON_RUN_AS_NODE=1

cd "$GCUPS_HOME"

# The service writes pid files and sockets here; /run may be a fresh tmpfs.
mkdir -p /run/gcups

./gcups /opt/gcups-container/configure-api.js

exec ./gcups resources/app.asar --context=service "$@"
