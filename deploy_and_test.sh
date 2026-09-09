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
        echo "Restarting original display manager..."
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
    
    # 4.5. Clean up diagnostic log
    if [ -f "/tmp/robco-greeter-qt-diag.log" ]; then
        echo "Removing temporary diagnostic log..."
        sudo rm -f "/tmp/robco-greeter-qt-diag.log"
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
        echo "[OK] Original display manager is active."
    else
        echo "[FAIL] Original display manager failed to activate!"
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
if [ -z "$ORIGINAL_DM_TARGET" ]; then
    echo "ERROR: display-manager.service is not configured."
    exit 1
fi
echo "Original DM Target recorded: $ORIGINAL_DM_TARGET"

echo "[2/10] Verifying prerequisites..."
if ! systemctl is-active --quiet display-manager.service; then
    echo "ERROR: Existing display manager is NOT active. We only test when it is running."
    exit 1
fi
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

DEV_DIR="$(pwd)"
if [ ! -f "$DEV_DIR/app/main.py" ]; then
    echo "ERROR: Application repository incomplete (app/main.py missing)."
    exit 1
fi
if [ ! -f "$DEV_DIR/requirements.txt" ]; then
    echo "ERROR: requirements.txt missing."
    exit 1
fi
echo "Prerequisites met."

echo "[3/10] Deploying production files and dedicated venv..."
if [ -d "$PROD_DIR" ]; then
    echo "ERROR: $PROD_DIR already exists! Aborting to prevent overwriting existing data."
    exit 1
fi

sudo mkdir -p "$PROD_DIR"
CREATED_PROD_DIR=1

sudo cp -a "$DEV_DIR/." "$PROD_DIR/"

# Disable development settings in config.toml for production realism
if [ -f "$PROD_DIR/config.toml" ]; then
    sudo sed -i 's/mock_auth = true/mock_auth = false/g' "$PROD_DIR/config.toml"
    sudo sed -i 's/development_mode = true/development_mode = false/g' "$PROD_DIR/config.toml"
fi

if [ ! -f "$PROD_DIR/app/main.py" ]; then
    echo "ERROR: Production entry point failed to copy."
    exit 1
fi

echo "Creating virtual environment in $PROD_DIR/venv..."
sudo python3 -m venv "$PROD_DIR/venv"
echo "Installing dependencies..."
sudo "$PROD_DIR/venv/bin/pip" install -q -r "$PROD_DIR/requirements.txt"
sudo "$PROD_DIR/venv/bin/pip" freeze | sudo tee "$PROD_DIR/installed_versions.txt" >/dev/null

# Apply strictly scoped permissions
sudo chown -R root:root "$PROD_DIR"
sudo find "$PROD_DIR" -type d -exec chmod 755 {} \;
sudo find "$PROD_DIR" -type f -executable -exec chmod 755 {} \;
sudo find "$PROD_DIR" -type f ! -executable -exec chmod 644 {} \;
sudo find "$PROD_DIR" -type f -name "*.so" -exec chmod 755 {} \;
sudo find "$PROD_DIR" -type f -name "*.so.*" -exec chmod 755 {} \;

# Fix SELinux contexts
sudo restorecon -Rv "$PROD_DIR" >/dev/null

echo "Verifying shared library permissions and imports as 'greetd'..."
sudo -u greetd bash -c "
cd $PROD_DIR && venv/bin/python3 -c 'import PyQt6.QtWidgets' || { echo 'ERROR: PyQt6.QtWidgets import failed!'; exit 1; }
" || exit 1

echo "[3b/10] Verifying noexec constraints..."
# Test execution of the python binary to ensure noexec is not set on /usr/local/lib
if ! sudo -u greetd "$PROD_DIR/venv/bin/python3" --version >/dev/null 2>&1; then
    echo "ERROR: Cannot execute python in $PROD_DIR. Check if partition is mounted with noexec."
    exit 1
fi

echo "[4/10] Running Isolated Qt Wayland Plugin Load Test as 'greetd' user..."
sudo -u greetd bash -c "cd $PROD_DIR && \
export QT_QPA_PLATFORM=wayland && \
export QT_DEBUG_PLUGINS=1 && \
DIAG_LOG='/tmp/robco-greeter-qt-diag.log' && \
echo '--- Isolated Qt Wayland Plugin Load Test ---' > \$DIAG_LOG && \
timeout 10 venv/bin/python3 -c '
import sys
from PyQt6.QtWidgets import QApplication
app = QApplication(sys.argv)
print(\"QApplication initialized successfully\")
' >> \$DIAG_LOG 2>&1
APP_EXIT_CODE=\$?

if [ \$APP_EXIT_CODE -eq 124 ]; then
    echo 'Wayland load test reached 10-second timeout (expected if waiting indefinitely for display)' >> \$DIAG_LOG
elif [ \$APP_EXIT_CODE -eq 0 ]; then
    echo 'QApplication initialized successfully (exit code 0)' >> \$DIAG_LOG
else
    echo \"QApplication failed to initialize (exit code \$APP_EXIT_CODE)\" >> \$DIAG_LOG
    # It is expected to abort (exit code 134) when there is no Wayland display active.
    # We only care if it failed due to missing shared libraries.
fi

if grep -q \"not found\" \$DIAG_LOG || grep -q \"Cannot load library\" \$DIAG_LOG; then
    echo \"ERROR: Missing shared libraries detected in Wayland plugin load test!\"
    cat \$DIAG_LOG
    exit 1
fi
" || { echo "ERROR: Wayland plugin load test failed."; exit 1; }

echo "[5/10] Backing up and configuring greetd..."
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
command = "cage -s -- bash -c 'cd /usr/local/lib/robco-greeter && export PYTHONUNBUFFERED=1 && venv/bin/python3 -m app.main >> /tmp/robco-greeter.log 2>&1'"
user = "greetd"
EOF

echo "=========================================================="
echo "                   STAGING COMPLETE                       "
echo "=========================================================="
echo "The system is ready for the controlled graphical test."
echo "=========================================================="

echo "[6/10] Stopping original display manager and starting greetd..."
if sudo systemctl stop display-manager.service; then
    PLM_STOPPED=1
else
    echo "ERROR: Failed to stop display-manager.service."
    exit 1
fi

sudo rm -f /tmp/robco-greeter.log
sudo systemctl start greetd.service

# Verify greetd is active immediately
if ! sudo systemctl is-active --quiet greetd.service; then
    echo "ERROR: greetd failed to remain active."
    sudo journalctl -u greetd.service -n 100 --no-pager
    exit 1
fi

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
if [ -f /tmp/robco-greeter.log ]; then
    sudo cp /tmp/robco-greeter.log ./robco-greeter-app.log
    sudo chown $USER:$USER ./robco-greeter-app.log
    echo "App logs saved to: robco-greeter-app.log"
fi

# Cleanup handles restoration
