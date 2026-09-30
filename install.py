#!/usr/bin/env python3
"""Install the local Omarchy widget and an unused desktop shortcut."""
from datetime import datetime
from pathlib import Path
import json
import os
import shutil
import subprocess
import time

source = Path(__file__).resolve().parent
destination = Path.home() / ".config/omarchy/plugins/io.github.cotopena.omafloat"
bindings = Path.home() / ".config/hypr/bindings.lua"
shell = Path.home() / ".config/omarchy/shell.json"
stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
backup = Path.home() / ".local/state/omafloat/backups" / stamp
begin = "-- BEGIN OmaFloat"
end = "-- END OmaFloat"
text = bindings.read_text()
legacy_begin = "-- BEGIN Omarchy Float Video"
if legacy_begin in text:
    raise SystemExit("Return the video and remove the old Float Video shortcut block "
                     "and gus.float-video plugin before installing OmaFloat. See README.md.")

subprocess.run(["omarchy", "plugin", "validate", str(source)], check=True)
if begin not in text:
    live_binds = json.loads(subprocess.check_output(["hyprctl", "-j", "binds"]))
    if any(b.get("modmask") == 69 and b.get("key", "").upper() == "P" for b in live_binds):
        raise SystemExit("Super+Ctrl+Shift+P is already assigned. Choose another shortcut first.")

backup.mkdir(parents=True)
shutil.copy2(bindings, backup / "bindings.lua")
shutil.copy2(shell, backup / "shell.json")
if destination.exists():
    shutil.copytree(destination, backup / "plugin")
if source != destination.resolve():
    shutil.copytree(source, destination, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(".git", "__pycache__", "artifacts", "browser-extension"))
legacy = destination / "browser-extension"
if legacy.exists():
    shutil.rmtree(legacy)  # Already preserved in the plugin backup above.
if begin not in text:
    bindings.write_text(text + "\n" + begin + '\n'
        'o.bind("SUPER + CTRL + SHIFT + P", "Float / return YouTube video", '
        '[[python3 "' + str(destination / "bin/omafloat") + '"]])\n' + end + '\n')
subprocess.run(["hyprctl", "reload"], check=True)
errors = subprocess.check_output(["hyprctl", "configerrors"], text=True).strip()
if errors and errors != "ok":
    shutil.copy2(backup / "bindings.lua", bindings)
    subprocess.run(["hyprctl", "reload"], check=True)
    raise SystemExit("Hyprland reported errors; restored bindings:\n" + errors)
subprocess.run(["omarchy-shell", "shell", "rescanPlugins"], check=True)
for attempt in range(3):
    result = subprocess.run(["omarchy", "plugin", "enable", "io.github.cotopena.omafloat", "right"])
    if result.returncode == 0:
        break
    # A plugin rescan can temporarily occupy the shell's IPC handler.
    if attempt == 2:
        raise SystemExit("Files installed; shell did not confirm activation. "
                         "Retry: omarchy plugin enable io.github.cotopena.omafloat right")
    time.sleep(1)
shell_path = str(Path(os.environ.get("OMARCHY_PATH", "/usr/share/omarchy")) / "shell")
ipc = subprocess.run(["quickshell", "ipc", "-p", shell_path, "call", "io.github.cotopena.omafloat", "status"],
                     capture_output=True, text=True, timeout=5)
if '"version":"0.3.0"' not in ipc.stdout:
    # Quickshell can retain an old QML component after a plugin rescan.
    locked = subprocess.run(["omarchy-hyprland-session-locked"], capture_output=True)
    if locked.returncode == 0:
        print("Files installed. Unlock the desktop, then run: omarchy restart shell")
    else:
        subprocess.run(["omarchy", "restart", "shell"], check=True)
print(f"Installed OmaFloat. Backups: {backup}")
print("Play a YouTube video, then click the OmaFloat icon in the bar to float it. "
      "Hover over the icon to see OmaFloat. Click the icon again to restore it.")
print("Keyboard shortcut: Super+Ctrl+Shift+P. No browser extension setup is needed.")
