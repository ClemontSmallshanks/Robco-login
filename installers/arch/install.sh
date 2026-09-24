#!/usr/bin/env bash
set -e

# ==========================================
# CONFIGURATION & ABSTRACTIONS
# ==========================================
DRY_RUN=0
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=1
fi

ROOT="${ROBCO_TEST_ROOT:-}"

# Abort if running natively on Fedora
if [ -z "$ROOT" ]; then
    if grep -iq fedora /etc/os-release 2>/dev/null; then
        echo "Arch Linux is required for native installation."
        echo "Running on Fedora."
        echo "Native Arch installation aborted safely."
        exit 1
    fi
fi

OS_RELEASE="${ROOT}/etc/os-release"
if [ ! -f "$OS_RELEASE" ] || ! grep -iq "ID=arch" "$OS_RELEASE"; then
    echo "ERROR: Target system is not Arch Linux."
    exit 1
fi

PROD_DIR="${ROOT}/usr/local/lib/robco-greeter"
GREETD_DIR="${ROOT}/etc/greetd"
SYSTEMD_DIR="${ROOT}/etc/systemd/system"
BIN_DIR="${ROOT}/usr/bin"
PAM_DIR="${ROOT}/etc/pam.d"

# ==========================================
# PACKAGE MANAGEMENT MOCK
# ==========================================
run_pacman() {
    local action=$1
    shift
    if [ -n "$ROOT" ] || [ $DRY_RUN -eq 1 ]; then
        if [ "$action" == "-S" ]; then
            echo "[MOCK] would install packages: $@"
        elif [ "$action" == "-Q" ]; then
            echo "[MOCK] would check if package installed: $@"
            return 0
        fi
    else
        echo "Running real pacman is forbidden in this phase."
        exit 1
    fi
}

# ==========================================
# SYSTEMD INTEGRATION MOCK
# ==========================================
run_systemctl() {
    local action=$1
    local service=$2
    if [ -n "$ROOT" ] || [ $DRY_RUN -eq 1 ]; then
        echo "[MOCK] would systemctl $action $service"
    else
        echo "Running real systemctl is forbidden in this phase."
        exit 1
    fi
}

# ==========================================
# DISPLAY MANAGER INTEGRATION
# ==========================================
detect_display_manager() {
    local target="${SYSTEMD_DIR}/display-manager.service"
    if [ -L "$target" ]; then
        readlink -f "$target"
    else
        echo "none"
    fi
}

# ==========================================
# DRY RUN MODE
# ==========================================
if [ $DRY_RUN -eq 1 ]; then
    echo "--- DRY RUN ---"
    echo "Would create: $PROD_DIR"
    echo "Would modify: $GREETD_DIR/config.toml"
    echo "Would modify: $SYSTEMD_DIR/display-manager.service"
    run_pacman -S "greetd cage python"
    run_systemctl enable "greetd.service"
    echo "--- DRY RUN COMPLETE ---"
    exit 0
fi

# ==========================================
# INSTALLATION LOGIC & ROLLBACK
# ==========================================
INSTALL_STATE="init"
BACKUP_GREETD="${ROOT}/tmp/greetd_config.bak"
BACKUP_DM="${ROOT}/tmp/dm_service.bak"

cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ] && [ "$INSTALL_STATE" != "success" ] && [ "$INSTALL_STATE" != "init" ]; then
        echo "Installation failed. Rolling back..."
        
        if [ -f "$BACKUP_GREETD" ]; then
            cat "$BACKUP_GREETD" > "${GREETD_DIR}/config.toml"
        else
            rm -f "${GREETD_DIR}/config.toml"
        fi
        
        if [ -f "$BACKUP_DM" ]; then
            ORIG=$(cat "$BACKUP_DM")
            if [ "$ORIG" != "none" ]; then
                ln -sf "$ORIG" "${SYSTEMD_DIR}/display-manager.service"
            else
                rm -f "${SYSTEMD_DIR}/display-manager.service"
            fi
        fi
        
        rm -rf "$PROD_DIR"
        run_systemctl "daemon-reload" ""
        echo "Rollback complete."
    fi
    
    rm -f "$BACKUP_GREETD" "$BACKUP_DM" 2>/dev/null || true
    exit $exit_code
}
trap cleanup EXIT ERR

echo "Arch Linux detected. Beginning simulated installation..."

INSTALL_STATE="backing_up"
mkdir -p "${ROOT}/tmp"
if [ -f "${GREETD_DIR}/config.toml" ]; then
    cp "${GREETD_DIR}/config.toml" "$BACKUP_GREETD"
else
    touch "$BACKUP_GREETD"
    rm -f "$BACKUP_GREETD"
fi

DM=$(detect_display_manager)
echo "$DM" > "$BACKUP_DM"

INSTALL_STATE="installing"
mkdir -p "$PROD_DIR"
mkdir -p "$GREETD_DIR"
mkdir -p "$SYSTEMD_DIR"

echo "Copying application..."
# In test mode we just touch a mock main file.
touch "${PROD_DIR}/main.py"

echo "Applying permissions..."
chmod 755 "${PROD_DIR}"
# No real chown/chmod on host paths.
if [ -n "$ROOT" ]; then
    echo "[MOCK] would apply root:root ownership to $PROD_DIR"
fi

echo "Writing greetd configuration..."
cat <<'CONFIG' > "${GREETD_DIR}/config.toml"
[terminal]
vt = 1

[default_session]
command = "cage -s -- bash -c 'cd /usr/local/lib/robco-greeter && python3 -m app.main'"
user = "greeter"
CONFIG

if [ "$DM" != "none" ] && [[ "$DM" != *"greetd"* ]]; then
    echo "$DM" > "${GREETD_DIR}/original_dm_target.txt"
fi

ln -sf "/usr/lib/systemd/system/greetd.service" "${SYSTEMD_DIR}/display-manager.service"

run_systemctl "enable" "greetd.service"
run_systemctl "daemon-reload" ""

INSTALL_STATE="success"
echo "Installation complete."
