# OmaFloat

Keep your video in view.

Keep a YouTube video in the corner while you work. Click the **OmaFloat icon** in the Omarchy bar to shrink and pin your YouTube window; click it again to restore it. Hover over the icon to see the **OmaFloat** tooltip.

No Chrome extension installation, account, API key, or browser profile setup is needed.

## Use it

1. Open a video in the YouTube app or a Chromium window and start playback.
2. Click the **OmaFloat icon** in the Omarchy bar, or press **Super + Ctrl + Shift + P** if you installed the shortcut.
3. Hover over the small video for YouTube's play/pause, volume, and seek controls. Click the icon again or press the shortcut again to restore its workspace and window mode.

The player starts at 600 × 338 in the bottom-right corner of your focused display. It remains visible when you switch workspaces on that display. Use your usual Omarchy window move/resize gestures to reposition it.

Keep the YouTube window open. Closing it stops playback. This plugin shrinks the existing window, so it cannot leave that same window available for browsing another page at the same time.

### If fullscreen does not activate

The plugin uses YouTube's **F** shortcut. Start with the player selected, rather than a search field or comment box. If the small window shows the whole page, click the **OmaFloat icon** to restore it, select YouTube's fullscreen button, then use **Super + Ctrl + Shift + P**. Browser extensions that intercept F can also affect automatic activation.

## Install locally

Requires Omarchy's Quickshell plugin system, Hyprland with the Lua dispatcher API (developed against 0.56.2), Python 3, and a Chromium-based browser. Firefox and other video sites are not supported by this version.

### Option A: plugin manager (recommended)

```sh
omarchy plugin add https://github.com/cotopena/omafloat --enable
```

This installs and enables the bar widget. It does not add a keyboard shortcut. To add the optional shortcut, run the installer from the installed plugin:

```sh
python3 ~/.config/omarchy/plugins/io.github.cotopena.omafloat/install.py
```

The installer keeps the widget where you placed it in the bar. It does not change the plugin-manager files, so `omarchy plugin update io.github.cotopena.omafloat` keeps working.

### Option B: from a clone

```sh
git clone https://github.com/cotopena/omafloat
cd omafloat
python3 install.py
```

The installer validates the plugin, copies it to `~/.config/omarchy/plugins/io.github.cotopena.omafloat`, enables it (a fresh install goes in the right section of the bar; an existing widget keeps its placement), and adds the Super + Ctrl + Shift + P shortcut to `~/.config/hypr/bindings.lua` if that shortcut is free. Existing plugin files, shell settings, and bindings are backed up under `~/.local/state/omafloat/backups/` before anything is written. To update, pull the clone and run the installer again.

Run the installer while your desktop is unlocked. If the bar retains old code after an upgrade, run:

```sh
omarchy restart shell
```

No setup is required in `chrome://extensions`.

## Marketplace package

`manifest.json` and `OmaFloatWidget.qml` are at the package root; `bin/omafloat` is resolved relative to the widget. The bar works when the plugin is installed and enabled through Omarchy's plugin system. `install.py` additionally installs the optional desktop shortcut.

Source: [cotopena/omafloat](https://github.com/cotopena/omafloat). The marketplace listing is pending submission and review.

### Upgrade from Float Video

Return any floating video first. Remove the old `gus.float-video` plugin through the plugin manager. If you installed its keyboard shortcut, remove the block between `-- BEGIN Omarchy Float Video` and `-- END Omarchy Float Video` from `~/.config/hypr/bindings.lua`, then run `hyprctl reload` and `hyprctl configerrors`. Install OmaFloat using either method above. The installer refuses to replace an existing legacy shortcut automatically. Existing backups remain under `~/.local/state/omarchy-float-video/backups/`.

Version 0.2 replaced the old companion-based prototype, and OmaFloat does not use a browser extension. Any extension previously loaded manually for Float Video can be removed separately in Chromium.

## Behavior and limits

- Chooses the most recently focused supported YouTube window. A video must be the selected tab in a regular browser window.
- Keeps the same video session and playback position, using YouTube's fullscreen player inside a floating window.
- Saves the original workspace, monitor, floating geometry, pin status, fullscreen flags, and fullscreen synchronization setting. A tiled window returns to tiling, though its exact slot may change.
- Restores existing fullscreen state if YouTube was fullscreen before activation.
- Rejects grouped windows and special workspaces. Unlock the desktop before activating it.
- State is local to the current Hyprland session. Closed windows are matched by address, process, and stable ID so a reused address does not affect another app.
- If you manually exit fullscreen while floating, click the **OmaFloat icon** to restore it before floating again.
- No network calls, browser debugging connection, downloaded video, or third-party player are used by the plugin.

## Development

```sh
omarchy plugin validate .
python3 -m unittest discover -s tests -v
python3 bin/omafloat status
python3 bin/omafloat restore
```

The helper accepts `--width 320..1200` and an explicit `--window 0x...` for testing. See [VERIFICATION.md](VERIFICATION.md) for the current test record.

## Remove

Return the video first. Disable/remove `io.github.cotopena.omafloat` through Omarchy's plugin manager. Remove the block between `-- BEGIN OmaFloat` and `-- END OmaFloat` in `~/.config/hypr/bindings.lua`, then run `hyprctl reload` and `hyprctl configerrors`.

## License

MIT.
