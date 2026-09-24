#!/usr/bin/env bash
set -e

ROOT="${ROBCO_TEST_ROOT:-}"

if [ -z "$ROOT" ]; then
    if grep -iq fedora /etc/os-release 2>/dev/null; then
        echo "Kubuntu is required for native uninstallation."
        exit 1
    fi
fi

PROD_DIR="${ROOT}/usr/local/lib/robco-greeter"
SDDM_CONF_DIR="${ROOT}/etc/sddm.conf.d"
SYSTEMD_DIR="${ROOT}/etc/systemd/system"
WAYLAND_SESSIONS="${ROOT}/usr/share/wayland-sessions"

echo "Uninstalling from simulated root: $ROOT"

rm -rf "$PROD_DIR"
rm -f "${SDDM_CONF_DIR}/10-robco.conf"
rm -f "${WAYLAND_SESSIONS}/robco-wayland.desktop"

if [ -n "$ROOT" ]; then
    echo "[MOCK] would restore original SDDM config if modified"
    echo "[MOCK] would systemctl daemon-reload"
fi

echo "Uninstallation complete."
