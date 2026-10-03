# OmaFloat verification

## Quick Controls — 2026-10-03

The native menu, placement schematic, and controller commands pass 37 controller tests, plugin validation, QML lint with documented metadata warnings, and isolated QML rendering. Runtime checks cover accessible control roles/actions, disabled actions, dropdown state readback, and keyboard focus scrolling to Restore at a 320px height. The complete widget also loads in an isolated Wayland process with a fixture helper.

See [preview and verification instructions](docs/PREVIEW.md) for commands, review regressions, and the implementation screenshot. The screenshot uses sample status data. This change has not been installed or exercised against a live browser; compositor/browser acceptance remains outstanding.

## Historical verification — 0.3.1 code review fixes

Changes: `status` no longer takes the toggle lock, so bar polling cannot drop a click or shortcut press. The bar refreshes on Hyprland window events, with a 30-second fallback poll, instead of every two seconds. After a toggle, all monitors refresh. Unexpected errors now show a notification. A failed refocus no longer hides the original error. The installer handles a missing `shell.json`, leaves a plugin-manager checkout untouched, and checks the IPC version through `omarchy-shell`. Its version now comes from `manifest.json`. The manifest adds bar widget aliases.

Second review round:

- Returning a video that was already in YouTube player fullscreen no longer clears client fullscreen first. Previously that could make Chromium leave the player's fullscreen.
- Named workspaces use a `name:` selector when floating and returning. A negative id is no longer sent, which Hyprland would read as a relative move.
- Each dispatch checks Hyprland's `ok` result and raises on failure, including warning-level failures that `hyprctl` reports with exit 0. Unpin is sent only to a pinned window, because unpinning an unpinned window is itself a warning-level failure.
- Restore re-reads the window and confirms floating mode, pin state, and workspace before clearing its state. If any of these do not match, the state is kept so the next click retries.
- The installer enables the widget without a section. A fresh install uses the manifest's default (right), and an existing placement is kept.
- A missing or slow `notify-send` no longer crashes the error handler.
- An originally pinned window passes the restore check on the monitor's active workspace, because Hyprland re-pinning moves it there. The workspace is still checked for unpinned windows, so a retry loop after switching workspaces is gone.

Verified in this worktree:

- `python3 -m unittest discover -s tests -v`: 23 tests pass. New tests cover lock-free status, the toggle debounce, a missing monitor, unexpected-error notification, refocus failure during rollback, widget/manifest version agreement, preserved client fullscreen when returning a pre-fullscreen video, named-workspace selectors, the generated dispatch result check, pin-only-when-pinned, a failed restore postcondition keeping state (mode change or workspace move), a pinned window returning after a workspace switch, and best-effort notifications. Every test now fails if it reaches a real subprocess.
- The generated dispatch Lua was checked offline with `lua5.4` against a stub `hl` table that returns `ok=false`. It raises `window.pin: <error>`.
- `omarchy plugin validate .` passes.
- `qmllint` on both QML files reports only unresolved `qs.*` imports, unqualified host singletons, and the existing Quickshell `QProcess::ExitStatus` type-info warning. `Quickshell.Hyprland` resolves.
- `python3 bin/omafloat status` prints `{"active": false}` without touching the desktop.

Not verified: this release has not been installed, enabled, or visually tested on the live desktop. The installer was not run. These still need a live desktop check:

- the already-fullscreen float/return cycle, confirming the returned window shows the player in fullscreen rather than the whole page;
- the new dispatch-result enforcement against real Hyprland results, including that no required step returns `ok=false` in normal float/return cycles;
- the event-driven refresh, the multi-monitor broadcast, the plugin-manager install path, and placement being kept on re-enable.

## Historical verification — 0.3.0 naming and release preparation

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
