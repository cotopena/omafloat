# OmaFloat

Keep your video in view.

Keep a YouTube video in the corner while you work. Click the **OmaFloat icon** in the Omarchy bar to open Quick Controls, then choose **Float video** to shrink and pin your YouTube window. Choose **Restore original window** to return it. Hover over the icon to see the **OmaFloat** tooltip.

No Chrome extension installation, account, API key, or browser profile setup is needed.

## Use it

1. Open a video in the YouTube app or a Chromium window and start playback.
2. Click the **OmaFloat icon** and choose **Float video**, or press **Super + Ctrl + Shift + P** if you installed the shortcut.
3. Hover over the small video for YouTube's play/pause, volume, and seek controls. Choose **Restore original window** or press the shortcut again to restore its workspace and window mode.

The player starts at 600 × 338 in the bottom-right corner of your focused display. It remains visible when you switch workspaces on that display. Use your usual Omarchy window move/resize gestures to reposition it.

Keep the YouTube window open. Closing it stops playback. This plugin shrinks the existing window, so it cannot leave that same window available for browsing another page at the same time.

### Quick Controls

The popup shows the supported video window, its workspace, connected displays, and a schematic of its current geometry. Pick Small (400), Medium (600), or Large (800 pixels wide), a display, or any corner. Sizes are constrained to the display work area. The diagram is letterboxed to the display's logical aspect ratio; its quiet editor shapes are illustrative, not a live desktop capture. The video marker uses actual window position and size.

**Hide float** parks the window on a dedicated special workspace without stopping playback. **Show float** returns it. **Follow workspaces** pins the float on its display. **Keep above other windows** raises it once per second while the widget runs; Hyprland has no independent always-above flag, and another floating window can briefly cover it between raises. Turning this off stops raising; floating windows still normally sit above tiled windows. Other monitors' fullscreen windows and compositor overlays are not overridden.

Tab moves through controls, Enter/Space activates them, and Escape dismisses the popup. Dropdowns support arrow keys. Short popups scroll, including automatically revealing keyboard focus. Keyboard and IPC `toggle` retain the original float/restore behavior rather than toggling the menu.

### If fullscreen does not activate

The plugin uses YouTube's **F** shortcut. Start with the player selected, rather than a search field or comment box. If the small window shows the whole page, choose **Restore original window**, select YouTube's fullscreen button, then use **Super + Ctrl + Shift + P**. Browser extensions that intercept F can also affect automatic activation.

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
- If you manually exit fullscreen while floating, choose **Restore original window** before floating again.
- No network calls, browser debugging connection, downloaded video, or third-party player are used by the plugin.

## Development

```sh
omarchy plugin validate .
python3 -m unittest discover -s tests -v
python3 bin/omafloat status
python3 bin/omafloat restore
```

The helper accepts `--width 320..1200` and an explicit `--window 0x...` for testing. Controls use serialized commands:

```sh
python3 bin/omafloat float
python3 bin/omafloat configure --width 800 --corner top-left --monitor DP-1
python3 bin/omafloat configure --follow false --above false
python3 bin/omafloat hide
python3 bin/omafloat show
```

`status` returns the tracked/eligible window, monitor metadata, current visibility/pinning, and placement options without taking the mutation lock. User actions briefly wait for the controller lock (up to three seconds); background maintenance skips a busy lock. Mutations retain the original restoration snapshot; partial failures leave it available for retry. `maintain` is used by the running widget for stack-order enforcement.

See [the isolated preview guide](docs/PREVIEW.md) for QML validation and fixture screenshot generation. See [VERIFICATION.md](VERIFICATION.md) for the current test record.

## Remove

Return the video first. Disable/remove `io.github.cotopena.omafloat` through Omarchy's plugin manager. Remove the block between `-- BEGIN OmaFloat` and `-- END OmaFloat` in `~/.config/hypr/bindings.lua`, then run `hyprctl reload` and `hyprctl configerrors`.

## License

MIT.
