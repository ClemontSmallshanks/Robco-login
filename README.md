# RobCo Greeter

Hey folks, so this is replica of the hacking minigame from Fallout. Of course, you don't have to play the minigame, you can just enter your actual password and enter your system directly. It's a fun addition to my system lol. I have attached several screenshots of what it looks like while I was working on it. Also, I have only played New Vegas, so this minigame might be different on other fallout games, but I don't know about that. Cheers!!
---

## Installation

The permanent installer script handles setting up the production environment, copying the files, setting strict secure permissions, and registering the greeter with `systemd`.

1. Ensure you have the prerequisites installed:
   - `greetd`
   - `cage` (Wayland compositor used to run the greeter)
   - `python3` and `pip`
2. Run the automated installation script:
   ```bash
   sudo ./install.sh
   ```
3. Once the installation is complete, **reboot your system**.

---

## Configuring Your Password

By default, the greeter is configured to allow a "minigame bypass". If you successfully beat the hacking minigame (or type your password directly on the keyboard), the script automatically passes your hardcoded system password to PAM to seamlessly launch your desktop without a secondary login screen.

**You must update the script with your actual Linux password before installing.**

1. Open `app/ui/states/hacking_state.py` in a text editor.
2. Locate line **181**:
   ```python
   SYSTEM_PASSWORD = "your_actual_password_here"
   ```
3. Change `"7337"` to your real Linux password.
4. Save the file and run `sudo ./install.sh` to apply the changes to the production deployment.

*(Note: If you change your Linux password in the future, you will need to update this file and run `install.sh` again).*

---

## Uninstallation / Emergency Recovery

If you ever find yourself locked out, or if you simply wish to revert to your original display manager (like SDDM/plasmalogin):

1. On the boot screen, switch to a raw text terminal by pressing **`Ctrl` + `Alt` + `F3`** (or F4-F6).
2. Log in with your standard username and password.
3. Navigate to this project folder:
   ```bash
   cd /path/to/robco-greeter
   ```
4. Run the uninstaller:
   ```bash
   sudo ./uninstall.sh
   ```
5. The script will automatically kill the RobCo greeter and cleanly restore your original display manager.
