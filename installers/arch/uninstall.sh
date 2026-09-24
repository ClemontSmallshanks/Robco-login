#!/usr/bin/env bash
set -e

ROOT="${ROBCO_TEST_ROOT:-}"

if [ -z "$ROOT" ]; then
    if grep -iq fedora /etc/os-release 2>/dev/null; then
        echo "Arch Linux is required for native uninstallation."
        exit 1
    fi
fi

PROD_DIR="${ROOT}/usr/local/lib/robco-greeter"
GREETD_DIR="${ROOT}/etc/greetd"
SYSTEMD_DIR="${ROOT}/etc/systemd/system"

echo "Uninstalling from simulated root: $ROOT"

rm -rf "$PROD_DIR"
rm -f "${GREETD_DIR}/config.toml"

if [ -f "${GREETD_DIR}/original_dm_target.txt" ]; then
    ORIG=$(cat "${GREETD_DIR}/original_dm_target.txt")
    ln -sf "$ORIG" "${SYSTEMD_DIR}/display-manager.service"
    rm -f "${GREETD_DIR}/original_dm_target.txt"
else
    rm -f "${SYSTEMD_DIR}/display-manager.service"
fi

if [ -n "$ROOT" ]; then
    echo "[MOCK] would systemctl disable greetd.service"
    echo "[MOCK] would systemctl daemon-reload"
fi

echo "Uninstallation complete."
