import subprocess
import os

commands = [
    "systemctl status greetd",
    "systemctl status plasmalogin",
    "systemctl status display-manager",
    "readlink -f /etc/systemd/system/display-manager.service",
    "systemctl cat greetd",
    "journalctl -b -1 -u greetd --no-pager",
    "journalctl -b -1 -u display-manager --no-pager"
]

with open("/home/regi/Desktop/Fallout login/robco-greeter/diag.txt", "w") as f:
    for cmd in commands:
        f.write(f"=== {cmd} ===\n")
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            f.write("STDOUT:\n")
            f.write(result.stdout)
            f.write("STDERR:\n")
            f.write(result.stderr)
        except Exception as e:
            f.write(f"Exception: {e}\n")
        f.write("\n")
