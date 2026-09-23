#!/bin/bash
# Permanent Installation Script for RobCo Greeter
# This script must be run as root or with sudo.
set -euo pipefail

echo "=== RobCo Greeter Permanent Installer ==="

if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Please run as root or with sudo."
    exit 1
fi

PROD_DIR="/usr/local/lib/robco-greeter"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEV_DIR="$SCRIPT_DIR"
STAGING_DIR="$(mktemp -d /tmp/robco-greeter-stage.XXXXXX)"

INSTALL_STATE="staging"
GREETD_CONFIG_BAK="/tmp/robco-greeter-greetd-config.bak"
DM_SERVICE_BAK="/tmp/robco-greeter-dm-service.bak"
GREETD_ENABLEMENT_BAK="/tmp/robco-greeter-greetd-enablement.bak"

cleanup() {
    local exit_code=$?
    if [ "${CLEANUP_RUN:-0}" = "1" ]; then
        exit $exit_code
    fi
    CLEANUP_RUN=1

    if [ $exit_code -ne 0 ]; then
        echo "ERROR: Installation failed during '$INSTALL_STATE'. Commencing rollback..."

        if [ "$INSTALL_STATE" = "configuring" ]; then
            echo "Rolling back production deployment..."
            if [ -d "${PROD_DIR}.bak" ]; then
                rm -rf "$PROD_DIR"
                mv "${PROD_DIR}.bak" "$PROD_DIR"
            elif [ -d "$PROD_DIR" ] && [ ! -d "${PROD_DIR}.bak" ]; then
                rm -rf "$PROD_DIR"
            fi

            echo "Rolling back configuration..."
            if [ -f "$GREETD_CONFIG_BAK" ]; then
                mkdir -p /etc/greetd
                cat "$GREETD_CONFIG_BAK" > /etc/greetd/config.toml
            else
                rm -f /etc/greetd/config.toml
            fi

            if [ -f "$DM_SERVICE_BAK" ]; then
                ORIG_TARGET=$(cat "$DM_SERVICE_BAK")
                if [ -n "$ORIG_TARGET" ]; then
                    ln -sf "$ORIG_TARGET" /etc/systemd/system/display-manager.service
                else
                    rm -f /etc/systemd/system/display-manager.service
                fi
            else
                rm -f /etc/systemd/system/display-manager.service
            fi

            if [ -f "$GREETD_ENABLEMENT_BAK" ]; then
                ORIG_STATE=$(cat "$GREETD_ENABLEMENT_BAK")
                if [ "$ORIG_STATE" = "disabled" ] || [ "$ORIG_STATE" = "not-found" ]; then
                    systemctl disable greetd.service >/dev/null 2>&1 || true
                elif [ "$ORIG_STATE" = "masked" ]; then
                    systemctl mask greetd.service >/dev/null 2>&1 || true
                elif [ "$ORIG_STATE" = "enabled" ] || [ "$ORIG_STATE" = "static" ] || [ "$ORIG_STATE" = "generated" ] || [ "$ORIG_STATE" = "indirect" ]; then
                    systemctl enable greetd.service >/dev/null 2>&1 || true
                fi
            fi

            systemctl daemon-reload >/dev/null 2>&1 || true
            echo "Rollback complete. The previous system state has been restored."
        fi
    fi

    # Cleanup temporary/backup files
    if [ -d "$STAGING_DIR" ]; then
        rm -rf "$STAGING_DIR"
    fi
    rm -rf "${PROD_DIR}.bak" 2>/dev/null || true
    rm -f "$GREETD_CONFIG_BAK" 2>/dev/null || true
    rm -f "$DM_SERVICE_BAK" 2>/dev/null || true
    rm -f "$GREETD_ENABLEMENT_BAK" 2>/dev/null || true

    exit $exit_code
}
trap cleanup EXIT ERR

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

echo "[3/11] Staging new deployment at $STAGING_DIR..."
cp -a "$DEV_DIR/." "$STAGING_DIR/"

# Prompt user for their password securely:
echo -n "Please enter your password for your account (password will be encrypted): "
read -r -s USERPASS
echo ""

# Disable development settings in config.toml for production realism
if [ -f "$STAGING_DIR/config.toml" ]; then
    sed -i 's/mock_auth = true/mock_auth = false/g' "$STAGING_DIR/config.toml"
    sed -i 's/development_mode = true/development_mode = false/g' "$STAGING_DIR/config.toml"
fi

echo "[4/11] Creating virtual environment..."
python3 -m venv "$STAGING_DIR/venv"

echo "[5/11] Installing dependencies..."
"$STAGING_DIR/venv/bin/pip" install -q -r "$STAGING_DIR/requirements.txt"

echo "[5.5/11] Generating encrypted credentials..."
"$STAGING_DIR/venv/bin/python3" "$STAGING_DIR/app/auth/encrypt_pass.py" "$STAGING_DIR/credentials.enc" <<< "$USERPASS"
unset USERPASS # Fully clear the variable from shell memory

echo "[6/11] Applying strict permissions..."
chown -R root:root "$STAGING_DIR"
find "$STAGING_DIR" -type d -exec chmod 755 {} \;
find "$STAGING_DIR" -type f -executable -exec chmod 755 {} \;
find "$STAGING_DIR" -type f ! -executable -exec chmod 644 {} \;
find "$STAGING_DIR" -type f -name "*.so" -exec chmod 755 {} \;
find "$STAGING_DIR" -type f -name "*.so.*" -exec chmod 755 {} \;

# Secure the credentials file
chown root:greetd "$STAGING_DIR/credentials.enc"
chmod 640 "$STAGING_DIR/credentials.enc"
rm -f "$STAGING_DIR/app/auth/encrypt_pass.py" # Remove encryption script from production

echo "[7/11] Verifying staged deployment..."
sudo -u greetd bash -c "cd $STAGING_DIR && venv/bin/python3 -c 'import PyQt6.QtWidgets'" || {
    echo "ERROR: Permission or installation error verifying PyQt6 as greetd."
    exit 1
}

if ! sudo -u greetd "$STAGING_DIR/venv/bin/python3" --version >/dev/null 2>&1; then
    echo "ERROR: Cannot execute python in staging dir. Check if partition is mounted with noexec."
    exit 1
fi

echo "[7.5/11] Backing up current configuration..."
INSTALL_STATE="backing_up"

if [ -f /etc/greetd/config.toml ]; then
    cp /etc/greetd/config.toml "$GREETD_CONFIG_BAK"
else
    # Create empty file so we know it didn't exist
    touch "$GREETD_CONFIG_BAK"
    # Actually, empty config is invalid for greetd, but rollback logic removes it if size is 0 or if we do it better.
    # Wait, my rollback says `if [ -f "$GREETD_CONFIG_BAK" ] ... cat ...`. If it's empty, it restores empty file.
    # Let's just create an empty backup so the file exists.
    rm -f "$GREETD_CONFIG_BAK" # ensuring it doesn't exist if not present
fi

ORIGINAL_DM_TARGET=$(readlink -f /etc/systemd/system/display-manager.service || echo "")
if [ -n "$ORIGINAL_DM_TARGET" ]; then
    echo "$ORIGINAL_DM_TARGET" > "$DM_SERVICE_BAK"
else
    touch "$DM_SERVICE_BAK"
fi

GREETD_STATE=$(systemctl is-enabled greetd.service 2>/dev/null || true)
if [ -z "$GREETD_STATE" ]; then
    GREETD_STATE="not-found"
fi
echo "$GREETD_STATE" > "$GREETD_ENABLEMENT_BAK"

echo "[7.8/11] Deploying to production..."
INSTALL_STATE="configuring"

find "$STAGING_DIR/venv/bin" -type f ! -type l -exec sed -i "s|$STAGING_DIR|$PROD_DIR|g" {} +
if [ -d "$PROD_DIR" ]; then
    echo "Backing up existing production deployment..."
    rm -rf "${PROD_DIR}.bak" 2>/dev/null || true
    mv "$PROD_DIR" "${PROD_DIR}.bak"
fi
mv "$STAGING_DIR" "$PROD_DIR"
restorecon -Rv "$PROD_DIR" >/dev/null

echo "[8/11] Configuring greetd..."
mkdir -p /etc/greetd
cat <<EOF > /etc/greetd/config.toml
[terminal]
vt = 1

[default_session]
command = "cage -s -- bash -c 'cd /usr/local/lib/robco-greeter && venv/bin/python3 -m app.main'"
user = "greetd"
EOF

if [ -n "$ORIGINAL_DM_TARGET" ]; then
    echo "Saving original DM target to /etc/greetd/original_dm_target.txt..."
    echo "$ORIGINAL_DM_TARGET" > /etc/greetd/original_dm_target.txt
fi

echo "[10/11] Enabling greetd.service and setting as active display manager..."
systemctl enable -f greetd.service || { echo "ERROR: Failed to enable greetd.service."; exit 1; }

ln -sf /lib/systemd/system/greetd.service /etc/systemd/system/display-manager.service

echo "[11/11] Reloading systemd..."
systemctl daemon-reload

INSTALL_STATE="success"

echo "=========================================================="
echo "                 INSTALLATION COMPLETE                    "
echo "=========================================================="
echo "RobCo Greeter is now permanently installed and configured."
echo "Original Display Manager Target saved to: /etc/greetd/original_dm_target.txt"
echo ""
echo "IMPORTANT: A reboot is required to transition from the current display manager to greetd."
echo "Please manually reboot the system when you are ready."
echo "=========================================================="
