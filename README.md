# RobCo Greeter

Hey folks, so this is replica of the hacking minigame from Fallout. Of course, you don't have to play the minigame, you can just enter your actual password and enter your system directly. It's a fun addition to my system lol. I have attached several screenshots of what it looks like while I was working on it. Also, I have only played New Vegas, so this minigame might be different on other fallout games, but I don't know about that. Cheers!!

---

## Prerequisites

Before installing, ensure your Linux distribution has the following packages installed (package names may vary depending on your distro):

- `greetd` (The modular login manager daemon)
- `cage` (A lightweight Wayland kiosk compositor)
- `python3` and `python3-pip`
- `python3-venv` (For virtual environments)

## Installation

The permanent installer script handles setting up the production environment, safely copying the files, applying strict secure permissions, and registering the greeter with `systemd`.

1. Clone or navigate to this repository directory.
2. Run the automated transactional installation script:
   ```bash
   sudo ./install.sh
   ```
3. The installer will prompt you to securely enter your Linux password. 
   > **Note:** Your input will be masked. The password is immediately encrypted and safely stored in the deployed production location (`/usr/local/lib/robco-greeter/credentials.enc`) with strict `root:greetd` permissions. It is **never** saved in this source repository.
4. Once the installation completes successfully, **reboot your system**.

Upon reboot, `greetd` will launch the RobCo terminal interface in place of your standard desktop login screen.

## How Authentication Works

By default, the greeter is configured to allow a "minigame bypass". If you successfully beat the hacking minigame by finding the correct word, the application automatically decrypts your system password in memory and passes it to PAM to seamlessly launch your desktop.

If you ever change your Linux system password, you will need to re-run `sudo ./install.sh` from this directory so the greeter can generate a new encrypted credential file matching your updated password.

## Emergency Recovery & Uninstallation

If you ever find yourself locked out, or if you simply wish to revert to your original display manager (like SDDM, GDM, or LightDM), you can easily uninstall the greeter:

1. On the lock screen, switch to a raw text terminal by pressing **`Ctrl + Alt + F3`** (or `F4`-`F6`).
2. Log in with your standard username and password.
3. Navigate to the folder where you originally downloaded this project:
   ```bash
   cd /path/to/robco-greeter
   ```
4. Run the uninstaller:
   ```bash
   sudo ./uninstall.sh
   ```
5. The script will automatically kill the RobCo greeter, disable `greetd`, and cleanly restore your system's original display manager symlink. You can then switch back to `TTY1` (`Ctrl + Alt + F1`) or reboot.
