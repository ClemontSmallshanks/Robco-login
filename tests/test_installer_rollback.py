import os
import stat
import subprocess
import tempfile
import pytest
from pathlib import Path

def setup_fake_env(tmp_path: Path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    
    def write_fake_cmd(name: str, script: str):
        p = bin_dir / name
        p.write_text(f"#!/bin/bash\n{script}")
        p.chmod(p.stat().st_mode | stat.S_IEXEC)
        
    write_fake_cmd("id", "exit 0")
    write_fake_cmd("cage", "exit 0")
    write_fake_cmd("chown", "exit 0")
    write_fake_cmd("restorecon", "exit 0")
    write_fake_cmd("sudo", '''
    if [ "$1" = "-u" ]; then
        shift 2
    fi
    exec "$@"
    ''')
    write_fake_cmd("readlink", "echo '/fake/dm.service'")
    
    fake_sys = tmp_path / "sys"
    fake_sys.mkdir(exist_ok=True)
    
    etc_greetd = fake_sys / "etc" / "greetd"
    etc_greetd.mkdir(parents=True, exist_ok=True)
    etc_pam = fake_sys / "etc" / "pam.d"
    etc_pam.mkdir(parents=True, exist_ok=True)
    (etc_pam / "greetd").write_text("auth required pam_unix.so")
    
    systemd_sys = fake_sys / "etc" / "systemd" / "system"
    systemd_sys.mkdir(parents=True, exist_ok=True)
    (systemd_sys / "display-manager.service").write_text("fake-original-service")
    
    prod_dir = fake_sys / "usr" / "local" / "lib" / "robco-greeter"
    prod_dir.mkdir(parents=True, exist_ok=True)
    (prod_dir / "old_prod_file.txt").write_text("I AM OLD PRODUCTION")
    
    (fake_sys / "tmp").mkdir(parents=True, exist_ok=True)
    
    return bin_dir, fake_sys, prod_dir, write_fake_cmd

def patch_script(original_script: str, fake_sys: Path, script_path: Path, prod_dir: Path):
    patched = original_script.replace(
        'PROD_DIR="/usr/local/lib/robco-greeter"',
        f'PROD_DIR="{prod_dir}"'
    ).replace(
        'DEV_DIR="$SCRIPT_DIR"',
        f'DEV_DIR="{script_path.parent}"'
    ).replace(
        '/etc/greetd',
        f'{fake_sys}/etc/greetd'
    ).replace(
        '/etc/systemd',
        f'{fake_sys}/etc/systemd'
    ).replace(
        '/etc/pam.d',
        f'{fake_sys}/etc/pam.d'
    ).replace(
        '/lib/systemd',
        f'{fake_sys}/lib/systemd'
    ).replace(
        '/tmp/robco-greeter-greetd-enablement.bak',
        f'{fake_sys}/tmp/robco-greeter-greetd-enablement.bak'
    ).replace(
        '/tmp/robco-greeter-greetd-config.bak',
        f'{fake_sys}/tmp/robco-greeter-greetd-config.bak'
    ).replace(
        '/tmp/robco-greeter-dm-service.bak',
        f'{fake_sys}/tmp/robco-greeter-dm-service.bak'
    )
    patched = patched.replace('if [ "$EUID" -ne 0 ]; then', 'if false; then')
    return patched

def test_installer_rollback(tmp_path: Path):
    script_path = Path(__file__).resolve().parent.parent / "install.sh"
    bin_dir, fake_sys, prod_dir, write_fake_cmd = setup_fake_env(tmp_path)
    
    systemctl_log = fake_sys / "systemctl_log.txt"
    write_fake_cmd("systemctl", f'''
    echo "$@" >> "{systemctl_log}"
    if [ "$1" = "is-enabled" ]; then
        echo "disabled"
        exit 1
    fi
    if [ "$1" = "daemon-reload" ]; then
        if [ ! -f "{fake_sys}/daemon_reloaded" ]; then
            touch "{fake_sys}/daemon_reloaded"
            echo "SIMULATED FAILURE"
            exit 1
        fi
    fi
    exit 0
    ''')
    
    test_script = tmp_path / "test_install.sh"
    test_script.write_text(patch_script(script_path.read_text(), fake_sys, script_path, prod_dir))
    test_script.chmod(test_script.stat().st_mode | stat.S_IEXEC)
    
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    p = subprocess.Popen([str(test_script)], env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        stdout, stderr = p.communicate(input="testpassword\n", timeout=60)
    except subprocess.TimeoutExpired:
        p.kill()
        stdout, stderr = p.communicate()
        print("TIMEOUT!")
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
        raise
    
    if not prod_dir.exists():
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
    assert p.returncode != 0
    assert prod_dir.exists()
    assert (prod_dir / "old_prod_file.txt").exists()
    assert (prod_dir / "old_prod_file.txt").read_text() == "I AM OLD PRODUCTION"
    assert not Path(f"{prod_dir}.bak").exists()
    
    dm_service = fake_sys / "etc" / "systemd" / "system" / "display-manager.service"
    assert dm_service.is_symlink() or dm_service.exists()
    if dm_service.is_symlink():
        assert os.readlink(str(dm_service)) == "/fake/dm.service"
    
    assert not (fake_sys / "etc" / "greetd" / "config.toml").exists()
    
    log_contents = systemctl_log.read_text()
    assert "enable -f greetd.service" in log_contents
    assert "disable greetd.service" in log_contents

def test_installer_rollback_originally_enabled(tmp_path: Path):
    script_path = Path(__file__).resolve().parent.parent / "install.sh"
    bin_dir, fake_sys, prod_dir, write_fake_cmd = setup_fake_env(tmp_path)
    
    systemctl_log = fake_sys / "systemctl_log.txt"
    write_fake_cmd("systemctl", f'''
    echo "$@" >> "{systemctl_log}"
    if [ "$1" = "is-enabled" ]; then
        echo "enabled"
        exit 0
    fi
    if [ "$1" = "daemon-reload" ]; then
        if [ ! -f "{fake_sys}/daemon_reloaded" ]; then
            touch "{fake_sys}/daemon_reloaded"
            echo "SIMULATED FAILURE"
            exit 1
        fi
    fi
    exit 0
    ''')
    
    test_script = tmp_path / "test_install.sh"
    test_script.write_text(patch_script(script_path.read_text(), fake_sys, script_path, prod_dir))
    test_script.chmod(test_script.stat().st_mode | stat.S_IEXEC)
    
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    p = subprocess.Popen([str(test_script)], env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        stdout, stderr = p.communicate(input="testpassword\n", timeout=60)
    except subprocess.TimeoutExpired:
        p.kill()
        stdout, stderr = p.communicate()
        print("TIMEOUT!")
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
        raise
    
    assert p.returncode != 0
    assert prod_dir.exists()
    
    log_contents = systemctl_log.read_text()
    assert "enable -f greetd.service" in log_contents
    # Wait, the first enable was the installation enable!
    # The rollback also calls enable because it was originally enabled!
    enable_count = log_contents.count("enable")
    assert enable_count >= 2

def test_installer_success(tmp_path: Path):
    script_path = Path(__file__).resolve().parent.parent / "install.sh"
    bin_dir, fake_sys, prod_dir, write_fake_cmd = setup_fake_env(tmp_path)
    
    write_fake_cmd("systemctl", "exit 0")
    
    test_script = tmp_path / "test_install.sh"
    test_script.write_text(patch_script(script_path.read_text(), fake_sys, script_path, prod_dir))
    test_script.chmod(test_script.stat().st_mode | stat.S_IEXEC)
    
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    p = subprocess.Popen([str(test_script)], env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        stdout, stderr = p.communicate(input="testpassword\n", timeout=60)
    except subprocess.TimeoutExpired:
        p.kill()
        stdout, stderr = p.communicate()
        print("TIMEOUT!")
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
        raise
    
    if p.returncode != 0:
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
    assert p.returncode == 0
    assert prod_dir.exists()
    assert (prod_dir / "app").exists()
    
    assert not Path(f"{prod_dir}.bak").exists()
    assert not (fake_sys / "tmp" / "robco-greeter-greetd-config.bak").exists()
    assert not (fake_sys / "tmp" / "robco-greeter-dm-service.bak").exists()
    assert not (fake_sys / "tmp" / "robco-greeter-greetd-enablement.bak").exists()
