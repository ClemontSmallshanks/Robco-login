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
        echo "Kubuntu is required for native installation."
        echo "Running on Fedora."
        echo "Native Kubuntu installation aborted safely."
        exit 1
    fi
fi

OS_RELEASE="${ROOT}/etc/os-release"
if [ ! -f "$OS_RELEASE" ] || ! grep -iq "ID=ubuntu" "$OS_RELEASE"; then
    echo "ERROR: Target system is not Ubuntu/Kubuntu."
    exit 1
fi

PROD_DIR="${ROOT}/usr/local/lib/robco-greeter"
SDDM_CONF_DIR="${ROOT}/etc/sddm.conf.d"
SYSTEMD_DIR="${ROOT}/etc/systemd/system"
BIN_DIR="${ROOT}/usr/bin"
PAM_DIR="${ROOT}/etc/pam.d"
WAYLAND_SESSIONS="${ROOT}/usr/share/wayland-sessions"

# ==========================================
# PACKAGE MANAGEMENT MOCK
# ==========================================
run_apt() {
    local action=$1
    shift
    if [ -n "$ROOT" ] || [ $DRY_RUN -eq 1 ]; then
        if [ "$action" == "install" ]; then
            echo "[MOCK] would apt-get install packages: $@"
        elif [ "$action" == "check" ]; then
            echo "[MOCK] would check if package installed: $@"
            return 0
        fi
    else
        echo "Running real apt is forbidden in this phase."
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

detect_plasma_wayland() {
    if [ -f "${BIN_DIR}/startplasma-wayland" ]; then
        echo "Found startplasma-wayland"
        return 0
    else
        # Allow passing in dry run / mock
        if [ -n "$ROOT" ] || [ $DRY_RUN -eq 1 ]; then
            echo "Mocking startplasma-wayland detection"
            return 0
        fi
        return 1
    fi
}

# ==========================================
# DRY RUN MODE
# ==========================================
if [ $DRY_RUN -eq 1 ]; then
    echo "--- DRY RUN ---"
    echo "Platform detected: Ubuntu/Kubuntu"
    echo "Desktop detected: KDE Plasma Wayland"
    echo "Display Manager: SDDM"
    echo "Would create: $PROD_DIR"
    echo "Would modify: $SDDM_CONF_DIR/10-robco.conf"
    run_apt install "python3 python3-pyqt6 sddm plasma-workspace-wayland"
    run_systemctl enable "sddm.service"
    echo "--- DRY RUN COMPLETE ---"
    exit 0
fi

# ==========================================
# INSTALLATION LOGIC & ROLLBACK
# ==========================================
INSTALL_STATE="init"
BACKUP_SDDM="${ROOT}/tmp/sddm_config.bak"

cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ] && [ "$INSTALL_STATE" != "success" ] && [ "$INSTALL_STATE" != "init" ]; then
        echo "Installation failed. Rolling back..."
        
        if [ -f "$BACKUP_SDDM" ]; then
            mv "$BACKUP_SDDM" "${SDDM_CONF_DIR}/10-robco.conf" 2>/dev/null || true
        else
            rm -f "${SDDM_CONF_DIR}/10-robco.conf"
        fi
        
        rm -rf "$PROD_DIR"
        run_systemctl "daemon-reload" ""
        echo "Rollback complete."
    fi
    
    rm -f "$BACKUP_SDDM" 2>/dev/null || true
    exit $exit_code
}
trap cleanup EXIT ERR

echo "Kubuntu Linux detected. Beginning simulated installation..."

INSTALL_STATE="backing_up"
mkdir -p "${ROOT}/tmp"
mkdir -p "$SDDM_CONF_DIR"

if [ -f "${SDDM_CONF_DIR}/10-robco.conf" ]; then
    cp "${SDDM_CONF_DIR}/10-robco.conf" "$BACKUP_SDDM"
fi

detect_plasma_wayland > /dev/null

INSTALL_STATE="installing"
mkdir -p "$PROD_DIR"
mkdir -p "$SYSTEMD_DIR"

echo "Copying application..."
# In test mode we just touch a mock main file.
touch "${PROD_DIR}/main.py"

echo "Applying permissions..."
chmod 755 "${PROD_DIR}"
if [ -n "$ROOT" ]; then
    echo "[MOCK] would apply root:root ownership to $PROD_DIR"
fi

echo "Writing SDDM configuration..."
cat <<'CONFIG' > "${SDDM_CONF_DIR}/10-robco.conf"
[Autologin]
User=greeter
Session=robco-wayland.desktop
CONFIG

# Simulate creating the wayland session
mkdir -p "$WAYLAND_SESSIONS"
cat <<'SESSION' > "${WAYLAND_SESSIONS}/robco-wayland.desktop"
[Desktop Entry]
Name=RobCo Greeter
Exec=python3 /usr/local/lib/robco-greeter/main.py
Type=Application
SESSION

run_systemctl "enable" "sddm.service"
run_systemctl "daemon-reload" ""

INSTALL_STATE="success"
echo "Installation complete."
