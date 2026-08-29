import os
import subprocess
import time

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode

def main():
    print("=== PRE-FLIGHT VERIFICATIONS ===")
    
    # 1. Directory exists?
    if os.path.exists("/usr/local/lib/robco-greeter"):
        print("ERROR: /usr/local/lib/robco-greeter exists.")
    else:
        print("[OK] /usr/local/lib/robco-greeter does not exist.")

    # 2. PLM is active?
    stdout, rc = run_cmd("systemctl is-active display-manager.service")
    if stdout == "active":
        print("[OK] PLM is currently active.")
    else:
        print(f"ERROR: PLM is not active: {stdout}")

    # 3. display-manager symlink?
    stdout, rc = run_cmd("readlink -f /etc/systemd/system/display-manager.service")
    if "plasmalogin.service" in stdout:
        print(f"[OK] display-manager.service points to {stdout}")
    else:
        print(f"ERROR: display-manager.service points to {stdout}")

    # 4. greetd inactive?
    stdout, rc = run_cmd("systemctl is-active greetd.service")
    if stdout != "active":
        print("[OK] greetd is inactive.")
    else:
        print("ERROR: greetd is active.")

    print("\n=== EXECUTING DEPLOY_AND_TEST.SH ===")
    os.chdir("/home/regi/Desktop/Fallout login/robco-greeter")
    process = subprocess.Popen(["bash", "./deploy_and_test.sh"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in process.stdout:
        print(line, end="")
    process.wait()
    
    print("\n=== POST-TEST VERIFICATION ===")
    stdout, rc = run_cmd("systemctl is-active display-manager.service")
    print(f"PLM State: {stdout}")

if __name__ == "__main__":
    main()
