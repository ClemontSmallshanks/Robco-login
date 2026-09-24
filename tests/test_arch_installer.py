import os
import subprocess
import pytest
from pathlib import Path
import shutil

INSTALLER = "installers/arch/install.sh"
UNINSTALLER = "installers/arch/uninstall.sh"

@pytest.fixture
def mock_root(tmp_path):
    root = tmp_path / "arch-root"
    os.makedirs(root / "etc")
    os.makedirs(root / "usr/bin")
    os.makedirs(root / "usr/local/lib")
    os.makedirs(root / "etc/systemd/system")
    os.makedirs(root / "etc/greetd")
    
    with open(root / "etc/os-release", "w") as f:
        f.write('ID=arch\n')
        
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
    # Pass empty root, which targets real system.
    # The script should detect Fedora and safely abort.
    # We mock /etc/os-release in a new namespace? No, it just reads the real one if ROOT is empty.
    # Since we are running ON Fedora, it should natively reject.
    result = run_script(INSTALLER)
    assert result.returncode == 1
    assert "Running on Fedora" in result.stdout
    assert "aborted safely" in result.stdout

def test_arch_detection(mock_root):
    result = run_script(INSTALLER, root=mock_root)
    assert result.returncode == 0
    assert "Arch Linux detected" in result.stdout

def test_dry_run(mock_root):
    result = run_script(INSTALLER, root=mock_root, args=["--dry-run"])
    assert result.returncode == 0
    assert "--- DRY RUN ---" in result.stdout
    assert "Would create" in result.stdout
    assert "would install packages: greetd cage python" in result.stdout

def test_simulated_installation(mock_root):
    result = run_script(INSTALLER, root=mock_root)
    assert result.returncode == 0
    
    # Assert paths created
    assert (mock_root / "usr/local/lib/robco-greeter/main.py").exists()
    assert (mock_root / "etc/greetd/config.toml").exists()
    
    # Assert display manager symlink
    dm_link = mock_root / "etc/systemd/system/display-manager.service"
    assert dm_link.is_symlink()
    assert os.readlink(dm_link) == "/usr/lib/systemd/system/greetd.service"

def test_uninstallation(mock_root):
    run_script(INSTALLER, root=mock_root)
    assert (mock_root / "usr/local/lib/robco-greeter").exists()
    
    result = run_script(UNINSTALLER, root=mock_root)
    assert result.returncode == 0
    
    assert not (mock_root / "usr/local/lib/robco-greeter").exists()
    assert not (mock_root / "etc/greetd/config.toml").exists()

def test_rollback_on_failure(mock_root):
    # Break the installer intentionally to test trap rollback
    # We can do this by modifying the installer temporarily in the test
    with open(INSTALLER, "r") as f:
        content = f.read()
    
    broken_installer = mock_root / "broken_install.sh"
    with open(broken_installer, "w") as f:
        # Insert a failure before success state
        f.write(content.replace('INSTALL_STATE="success"', 'exit 1\n'))
        
    result = run_script(broken_installer, root=mock_root)
    assert result.returncode == 1
    assert "Rollback complete" in result.stdout
    
    # Verify paths rolled back
    assert not (mock_root / "usr/local/lib/robco-greeter").exists()

def test_no_escape_from_simulated_root(mock_root):
    # To test if the script writes outside ROOT, we check that no real system changes occur.
    with open(INSTALLER, "r") as f:
        content = f.read()
        
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.strip().startswith('#') or 'echo' in line or 'readlink' in line or 'ln -sf "/usr/lib' in line or 'grep' in line:
            continue
            
        if "mkdir" in line or "cp" in line or "rm" in line or (">" in line and "2>/dev/null" not in line and ">&" not in line):
            if "/etc/" in line and "${ROOT}" not in line and "${GREETD_DIR}" not in line and "${SYSTEMD_DIR}" not in line and "${PAM_DIR}" not in line:
                pytest.fail(f"Potential root escape in installer line {i+1}: {line}")
            if "/usr/" in line and "${ROOT}" not in line and "${PROD_DIR}" not in line and "${BIN_DIR}" not in line:
                pytest.fail(f"Potential root escape in installer line {i+1}: {line}")

