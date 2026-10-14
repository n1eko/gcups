#!/bin/sh
# Installs the GC UPS udev rules on the HOST, so the UPS device nodes are
# readable by the unprivileged user inside the container.
#
# The rules are copied out of the image, where the official install.sh wrote
# them, so they always match the bundled gcups version.
#
# Usage: sudo ./install-udev-rules.sh [image]
set -eu

IMAGE="${1:-ghcr.io/n1eko/gcups:1.1.10}"
RULES_DIR=/etc/udev/rules.d

if [ "$(id -u)" -ne 0 ]; then
    echo "Run as root: sudo $0 $*" >&2
    exit 1
fi

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

container="$(docker create "$IMAGE")"
docker cp "$container:$RULES_DIR/." "$tmp/"
docker rm "$container" >/dev/null

for rule in "$tmp"/*gcups*.rules; do
    [ -e "$rule" ] || { echo "No gcups rules found in $IMAGE" >&2; exit 1; }
    install -m 644 "$rule" "$RULES_DIR/"
    echo "Installed $RULES_DIR/$(basename "$rule")"
done

udevadm control --reload-rules
udevadm trigger
echo "udev rules reloaded. Re-plug the UPS if it was already connected."
