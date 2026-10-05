# OmaPeek verification

## OmaPeek package identity — 2026-10-05, 0.4.0

Renamed the product, repository references, plugin ID, IPC target, QML components, icon, controller, shortcut markers, preview asset, and runtime/hidden-workspace names to OmaPeek. Current package ID is `io.github.cotopena.omapeek`; source is `https://github.com/cotopena/omapeek`. Historical records below retain the names and paths actually tested at their recorded commits. The earlier live acceptance remains evidence for the pre-rename implementation, not a new browser acceptance run.

Rename checks: all 46 controller tests, plugin validation, whitespace checks, and isolated full-widget loading pass. QML lint completes with the previously documented dynamic-type metadata warnings.

The installed copy was migrated to `io.github.cotopena.omapeek` through the standard Git plugin installation path. The bar placement and existing shortcut were preserved, and the old installation/configuration/runtime directory were backed up under `~/.local/state/omapeek/backups/`. The new IPC target reports version `0.4.0`; plugin discovery shows OmaPeek enabled with no old plugin ID. `hyprctl reload` and `hyprctl configerrors` pass. This migration performed no browser or keyboard-input testing.

## Live acceptance — 2026-10-05, df353ad

Tested the installed plugin against Hyprland 0.56.2 and the existing Chromium YouTube app on two 1920 × 1080 displays (HDMI-A-1 and DP-1). Controller dispatches here were real, not mocks. Local evidence is retained in `/tmp/omafloat-live-20261005/`; captures include unrelated desktop content and are intentionally not published in the repository.

Passed:

- Native bar click opens Quick Controls; repeated same-icon click closes it through the popup dismissal layer. Outside click closes it, and clicking the other display's bar opens a peer popup with matching float size, corner, display, Follow and Above readback.
- Native Hide/Show buttons change actual visibility; display dropdown selects DP-1 and updates actual placement/readback. Escape dismissed the layer, confirmed by layer inventory. Initial apparent Tab focus is superseded by the additional keyboard observations below; full Tab traversal was not established.
- Real controller placement covers widths 400, 600, 800 (heights 225, 338, 450) at all four corners. Moving between both displays passes. Hide, change display while hidden with Follow off, then Show returns to the selected display/workspace.
- Follow off unpins; Follow on pins and tracks an actual workspace change. Above off/on and maintenance return successfully with correct option readback. A competing-window stacking check was attempted but remained inconclusive because input/focus and browser navigation interfered.
- Three consecutive normal float/restore cycles return to tiled, unpinned workspace 10 with fullscreen 0/0; floating establishes client fullscreen 2 each time. A separate cycle begun in actual YouTube player fullscreen returns to fullscreen 2/2, with a capture showing the fullscreen player.
- The session began with an active tracked float. Its original runtime snapshot/restore target was preserved byte-for-byte. Final window position/size, floating/pinned/fullscreen states, Follow/Above options, both monitor workspaces, focus and cursor match the initial state. The final state remains an active 400 × 225 top-right float, not a tiled restored window.

Input tooling and limits:

- `send_key_state` mouse down/up calls returned success but did not exercise the layer-shell bar. Native clicks were completed using a short-lived unprivileged `zwlr_virtual_pointer_v1` client compiled from the official Hyprland v0.56.2 protocol XML. Cursor readback confirmed requested global coordinates; each invocation released the button and disconnected. No daemon, installation, root/input permission change, remote-debugging port, or process restart was used. Existing browser-extension automation was used only during final browser recovery.
- An early IPC-open plus immediate synthetic Tab/Return reached an unrelated terminal pane and submitted an existing unfinished draft. The other agent responded with clarification only. After confirming that the pane was idle, its input was empty, and no newer input followed, the original draft was restored without Enter and verified unsent. No unrelated project files were touched. This input incident does not establish a plugin keyboard defect. Full keyboard traversal and screen-reader behavior remain unverified. The configured shortcut was attempted with synthetic input, but no toggle was verified; it is inconclusive. Widget IPC toggle activation was not exercised; normal cycles used the controller CLI.
- Physical monitor disconnection/reconnection, bar-owner replacement on hotplug, and missing-monitor restoration remain hardware-only unverified checks. No monitor was disabled to simulate unplugging. Peer readback does not prove hotplug ownership handoff.
- This is one installed desktop/browser combination, not fresh-machine installation coverage. No marketplace submission, commit or push was performed.

### Additional runtime checks and incident — 2026-10-05

Same-display corner dropdown Down/Enter selected bottom-left with real controller readback. Display dropdown Down/Enter selected DP-1. Subsequent Tab focus did not provide reliable per-control evidence; full traversal and keyboard size activation remain inconclusive. Bulk keyboard input reached Chromium UI, and the original tab navigated to Google's “Signed out – syncing is paused” landing page. No sign-in or account repair was attempted. The recorded exact original video URL was reopened in the same original tab to restore the video view; the browser sign-out/sync side effect is not reversed by compositor restoration. The unrelated unfinished draft was separately restored unsent as described above.

The live Super+Ctrl+Shift+P binding matches the installed helper, but synthetic chord attempts did not produce a verified toggle; physical shortcut activation remains unverified. A temporary Foot window was created and removed for overlap checks. Above off/on readback passed, but browser focus/navigation interference prevented a clean stacking verdict; keep-above competing-window behavior remains inconclusive. No further keyboard/control experiments were continued after the stop instruction.

Final browser recovery: the observed landing page title was `Signed out – syncing is paused`, at `https://accounts.google.com/signout/chrome/landing` (query omitted). After reopening the recorded video in the same original tab, YouTube displayed a Sign in link. This confirms the current signed-out state; initial authentication state was not captured, so its exact change and cause are not proven. Authentication was not restored. Any desired sign-in is a user-only recovery step. No credentials, cookies or account/profile settings were handled. The recorded video is playing again (read-only video state reported paused=false, time advancing near the beginning), but its original playback position is unknown. The player-only presentation was restored, followed by the initial 400 × 225 geometry, pinned/floating and 0/0 fullscreen flags, saved runtime snapshot, focus/cursor and workspaces. The temporary terminal is gone and plugin popup closed. Browser automation's temporary debugging banner was cancelled during cleanup.

## Historical Quick Controls — 2026-10-03

Outstanding live checks in this historical entry are superseded by the dated live acceptance record above, within its stated coverage and limits.

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
