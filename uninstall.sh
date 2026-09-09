#!/bin/bash
# Permanent Uninstall and Rollback Script for RobCo Greeter
# This script must be run as root or with sudo.

echo "=== RobCo Greeter Permanent Uninstaller ==="

if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Please run as root or with sudo."
    exit 1
fi

PROD_DIR="/usr/local/lib/robco-greeter"
ORIGINAL_DM_FILE="/etc/greetd/original_dm_target.txt"

echo "[1/9] Stopping greetd..."
if systemctl is-active --quiet greetd.service; then
    systemctl stop greetd.service || echo "Failed to stop greetd."
fi

echo "[2/9] Disabling greetd..."
systemctl disable greetd.service || echo "Failed to disable greetd."

echo "[3/9] Restoring original display-manager target..."
if [ -f "$ORIGINAL_DM_FILE" ]; then
    ORIGINAL_DM_TARGET=$(cat "$ORIGINAL_DM_FILE")
    if [ -n "$ORIGINAL_DM_TARGET" ]; then
        echo "Restoring display-manager.service to $ORIGINAL_DM_TARGET..."
        ln -sf "$ORIGINAL_DM_TARGET" /etc/systemd/system/display-manager.service
    else
        echo "WARNING: Original target file was empty."
    fi
else
    echo "WARNING: $ORIGINAL_DM_FILE not found. Cannot automatically restore original display manager symlink!"
fi

echo "[4/9] Cleaning up greetd configuration..."
if grep -q "robco-greeter" /etc/greetd/config.toml 2>/dev/null; then
    echo "Removing RobCo greetd configuration..."
    rm -f /etc/greetd/config.toml
fi

echo "[5/9] Reloading systemd..."
systemctl daemon-reload

echo "[6/9] Removing production RobCo installation..."
if [ -d "$PROD_DIR" ]; then
    rm -rf "$PROD_DIR"
    echo "Removed $PROD_DIR."
fi

echo "[7/9] Starting restored display manager..."
systemctl start display-manager.service || echo "Failed to start display-manager.service."

echo "[8/9] Verifying restored display manager..."
if systemctl is-active --quiet display-manager.service; then
    echo "[OK] Restored display manager is active."
else
    echo "[FAIL] Restored display manager failed to start!"
fi

echo "[9/9] Verifying greetd is inactive..."
if systemctl is-active --quiet greetd.service; then
    echo "[FAIL] greetd is STILL ACTIVE!"
else
    echo "[OK] greetd is inactive."
fi

echo "=========================================================="
echo "                 UNINSTALLATION COMPLETE                  "
echo "=========================================================="
echo "RobCo Greeter has been removed and the system restored."
echo "=========================================================="
