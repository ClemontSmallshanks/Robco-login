#!/bin/bash
# Strict Controlled Test Harness for Greetd Integration
# This test is isolated and reversible.

echo "=== RobCo Greeter Controlled Test Harness ==="

# Global state variables for cleanup
PLM_STOPPED=0
GREETD_CONFIG_BACKUP=""
ORIGINAL_DM_TARGET=""
CREATED_PROD_DIR=0
PROD_DIR="/usr/local/lib/robco-greeter"

cleanup() {
    echo ""
    echo "=========================================================="
    echo "                  STARTING CLEANUP                        "
    echo "=========================================================="
    
    # 1. Stop greetd if running
    if systemctl is-active --quiet greetd.service; then
        echo "Stopping greetd.service..."
        sudo systemctl stop greetd.service || echo "Failed to stop greetd."
    fi
    
    # 2. Restore Greetd configuration
    if [ -n "$GREETD_CONFIG_BACKUP" ] && [ -f "$GREETD_CONFIG_BACKUP" ]; then
        if grep -q "NO_ORIGINAL" "$GREETD_CONFIG_BACKUP"; then
            echo "Removing temporary greetd config..."
            sudo rm -f /etc/greetd/config.toml || echo "Failed to remove temp config."
        else
            echo "Restoring original greetd config from $GREETD_CONFIG_BACKUP..."
            sudo mv "$GREETD_CONFIG_BACKUP" /etc/greetd/config.toml || echo "Failed to restore config."
        fi
    fi
    
    # 3. Restore PLM
    if [ "$PLM_STOPPED" -eq 1 ]; then
        echo "Restarting PLM..."
        sudo systemctl start display-manager.service || echo "Failed to start display-manager.service."
    fi

    # 4. Remove production directory ONLY if we created it
    if [ "$CREATED_PROD_DIR" -eq 1 ]; then
        echo "Removing temporary production directory $PROD_DIR..."
        if ! sudo rm -rf "$PROD_DIR"; then
            echo "ERROR: Failed to remove $PROD_DIR."
            FAIL_FLAG=1
        fi
    fi

    # 5. Verification Check
    echo ""
    echo "=== FINAL SAFETY VERIFICATION ==="
    
    # Check greetd
    if systemctl is-active --quiet greetd.service; then
        echo "[FAIL] greetd is STILL ACTIVE!"
        FAIL_FLAG=1
    else
        echo "[OK] greetd is inactive."
    fi
    
    # Check PLM
    if systemctl is-active --quiet display-manager.service; then
        echo "[OK] PLM is active."
    else
        echo "[FAIL] PLM failed to activate!"
        FAIL_FLAG=1
    fi
    
    # Check symlink
    CURRENT_DM_TARGET=$(readlink -f /etc/systemd/system/display-manager.service || echo "NONE")
    if [ "$CURRENT_DM_TARGET" = "$ORIGINAL_DM_TARGET" ]; then
        echo "[OK] display-manager.service target is unchanged."
    else
        echo "[FAIL] display-manager.service target CHANGED! ($CURRENT_DM_TARGET)"
        FAIL_FLAG=1
    fi

    # Check directory
    if [ "$CREATED_PROD_DIR" -eq 1 ] && [ -d "$PROD_DIR" ]; then
        echo "[FAIL] Temporary production directory was not removed!"
        FAIL_FLAG=1
    else
        echo "[OK] Temporary production directory state restored."
    fi
    
    # Output manual recovery commands if any failure
    if [ -n "$FAIL_FLAG" ]; then
        echo "=========================================================="
        echo "CRITICAL WARNING: Cleanup encountered an error."
        echo "Execute the following commands to manually recover your system:"
        echo "  sudo systemctl stop greetd.service"
        if [ -n "$ORIGINAL_DM_TARGET" ]; then
            echo "  sudo ln -sf $ORIGINAL_DM_TARGET /etc/systemd/system/display-manager.service"
        fi
        echo "  sudo systemctl start display-manager.service"
        if [ "$CREATED_PROD_DIR" -eq 1 ] && [ -d "$PROD_DIR" ]; then
            echo "  sudo rm -rf $PROD_DIR"
        fi
        echo "=========================================================="
    else
        echo "System successfully restored to its original state."
    fi
    
    echo "Test harness finished."
}

trap cleanup EXIT INT TERM

echo "[1/10] Recording current display-manager state..."
ORIGINAL_DM_TARGET=$(readlink -f /etc/systemd/system/display-manager.service || echo "")
if [ -z "$ORIGINAL_DM_TARGET" ] || [[ ! "$ORIGINAL_DM_TARGET" == *plasmalogin.service* ]]; then
    echo "ERROR: display-manager.service does not point to plasmalogin. Target is: $ORIGINAL_DM_TARGET"
    exit 1
fi
echo "Original DM Target recorded: $ORIGINAL_DM_TARGET"

echo "[2/10] Verifying prerequisites..."
if ! id greetd >/dev/null 2>&1; then
    echo "ERROR: 'greetd' user does not exist."
    exit 1
fi
if ! systemctl list-unit-files greetd.service >/dev/null 2>&1; then
    echo "ERROR: greetd.service is not installed."
    exit 1
fi
if ! command -v cage >/dev/null 2>&1; then
    echo "ERROR: cage compositor is not installed."
    exit 1
fi
if [ ! -f /etc/pam.d/greetd ]; then
    echo "ERROR: /etc/pam.d/greetd does not exist. PAM configuration is missing."
    exit 1
fi
echo "Prerequisites met."

echo "[3/10] Deploying production files and dedicated venv..."
DEV_DIR="$(pwd)"

if [ -d "$PROD_DIR" ]; then
    echo "ERROR: $PROD_DIR already exists! Aborting to prevent overwriting existing data."
    exit 1
fi

sudo mkdir -p "$PROD_DIR"
CREATED_PROD_DIR=1

# Copy files
sudo cp -a "$DEV_DIR/." "$PROD_DIR/"

# Create venv and install dependencies
echo "Creating virtual environment in $PROD_DIR/venv..."
sudo python3 -m venv "$PROD_DIR/venv"
echo "Installing dependencies..."
sudo "$PROD_DIR/venv/bin/pip" install -q -r "$PROD_DIR/requirements.txt"
# Record exactly what versions were resolved from PyPI
sudo "$PROD_DIR/venv/bin/pip" freeze | sudo tee "$PROD_DIR/installed_versions.txt" >/dev/null

# Apply strictly scoped permissions
sudo chown -R root:root "$PROD_DIR"
# Dirs to 755
sudo find "$PROD_DIR" -type d -exec chmod 755 {} \;
# Executable files (like venv/bin/*) to 755
sudo find "$PROD_DIR" -type f -executable -exec chmod 755 {} \;
# Non-executable files to 644
sudo find "$PROD_DIR" -type f ! -executable -exec chmod 644 {} \;
# ELF/shared-library files must be explicitly 755
sudo find "$PROD_DIR" -type f -name "*.so" -exec chmod 755 {} \;
sudo find "$PROD_DIR" -type f -name "*.so.*" -exec chmod 755 {} \;

# Fix SELinux contexts for the deployment directory
echo "Relabeling SELinux contexts for $PROD_DIR..."
sudo restorecon -Rv "$PROD_DIR" >/dev/null

echo "Verifying shared library permissions as 'greetd'..."
sudo -u greetd bash -c "
echo 'Checking QtWidgets.abi3.so permissions:'
find $PROD_DIR/venv -name 'QtWidgets.abi3.so' -exec ls -l {} \;
echo 'Checking libqwayland-generic.so permissions:'
find $PROD_DIR/venv -name 'libqwayland-generic.so' -exec ls -l {} \;

echo 'Verifying QtWidgets import after permission lockdown...'
cd $PROD_DIR && venv/bin/python3 -c 'import PyQt6.QtWidgets' || { echo 'ERROR: PyQt6.QtWidgets import failed!'; exit 1; }
echo 'PyQt6.QtWidgets imported successfully!'
" || exit 1

echo "[3b/10] Running Isolated Qt Wayland Plugin Load Test..."
sudo -u greetd bash -c "cd $PROD_DIR && \
export QT_QPA_PLATFORM=wayland && \
export QT_DEBUG_PLUGINS=1 && \
echo '--- Isolated Qt Wayland Plugin Load Test ---' > qt_wayland_diag.log && \
timeout 10 venv/bin/python3 -c '
import sys
from PyQt6.QtWidgets import QApplication
app = QApplication(sys.argv)
print(\"QApplication initialized successfully\")
' >> qt_wayland_diag.log 2>&1
APP_EXIT_CODE=\$?

if [ \$APP_EXIT_CODE -eq 124 ]; then
    echo 'Wayland load test reached 10-second timeout (expected if waiting indefinitely for display)' >> qt_wayland_diag.log
elif [ \$APP_EXIT_CODE -eq 0 ]; then
    echo 'QApplication initialized successfully (exit code 0)' >> qt_wayland_diag.log
else
    echo \"QApplication failed to initialize (exit code \$APP_EXIT_CODE)\" >> qt_wayland_diag.log
fi

echo \"\"
echo \"=== WAYLAND PLUGIN DIAGNOSTIC LOG ===\"
cat qt_wayland_diag.log
echo \"=====================================\"

if grep -q \"not found\" qt_wayland_diag.log || grep -q \"Cannot load library\" qt_wayland_diag.log; then
    echo \"ERROR: Missing shared libraries detected in Wayland plugin load test!\"
    exit 1
fi
" || { echo "ERROR: Wayland plugin load test failed due to missing libraries."; exit 1; }

echo "[4/10] Backing up and configuring greetd..."
sudo mkdir -p /etc/greetd
GREETD_CONFIG_BACKUP=$(mktemp)
if [ -f /etc/greetd/config.toml ]; then
    sudo cp /etc/greetd/config.toml "$GREETD_CONFIG_BACKUP"
else
    echo "NO_ORIGINAL" > "$GREETD_CONFIG_BACKUP"
fi

cat <<EOF | sudo tee /etc/greetd/config.toml >/dev/null
[terminal]
vt = 1

[default_session]
command = "cage -s -- bash -c 'cd /usr/local/lib/robco-greeter && venv/bin/python3 -m app.main'"
user = "greetd"
EOF

echo "[5/10] Running Deep Qt Wayland Diagnostics as 'greetd' user..."
# Run diagnostic script using the unprivileged greetd user and the venv interpreter
sudo -u greetd bash -c "cd $PROD_DIR && \
export QT_DEBUG_PLUGINS=1 && \
export QT_QPA_PLATFORM=wayland && \
echo '--- Python & PyQt Versions ---' > qt_diag.log && \
venv/bin/python3 -c '
import sys
import PyQt6.QtCore as QtCore
import os
print(f\"Interpreter Path: {sys.executable}\")
print(f\"Python Version: {sys.version.split()[0]}\")
print(f\"PyQt6 Version: {QtCore.PYQT_VERSION_STR}\")
print(f\"Qt Version: {QtCore.QT_VERSION_STR}\")
pyqt_dir = os.path.dirname(QtCore.__file__)
print(f\"PyQt6 Directory: {pyqt_dir}\")
' >> qt_diag.log 2>&1

echo '--- Locating Qt Plugins ---' >> qt_diag.log
PLUGIN_DIR=\$(venv/bin/python3 -c 'import os, PyQt6.QtCore as c; print(os.path.join(os.path.dirname(c.__file__), \"Qt6\", \"plugins\", \"platforms\"))')
echo \"Plugin directory: \$PLUGIN_DIR\" >> qt_diag.log

echo '--- LDD Output for Platform Plugins ---' >> qt_diag.log
if [ -d \"\$PLUGIN_DIR\" ]; then
    for p in \"\$PLUGIN_DIR\"/*.so; do
        echo \"Plugin: \$p\" >> qt_diag.log
        ldd \"\$p\" >> qt_diag.log 2>&1 || true
    done
else
    echo \"WARNING: Plugin directory not found!\" >> qt_diag.log
fi

echo '--- Testing Explicit Wayland Plugin Load ---' >> qt_diag.log
# Time-bounded QPA plugin initialization test
timeout 10 venv/bin/python3 -c '
import sys
from PyQt6.QtWidgets import QApplication
app = QApplication(sys.argv)
print(\"QApplication initialized successfully\")
' >> qt_diag.log 2>&1
APP_EXIT_CODE=\$?

if [ \$APP_EXIT_CODE -eq 124 ]; then
    echo 'Wayland load test reached 10-second timeout (expected if waiting indefinitely for display)' >> qt_diag.log
elif [ \$APP_EXIT_CODE -eq 0 ]; then
    echo 'QApplication initialized successfully (exit code 0)' >> qt_diag.log
else
    echo \"QApplication failed to initialize (exit code \$APP_EXIT_CODE)\" >> qt_diag.log
fi

echo \"\"
echo \"=== COMPLETE DIAGNOSTIC LOG ===\"
cat qt_diag.log
echo \"===============================\"

# Check for missing shared libraries
if grep -q \"not found\" qt_diag.log || grep -q \"Cannot load library\" qt_diag.log; then
    echo \"ERROR: Missing shared libraries detected in Qt plugins or ldd output!\"
    exit 1
fi
" || { echo "ERROR: Qt Diagnostic detected missing libraries or failed."; exit 1; }

echo "=========================================================="
echo "                   STAGING COMPLETE                       "
echo "=========================================================="
echo "The system is ready for the controlled graphical test."
echo "This test is isolated and reversible."
echo "=========================================================="

echo "[6/10] Stopping PLM and starting greetd..."
if sudo systemctl stop display-manager.service; then
    PLM_STOPPED=1
else
    echo "ERROR: Failed to stop display-manager.service."
    exit 1
fi

sudo systemctl start greetd.service

# Verify greetd is active immediately
if ! sudo systemctl is-active --quiet greetd.service; then
    echo "ERROR: greetd failed to remain active."
    sudo journalctl -u greetd.service -n 100 --no-pager
    exit 1
fi

# Print additional diagnostics
systemctl status greetd.service --no-pager
sudo journalctl -u greetd.service -n 50 --no-pager

echo ""
echo "TEST IS RUNNING ON TTY1."
echo "Switch to TTY1 using Ctrl+Alt+F1."
echo "Interact with the RobCo graphical login."
echo "When finished, return to TTY3 using Ctrl+Alt+F3."
echo "Press ENTER here to begin cleanup."
echo ""
read -p "Return to TTY3 and press ENTER when testing is complete..."

echo "[7/10] Capturing logs for greetd..."
sudo journalctl -b 0 -u greetd.service --no-pager > greetd-test-session.log
echo "Logs saved to: greetd-test-session.log"

# Cleanup will handle restoration
