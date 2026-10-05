#!/usr/bin/env python3
"""Install the local Omarchy widget and an unused desktop shortcut."""
from datetime import datetime
from pathlib import Path
import json
import shutil
import subprocess
import time

source = Path(__file__).resolve().parent
destination = Path.home() / ".config/omarchy/plugins/io.github.cotopena.omapeek"
bindings = Path.home() / ".config/hypr/bindings.lua"
shell = Path.home() / ".config/omarchy/shell.json"
stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
backup = Path.home() / ".local/state/omapeek/backups" / stamp
begin = "-- BEGIN OmaPeek"
end = "-- END OmaPeek"
# A plugin-manager checkout updates through git; only add the shortcut to it.
managed = (destination / ".git").exists() and source != destination.resolve()
package = destination if managed else source
version = json.loads((package / "manifest.json").read_text())["version"]
if not bindings.is_file():
    raise SystemExit(f"{bindings} was not found. OmaPeek adds its shortcut to Omarchy's "
                     "Hyprland bindings; restore that file, then run the installer again.")
text = bindings.read_text()
legacy_markers = ("-- BEGIN OmaFloat", "-- BEGIN Omarchy Float Video")
if any(marker in text for marker in legacy_markers):
    raise SystemExit("Return the video and remove the old plugin and shortcut block "
                     "before installing OmaPeek. See README.md upgrade instructions.")

subprocess.run(["omarchy", "plugin", "validate", str(package)], check=True)
if begin not in text:
    live_binds = json.loads(subprocess.check_output(["hyprctl", "-j", "binds"]))
    if any(b.get("modmask") == 69 and b.get("key", "").upper() == "P" for b in live_binds):
        raise SystemExit("Super+Ctrl+Shift+P is already assigned. Choose another shortcut first.")

backup.mkdir(parents=True)
shutil.copy2(bindings, backup / "bindings.lua")
if shell.exists():
    shutil.copy2(shell, backup / "shell.json")
if not managed and source != destination.resolve():
    if destination.exists():
        shutil.copytree(destination, backup / "plugin")
    shutil.copytree(source, destination, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(".git", "__pycache__", "artifacts"))
if begin not in text:
    bindings.write_text(text + "\n" + begin + '\n'
        'o.bind("SUPER + CTRL + SHIFT + P", "Float / return YouTube video", '
        '[[python3 "' + str(destination / "bin/omapeek") + '"]])\n' + end + '\n')
subprocess.run(["hyprctl", "reload"], check=True)
errors = subprocess.check_output(["hyprctl", "configerrors"], text=True).strip()
if errors and errors != "ok":
    shutil.copy2(backup / "bindings.lua", bindings)
    subprocess.run(["hyprctl", "reload"], check=True)
    raise SystemExit("Hyprland reported errors; restored bindings:\n" + errors)
subprocess.run(["omarchy-shell", "shell", "rescanPlugins"], check=True)
for attempt in range(3):
    # No section: a new entry uses the manifest's defaultSection; an existing one keeps its place.
    result = subprocess.run(["omarchy", "plugin", "enable", "io.github.cotopena.omapeek"])
    if result.returncode == 0:
        break
    # A plugin rescan can temporarily occupy the shell's IPC handler.
    if attempt == 2:
        raise SystemExit("Files installed; shell did not confirm activation. "
                         "Retry: omarchy plugin enable io.github.cotopena.omapeek")
    time.sleep(1)
try:
    ipc = subprocess.run(["omarchy-shell", "io.github.cotopena.omapeek", "status"],
                         capture_output=True, text=True, timeout=5).stdout
except (OSError, subprocess.TimeoutExpired):
    ipc = ""
if f'"version":"{version}"' not in ipc:
    # Quickshell can retain an old QML component after a plugin rescan.
    locked = subprocess.run(["omarchy-hyprland-session-locked"], capture_output=True)
    if locked.returncode == 0:
        print("Files installed. Unlock the desktop, then run: omarchy restart shell")
    else:
        subprocess.run(["omarchy", "restart", "shell"], check=True)
print(f"Installed OmaPeek {version}. Backups: {backup}")
if managed:
    print(f"Kept the plugin-manager copy in {destination}. "
          "Update it with: omarchy plugin update io.github.cotopena.omapeek")
print("Play a YouTube video, open OmaPeek in the bar, and choose Float video. "
      "Hover over the icon to see OmaPeek. Choose Restore original window to return it.")
print("Keyboard shortcut: Super+Ctrl+Shift+P. No browser extension setup is needed.")
