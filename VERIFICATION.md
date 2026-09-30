# OmaFloat verification

## 0.3.0 — naming and release preparation

Renamed the package to OmaFloat, plugin ID to `io.github.cotopena.omafloat`, widget to `OmaFloatWidget.qml`, and helper to `bin/omafloat`. The controller retains its legacy runtime state directory for compatible restore state and locking. No playback or window-control behavior was changed.

Validated the renamed manifest and ran all eleven controller tests. The installed desktop remains on Float Video 0.2.1; this release has not been installed or visually tested on the live desktop. The optional installer refuses an existing legacy shortcut and documents the manual upgrade steps.

The record below describes the earlier 0.2.1 desktop checks and does not assert fresh visual verification of 0.3.0.

## Historical verification — 0.2.1

## 2026-09-30 repeat-toggle fix

Reproduced the reported failure: the first float succeeded, restore returned the video to normal, and the next float rolled back while waiting for a fresh Chromium fullscreen event.

The helper now establishes client fullscreen explicitly after enabling floating mode. Hyprland clears the client fullscreen flags when float mode changes. A missing fresh fullscreen event no longer aborts the toggle.

### Passed

- Eleven controller tests, including a regression for missing client fullscreen events and the float/fullscreen transition order.
- Omarchy manifest validation and Hyprland configuration validation.
- Installed version 0.2.1 loaded after a shell restart; IPC reports the new version.
- Repeated float/return/float cycles on the live personal YouTube app, using both the helper and installed bar IPC action.
- Visual desktop captures show the fullscreen video within a 600 × 338 floating window. Client fullscreen remains 2 and the window is pinned.
- Returning restores workspace 7, tiled mode, unpinned state, and fullscreen 0/0.
- The bar reports Return video while floating and Float video after returning.
- Playback continued through the cycles. Pause and resume were verified using the player's K shortcut and the video element's paused/currentTime values.
- Source and installed executable/widget/manifest files match. The desktop shortcut points to that installed helper.

The physical keyboard chord still needs a user check; its configured command is the tested helper. Browser inspection temporarily displays a debugging banner in captures.

### Remaining release checks

- Test installation through a published git repository on a second Omarchy machine.
- Check additional Chromium/browser-extension combinations and keyboard focus in search/comment inputs. If F is intercepted, the small window can show the entire page; the README explains how to return and select fullscreen explicitly.

No marketplace submission or public publishing has been performed.

Backups for this fix: `~/.local/state/omarchy-float-video/backups/20260930-141519/` and `20260930-142024/`.
