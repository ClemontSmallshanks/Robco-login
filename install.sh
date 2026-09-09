#!/bin/bash
# Permanent Installation Script for RobCo Greeter
# This script must be run as root or with sudo.

echo "=== RobCo Greeter Permanent Installer ==="

if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Please run as root or with sudo."
    exit 1
fi

PROD_DIR="/usr/local/lib/robco-greeter"
DEV_DIR="$(pwd)"

echo "[1/11] Verifying prerequisites..."
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

echo "[2/11] Verifying existing application..."
if [ ! -f "$DEV_DIR/app/main.py" ]; then
    echo "ERROR: Application repository incomplete (app/main.py missing)."
    exit 1
fi
if [ ! -f "$DEV_DIR/requirements.txt" ]; then
    echo "ERROR: requirements.txt missing."
    exit 1
fi

echo "[3/11] Creating production deployment at $PROD_DIR..."
if [ -d "$PROD_DIR" ]; then
    echo "WARNING: $PROD_DIR already exists. It will be overwritten."
    rm -rf "$PROD_DIR"
fi
mkdir -p "$PROD_DIR"
cp -a "$DEV_DIR/." "$PROD_DIR/"

# Disable development settings in config.toml for production realism
if [ -f "$PROD_DIR/config.toml" ]; then
    sed -i 's/mock_auth = true/mock_auth = false/g' "$PROD_DIR/config.toml"
    sed -i 's/development_mode = true/development_mode = false/g' "$PROD_DIR/config.toml"
fi

echo "[4/11] Creating virtual environment..."
python3 -m venv "$PROD_DIR/venv"

echo "[5/11] Installing dependencies..."
"$PROD_DIR/venv/bin/pip" install -q -r "$PROD_DIR/requirements.txt"

echo "[6/11] Applying strict permissions..."
chown -R root:root "$PROD_DIR"
find "$PROD_DIR" -type d -exec chmod 755 {} \;
find "$PROD_DIR" -type f -executable -exec chmod 755 {} \;
find "$PROD_DIR" -type f ! -executable -exec chmod 644 {} \;
find "$PROD_DIR" -type f -name "*.so" -exec chmod 755 {} \;
find "$PROD_DIR" -type f -name "*.so.*" -exec chmod 755 {} \;

# Fix SELinux contexts
restorecon -Rv "$PROD_DIR" >/dev/null

echo "[7/11] Verifying application as 'greetd'..."
sudo -u greetd bash -c "cd $PROD_DIR && venv/bin/python3 -c 'import PyQt6.QtWidgets'" || {
    echo "ERROR: Permission or installation error verifying PyQt6 as greetd."
    exit 1
}

if ! sudo -u greetd "$PROD_DIR/venv/bin/python3" --version >/dev/null 2>&1; then
    echo "ERROR: Cannot execute python in $PROD_DIR. Check if partition is mounted with noexec."
    exit 1
fi

echo "[8/11] Configuring greetd..."
mkdir -p /etc/greetd
cat <<EOF > /etc/greetd/config.toml
[terminal]
vt = 1

[default_session]
command = "cage -s -- bash -c 'cd /usr/local/lib/robco-greeter && venv/bin/python3 -m app.main'"
user = "greetd"
EOF

echo "[9/11] Backing up original display manager target..."
ORIGINAL_DM_TARGET=$(readlink -f /etc/systemd/system/display-manager.service || echo "")
if [ -n "$ORIGINAL_DM_TARGET" ]; then
    echo "Saving original DM target to /etc/greetd/original_dm_target.txt..."
    echo "$ORIGINAL_DM_TARGET" > /etc/greetd/original_dm_target.txt
fi

echo "[10/11] Enabling greetd.service and setting as active display manager..."
systemctl enable -f greetd.service || { echo "ERROR: Failed to enable greetd.service."; exit 1; }

ln -sf /lib/systemd/system/greetd.service /etc/systemd/system/display-manager.service

echo "[11/11] Reloading systemd..."
systemctl daemon-reload

echo "=========================================================="
echo "                 INSTALLATION COMPLETE                    "
echo "=========================================================="
echo "RobCo Greeter is now permanently installed and configured."
echo "Original Display Manager Target saved to: /etc/greetd/original_dm_target.txt"
echo ""
echo "IMPORTANT: A reboot is required to transition from the current display manager to greetd."
echo "Please manually reboot the system when you are ready."
echo "=========================================================="
