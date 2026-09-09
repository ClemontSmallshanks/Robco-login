# RobCo Greeter

A highly immersive, Fallout-inspired terminal login screen (greeter) for Wayland systems. 

Built on top of `greetd` and `cage`, this greeter forces you to interact with a classic RobCo Industries terminal to authenticate and launch your desktop environment (such as Plasma Wayland). It features the iconic hacking minigame which can be configured to act as an authentic bypass to your Linux session.

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
