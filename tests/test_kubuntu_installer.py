import os
import subprocess
import pytest
from pathlib import Path
import shutil

INSTALLER = "installers/kubuntu/install.sh"
UNINSTALLER = "installers/kubuntu/uninstall.sh"

@pytest.fixture
def mock_root(tmp_path):
    root = tmp_path / "kubuntu-root"
    os.makedirs(root / "etc")
    os.makedirs(root / "usr/bin")
    os.makedirs(root / "usr/local/lib")
    os.makedirs(root / "etc/systemd/system")
    os.makedirs(root / "etc/sddm.conf.d")
    os.makedirs(root / "etc/pam.d")
    os.makedirs(root / "usr/share/wayland-sessions")
    
    with open(root / "etc/os-release", "w") as f:
        f.write('ID=ubuntu\nVERSION_ID="26.04"\n')
        
    return root

def run_script(script, root=None, args=None):
    env = os.environ.copy()
    if root:
        env["ROBCO_TEST_ROOT"] = str(root)
    cmd = ["bash", script]
    if args:
        cmd.extend(args)
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    return result

def test_fedora_rejection(tmp_path):
    # Running native (ROOT=None) on Fedora should reject
    result = run_script(INSTALLER)
    assert result.returncode == 1
    assert "Running on Fedora" in result.stdout
    assert "aborted safely" in result.stdout

def test_kubuntu_detection(mock_root):
    result = run_script(INSTALLER, root=mock_root)
    assert result.returncode == 0
    assert "Kubuntu Linux detected" in result.stdout

def test_dry_run(mock_root):
    result = run_script(INSTALLER, root=mock_root, args=["--dry-run"])
    assert result.returncode == 0
    assert "--- DRY RUN ---" in result.stdout
    assert "Would create" in result.stdout
    assert "would apt-get install packages: python3 python3-pyqt6 sddm plasma-workspace-wayland" in result.stdout

def test_simulated_installation(mock_root):
    result = run_script(INSTALLER, root=mock_root)
    assert result.returncode == 0
    
    # Assert paths created
    assert (mock_root / "usr/local/lib/robco-greeter/main.py").exists()
    assert (mock_root / "etc/sddm.conf.d/10-robco.conf").exists()
    assert (mock_root / "usr/share/wayland-sessions/robco-wayland.desktop").exists()
    
def test_uninstallation(mock_root):
    run_script(INSTALLER, root=mock_root)
    assert (mock_root / "usr/local/lib/robco-greeter").exists()
    
    result = run_script(UNINSTALLER, root=mock_root)
    assert result.returncode == 0
    
    assert not (mock_root / "usr/local/lib/robco-greeter").exists()
    assert not (mock_root / "etc/sddm.conf.d/10-robco.conf").exists()
    assert not (mock_root / "usr/share/wayland-sessions/robco-wayland.desktop").exists()

def test_rollback_on_failure(mock_root):
    with open(INSTALLER, "r") as f:
        content = f.read()
    
    broken_installer = mock_root / "broken_install.sh"
    with open(broken_installer, "w") as f:
        f.write(content.replace('INSTALL_STATE="success"', 'exit 1\n'))
        
    result = run_script(broken_installer, root=mock_root)
    assert result.returncode == 1
    assert "Rollback complete" in result.stdout
    assert not (mock_root / "usr/local/lib/robco-greeter").exists()

def test_no_escape_from_simulated_root(mock_root):
    with open(INSTALLER, "r") as f:
        content = f.read()
        
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.strip().startswith('#') or 'echo' in line or 'readlink' in line or 'grep' in line:
            continue
            
        if "mkdir" in line or "cp" in line or "rm" in line or (">" in line and "2>/dev/null" not in line and ">&" not in line):
            if "/etc/" in line and "${ROOT}" not in line and "${SDDM_CONF_DIR}" not in line and "${SYSTEMD_DIR}" not in line and "${PAM_DIR}" not in line:
                pytest.fail(f"Potential root escape in installer line {i+1}: {line}")
            if "/usr/" in line and "${ROOT}" not in line and "${PROD_DIR}" not in line and "${BIN_DIR}" not in line and "${WAYLAND_SESSIONS}" not in line:
                pytest.fail(f"Potential root escape in installer line {i+1}: {line}")

