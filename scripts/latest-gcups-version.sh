#!/bin/sh
# Prints the latest gcups version for Linux (e.g. 1.1.10).
#
# Green Cell publishes no version API that is kept up to date (release.json
# still lists 1.1.7), so this reads the version from the install instructions
# on the download page:  export GCUPS="gcups-<version>"
# The page's script bundle has a content-hashed name, so it is found first.
# The matching tarball is checked before the version is printed.
set -eu

SITE=https://gcups.greencell.global
TARBALL_URL=https://gcups-static.greencell.global/linux/x86_64

fail() { echo "latest-gcups-version: $*" >&2; exit 1; }

page="$(curl -fsSL --max-time 30 "$SITE/en")" || fail "cannot fetch $SITE/en"

bundles="$(printf '%s\n' "$page" | grep -oE 'src="\./js/[^"]+\.js"' | sed -E 's/^src="\.\/(.*)"$/\1/')"
[ -n "$bundles" ] || fail "no script bundle found on $SITE/en (page layout changed?)"

version=""
for bundle in $bundles; do
    version="$(curl -fsSL --max-time 30 "$SITE/$bundle" \
        | grep -oE 'export GCUPS=\\?"gcups-[0-9]+(\.[0-9]+)+' \
        | grep -oE '[0-9]+(\.[0-9]+)+$' \
        | sort -uV | tail -1)" || true
    [ -n "$version" ] && break
done
[ -n "$version" ] || fail "install instructions not found in $SITE (page layout changed?)"

curl -fsI --max-time 30 -o /dev/null "$TARBALL_URL/gcups-$version.tar.gz" \
    || fail "site lists $version but $TARBALL_URL/gcups-$version.tar.gz is not downloadable"

echo "$version"
