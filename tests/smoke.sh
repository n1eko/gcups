#!/bin/sh
# End-to-end smoke test for both images, run by CI and usable locally.
#
# Usage: tests/smoke.sh [gcups-image] [exporter-image]
#
# By default the app runs with the host's USB devices hidden, so it behaves
# as if no UPS were attached (even on a host with one plugged in). To test
# against a real UPS, set SMOKE_DEVICE=/dev/bus/usb/BBB/DDD (stop any other
# container using it first).
set -eu

GCUPS_IMAGE="${1:-gcups:test}"
EXPORTER_IMAGE="${2:-gcups-exporter:test}"
PASSWORD="Smoke12345"
NETWORK="gcups-smoke-$$"
GCUPS_PORT="${SMOKE_GCUPS_PORT:-18080}"
EXPORTER_PORT="${SMOKE_EXPORTER_PORT:-19199}"

cleanup() {
    status=$?
    if [ "$status" -ne 0 ]; then
        echo "--- gcups logs"; docker logs smoke-gcups 2>&1 | grep -v getCurrentParameters | tail -30 || true
        echo "--- exporter logs"; docker logs smoke-exporter 2>&1 | tail -20 || true
    fi
    docker rm -f smoke-gcups smoke-exporter >/dev/null 2>&1 || true
    docker network rm "$NETWORK" >/dev/null 2>&1 || true
    exit "$status"
}
trap cleanup EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }
pass() { echo "ok: $*"; }

wait_for_url() {
    for _ in $(seq 60); do
        curl -fs -o /dev/null "$1" && return 0
        sleep 1
    done
    fail "$1 did not respond within 60s"
}

login_status() {
    curl -s -o /dev/null -w '%{http_code}' -H 'Content-Type: application/json' \
        -d "{\"password\":\"$1\"}" "http://localhost:$GCUPS_PORT/api/login"
}

if [ -n "${SMOKE_DEVICE:-}" ]; then
    usb_option="--device=$SMOKE_DEVICE"
    expected_connected=1.0
else
    usb_option="--tmpfs=/sys/bus/usb/devices:ro"
    expected_connected=0.0
fi

docker network create "$NETWORK" >/dev/null

docker run -d --name smoke-gcups --network "$NETWORK" -p "$GCUPS_PORT:8080" \
    -e GCUPS_PASSWORD="$PASSWORD" "$usb_option" "$GCUPS_IMAGE" >/dev/null
wait_for_url "http://localhost:$GCUPS_PORT/"
pass "web UI is up"

[ "$(login_status "$PASSWORD")" = 201 ] || fail "login with GCUPS_PASSWORD was rejected"
pass "login with GCUPS_PASSWORD"
[ "$(login_status wrong-password)" = 403 ] || fail "login with a wrong password was accepted"
pass "wrong password rejected"

docker run -d --name smoke-exporter --network "$NETWORK" -p "$EXPORTER_PORT:9199" \
    -e GCUPS_URL=http://smoke-gcups:8080 -e GCUPS_PASSWORD="$PASSWORD" \
    "$EXPORTER_IMAGE" >/dev/null
wait_for_url "http://localhost:$EXPORTER_PORT/metrics"

metrics="$(curl -fsS "http://localhost:$EXPORTER_PORT/metrics" | grep '^gcups_')"
echo "$metrics"
echo "$metrics" | grep -qx 'gcups_up 1.0' || fail "exporter could not read the API"
echo "$metrics" | grep -qx "gcups_connected $expected_connected" \
    || fail "expected gcups_connected $expected_connected"
pass "exporter reads the API"

started=$(date +%s)
docker stop smoke-exporter smoke-gcups >/dev/null
[ $(( $(date +%s) - started )) -lt 5 ] || fail "containers ignored SIGTERM"
pass "containers stop on SIGTERM"
