#!/bin/sh
# Changes the gcups version everywhere it appears in the repository.
#
# Usage: scripts/set-gcups-version.sh <new-version>
set -eu

cd "$(dirname "$0")/.."

new="${1:?usage: $0 <new-version>}"
echo "$new" | grep -qxE '[0-9]+(\.[0-9]+)+' || { echo "invalid version: $new" >&2; exit 1; }

current="$(sed -nE 's/^ARG GCUPS_VERSION=//p' gcups/Dockerfile)"
[ -n "$current" ] || { echo "ARG GCUPS_VERSION not found in gcups/Dockerfile" >&2; exit 1; }
[ "$current" != "$new" ] || { echo "already at $new"; exit 0; }

# Escape the dots so 1.1.10 doesn't also match e.g. 1.1.1x0.
pattern="$(echo "$current" | sed 's/\./\\./g')"
for file in gcups/Dockerfile compose.yaml scripts/install-udev-rules.sh README.md; do
    sed -i "s/$pattern/$new/g" "$file"
done

echo "gcups version: $current -> $new"
