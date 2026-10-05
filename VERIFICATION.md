# OmaPeek verification

## OmaPeek package identity — 2026-10-05, 0.4.0

Renamed the product, repository references, plugin ID, IPC target, QML components, icon, controller, shortcut markers, preview asset, and runtime/hidden-workspace names to OmaPeek. Current package ID is `io.github.cotopena.omapeek`; source is `https://github.com/cotopena/omapeek`. Historical records below retain the names and paths actually tested at their recorded commits. The earlier live acceptance remains evidence for the pre-rename implementation, not a new browser acceptance run.

Rename checks: all 46 controller tests, plugin validation, whitespace checks, and isolated full-widget loading pass. QML lint completes with the previously documented dynamic-type metadata warnings.

The installed copy was migrated to `io.github.cotopena.omapeek` through the standard Git plugin installation path. The bar placement and existing shortcut were preserved, and the old installation/configuration/runtime directory were backed up under `~/.local/state/omapeek/backups/`. The new IPC target reports version `0.4.0`; plugin discovery shows OmaPeek enabled with no old plugin ID. `hyprctl reload` and `hyprctl configerrors` pass. This migration performed no browser or keyboard-input testing.

## Physical DP unplug and local recovery — 2026-10-05

At 11:31:49 EDT, the owner prepared a visible 600 × 338 YouTube PWA float on DP-1 at `[1300, 722]`, pinned with Follow and Above enabled. Physical DP removal at 11:37:24 reproduced the reported failure against the installed published code: the popup still opened, but the owner could not see the video. Hyprland retained the same mapped, floating, pinned browser window at the same coordinates, changed its monitor to `-1` and workspace to `3`, and reported `visible=true`. HDMI-A-1 was the only remaining output, with logical x bounds `[1920, 3840)`, so the video rectangle ending at x=1900 had no screen overlap. The compositor session and browser PID remained alive. This reproduction establishes an orphaned, offscreen float; `visible=true` alone does not establish that pixels are on a connected display.

The candidate helper and widget were backed up and copied into the existing user plugin installation while DP remained absent. The first candidate automatically journaled recovery but failed before moving: `window.pin` returned `Window has no monitor`. The coordinator then corrected the order to attach the window to the survivor **before** unpinning, and set `follow=False` on the monitor move as well as the workspace move. This agrees with the running Hyprland commit's [pin and workspace actions](https://github.com/hyprwm/Hyprland/blob/efb50993780079460b0cbed1363e2166a2de1d9f/src/config/shared/actions/ConfigActions.cpp) and [Lua move routing](https://github.com/hyprwm/Hyprland/blob/efb50993780079460b0cbed1363e2166a2de1d9f/src/config/lua/bindings/LuaBindingsDispatchers.cpp). A new regression models monitor `-1`, rejects pin changes before attachment, and checks silent movement with Follow both off and on. All **57 tests pass**.

After installing the corrected helper, **widget maintenance automatically recovered the existing video** at 11:40:07: HDMI monitor `0`, workspace `1`, `[3220, 722]`, unchanged 600 × 338 size, floating and pinned. No manual maintain command was used for the successful recovery. The saved original restore snapshot and options matched their pre-install backups exactly, the recovery journal cleared, and active keyboard focus remained on the same terminal. No browser input, drag, compositor restart, or monitor configuration change was used. Hyprland itself changed `fullscreenClient` from 2 to 0 during the unplug baseline; recovery did not change it further.

The owner confirmed the recovered video was **visible and playing** while DP remained disconnected. This proved the corrected helper recovered through maintenance with Above on; subsequent checks showed the running widget had retained its older QML despite matching candidate files on disk. Private event/snapshot evidence is in `/tmp/omapeek-hotplug-yn4lajn4/events.jsonl`; installed-file and runtime backups are under `~/.local/state/omapeek/backups/hotplug-20261005-hlmyhilt/`. Version is still 0.4.0. No commit, push, release or marketplace submission occurred.

### Above-off repeat and cached widget diagnosis

After reconnect, setup moved the same float to DP and disabled Above, restoring terminal focus afterward. Physical removal at 11:43:38 again left an orphaned monitor `-1` window offscreen. Recovery did not occur, so this repeat **failed**. The desktop locked at 11:44:25, after the failure had already been captured; the controller correctly skips maintenance during a session lock. DP reconnected at 11:45:44, later confirmed by the owner. Recovery must not be credited for this cycle.

Omarchy reported plugin reloads, but a new diagnostic IPC status probe still returned the old field set even after `rescanPlugins`, and new bar instances reported the old widget source location. After an unlocked `omarchy restart shell`, IPC returned the new `hidden`, `above` and `maintenanceEnabled` fields; with Above false, maintenance was confirmed enabled. This establishes that the updated widget had not been loaded by the earlier hot reload. The shell was restarted once; the compositor/browser were not restarted. When upgrading, verify the running widget rather than inferring it from installed file equality.

Reconnection exposed a second controller gap: monitor `-1` can persist even when its coordinates overlap the reconnected output. Recovery now also handles an orphaned float with screen overlap, while preserving accessible placements with a valid monitor. Hyprland treats moving to the same workspace as a no-op, so an orphan on the target output's active workspace first moves silently through another active workspace. With only one output, a temporary unused normal workspace is selected above the existing workspace IDs, then the float moves to the target workspace; no workspace is activated. The final move, pinning and geometry steps retain the pending recovery journal and immutable original snapshot. A regression models overlap, pin rejection without attachment, same-workspace no-op, one/two-output paths, and silent moves. All **58 tests pass**.

The original video window was no longer present by 11:48:47, before the reconnect correction could be accepted. At 12:22 the coordinator confirmed no eligible video, both outputs connected, matching latest installed helper/widget files and the fresh widget IPC fields. Logging was restarted for a new owner-selected video.

### Fresh widget automatic recovery: PASS with Above off

The owner reopened and floated a new YouTube PWA. At 12:24 the coordinator confirmed it was visible on DP-1 at `[1300, 722]`, 600 × 338, floating/pinned, with Follow on. Above was temporarily disabled without changing focus, and **running widget IPC confirmed `above=false` and `maintenanceEnabled=true` before unplug**. The owner physically removed DP at 12:24:59.553. The event log shows the same window moving onto HDMI at 12:24:59.835, about 0.28 seconds after removal, then finishing pinned on workspace `1`, `[3220, 722]`, 600 × 338. No manual maintenance/recovery command or shell restart was issued for this test. The owner confirmed the video appeared automatically.

Readback confirmed the same address/PID/stable ID, unchanged original restore snapshot, unchanged size/Follow setting, cleared recovery journal, and unchanged keyboard focus. Above was restored to its original enabled setting afterward. This **passes the reported visible-video unplug recovery with the corrected helper and fresh widget, including Above off**. Evidence: `fresh-repeat-before.json`, `fresh-repeat-after.json` and `events.jsonl` in the private directory listed above.

### Restore with the original display absent: PASS

With DP still absent, the owner clicked Restore original window and confirmed the normal browser on its original workspace `10`. At 12:27, readback confirmed the same address/PID/stable ID on HDMI, tiled, unpinned, mapped, not hidden, with fullscreen modes 0/0 matching the original snapshot. Its tiled rectangle `[1932, 38]`, 1896 × 1030, was inside HDMI's current bounds. The current runtime snapshot was removed and plugin status became inactive. Evidence: `missing-display-restore-after.json`.

### Physical shortcut: PASS

The owner focused the normal YouTube window and pressed Super + Ctrl + Shift + P, confirming that it floated. Readback verified the same window active, floating/pinned at 600 × 338 on HDMI, Follow and Above enabled. DP was still absent, so this establishes physical shortcut delivery and controller activation, not monitor reconnection.

### Hidden hotplug with Follow off: PASS

After DP was physically reconnected and confirmed present, the coordinator placed the tracked float on DP, disabled Follow, and hid it using the controller. At 12:28:53 it was floating/unpinned on `special:omapeek-hidden`, with its visible destination saved as DP/workspace `2`, geometry `[1300, 722]`, 600 × 338. The original restore snapshot was unchanged. DP removal at 12:29:23 left it on the hidden workspace; the event log shows it stayed hidden until the owner explicitly clicked **Show float** on the surviving HDMI bar at 12:30:30. The owner confirmed it appeared and played.

Readback verified the same address/PID/stable ID, HDMI monitor `0`, active workspace `1`, `[3220, 722]`, unchanged size, floating/unpinned with Follow still off, updated visible destination and unchanged original snapshot. Follow and Above were restored to their original enabled settings afterward. Evidence: `hidden-hotplug-before.json`, `hidden-hotplug-ready.json`, `hidden-hotplug-after.json` and `events.jsonl`.

### Final reconnect and both bar menus: PASS

The owner reconnected DP and confirmed both monitors' OmaPeek menus opened with matching settings. By final capture the same video had returned to a normal tiled/unpinned browser on HDMI/workspace `10`, and runtime state was cleared; both outputs were connected and fresh widget IPC correctly reported inactive/not hidden with maintenance disabled. This final normal-browser state was left in place. Installed production files matched the tested checkout. The temporary monitor observer was stopped; evidence and backups were retained. Evidence: `reconnect-final.json`. At the end of this acceptance run, the fix was installed locally and repository changes were uncommitted/unpushed. Marketplace submission was not performed.

The orphan-on-reconnect correction has unit coverage but has not been reproduced against the final running candidate; complete mixed-scale/rotation/hardware and native keyboard-focus matrices remain outside this acceptance. No compositor-crash fix is established.

## Offline hotplug recovery diagnosis — 2026-10-05, initial candidate

The owner reported that unplugging a monitor made the video inaccessible while the popup still opened; reconnecting made it reappear on the main display. This report is not yet reproduced with this candidate. The coordinator separately observed a new Hyprland session with no YouTube client and the saved old browser PID dead; that state is not the original reproduction. Crash analysis reported an 11:02:13 segfault/handler abort in `CDwindleAlgorithm::movedTarget → setFloating → dragEnd/dragBegin → mouse keybind`, with both connectors connected in the log tail, followed by a safe-mode exit crash and no OOM. Neither crash is attributed here to OmaPeek or hotplug. This follow-up used code inspection and offline tests only; no desktop control, configuration changes, installation or browser interaction occurred.

**Code-backed failure scenario:** unchanged HEAD's `maintain` only raises a visible float, and `show` returns immediately unless the window is on OmaPeek's hidden special workspace. If unplug/re-layout leaves a tracked floating window's absolute content rectangle outside all connected displays, maintenance never makes it reachable; a stale monitor ID instead produces an error. Above-off prevents the widget from scheduling maintenance at all, and hotplug events previously scheduled status refresh without explicitly requesting maintenance. Separately, hidden Show trusts saved absolute geometry when the output name survives, even if its origin/scale changed. The new tests fail against unchanged HEAD (7 assertion failures and 8 stale-monitor errors across the three core scenario tests; local output `/tmp/omapeek-offline-hotplug-baseline.txt`). This establishes missing recovery behavior, not the live root cause.

**Candidate design:** `geometry_visible` (`bin/omapeek:132`) computes content intersection with usable logical monitor bounds, including scale, rotation, origin and reserved areas. `reconcile_visible` (`bin/omapeek:392`) only rescues tracked, non-hidden, floating content with zero usable overlap on every connected display (or resumes its already-journaled partial rescue). Any accessible manual placement, including partial/off-edge or cross-display overlap, is left untouched. It prefers the current surviving monitor, otherwise a focused/available survivor, and recomputes the selected corner/size with existing fit limits. Existing-monitor recovery preserves a Follow-off workspace; when the owning monitor is gone, recovery uses the survivor's active workspace. Follow pinning is restored independently of Above. Above-off never raises; no focus, fullscreen or media-key operation is added. With no outputs, maintenance waits for a later attempt. This conservative policy deliberately does not recenter partially visible windows or recover a destroyed/dead browser.

Recovery journals `visible_destination`, removal of obsolete `visible_geometry`, and an optional validated `recovery_pending` flag before any dispatch. The immutable `original`, restoration monitor and option values remain intact. The flag is cleared only after geometry/pin completion; a retry finishes even if a partial monitor move already made content visible. Deliberate Hide/configuration commands supersede the pending rescue. Ordinary hidden maintenance does not reveal or move the window. Hidden Show retains its destination/Follow-off behavior and saved manual geometry when that geometry intersects the selected output, otherwise uses fresh corner geometry after an origin/scale/layout shift. Existing hidden-disconnect and hidden-display-selection regressions still pass.

`OmaPeekWidget.qml:113` now enables visible-float maintenance regardless of Above. Its production event handler at line 125 explicitly restarts the 200ms maintenance timer for monitor add/remove events (both event-name variants) without requiring an active/Above transition. Owner election/busy checks still gate execution; a busy operation may defer recovery to a later event/status transition or the 12-second safety timer. The maintenance exit refreshes/broadcasts status. Pure output geometry changes without a hotplug event remain covered by the 12-second fallback. No new recovery UI/action is introduced: automatic narrow reconciliation plus the existing non-hidden CLI Show path covers the demonstrated code scenarios.

**Offline validation:** all **56 controller tests pass** (10 new tests); every compositor/controller subprocess remains mocked, with the new widget scheduling test executing the actual QML handler/maintenance predicate in Node with timer spies. Coverage includes absent versus reassigned monitor IDs, Follow/Above combinations, idempotence, negative/shifted origins, fractional/high scale, rotation, unchanged accessible manual placements, hidden/tiled exclusion, zero-output transitions, saved hidden geometry after layout shifts, journal-before-dispatch, partial failure/retry, no focus stealing command, and explicit Hide superseding recovery. Qt offscreen keyboard/accessibility checks pass; Python compilation, manifest validation, whitespace checks and QML lint pass with existing dynamic metadata warnings. Logs: `/tmp/omapeek-offline-hotplug-tests.txt`, `/tmp/omapeek-hotplug-qmllint.log`.

**Release recommendation:** hold release acceptance pending the coordinator/owner's physical reproduction and validation. This is an uninstalled, uncommitted candidate. Validate the original unplug scenario with a live browser, capturing client identity/geometry, monitor logical bounds, Follow/Above, workspace and runtime state before/after. Test Above off and on, survivor origin/scale/layout shifts, and hidden Show separately. Confirm recovery scheduling, reachable content, preserved restore snapshot and successful reconnect/bar ownership. Do not claim a crash fix, physical hotplug pass, shortcut pass or recovered browser authentication from these offline results.

## Earlier release confidence follow-up — 2026-10-05, before owner hotplug report

At this earlier check, no production defect was reproduced; production QML/controller files and the installed copy were unchanged. In particular, absence of `onClosed` in `OmaPeekDropdown.qml` is not a demonstrated bug: Qt returns focus to its trigger automatically in the isolated tests below. No new global/synthetic desktop keyboard input or browser automation was used.

**Isolated Qt keyboard passes:** `python3 tools/preview-qml.py --keyboard-check --height 320 --output /tmp/omapeek-keyboard-short.png` and the same check at default height with `--accessibility-check` pass. The new `tests/KeyboardChecks.qml` uses QtTest events confined to an offscreen QQuickWindow containing the production `ControlsViewport`/controls. It starts at the panel's viewport focus target, Tabs to the first action, traverses all 13 controls forward and backward, checks forward wrap, and confirms every forward-focused control is scrolled into view at 320px. Return, keypad Enter and Space each emit exactly one expected command from visibility, all three size presets, all four corner buttons, both toggles and Restore. Display/Placement dropdown opening, Up/Down selection, Return routing, Escape dismissal, reopening and trigger focus restoration pass. Changing fixture monitor readback (including portrait geometry) preserves trigger focus and subsequent Tab order. This is simulated controller readback, not physical window movement or live layer-shell keyboard acquisition. The helper is never invoked. Accessibility/disabled-action checks also pass. The harness fails on exceptions or a missing success marker.

**Real Hyprland stacking pass with neutral fixtures:** two solid-color Quickshell floating windows owned by one exact recorded PID/address set were overlapped on the current display. Three trials focused/raised the blue competitor, ran the production `Controller.configure(..., action="maintain")` with Above false, then with Above true. A 1px capture wholly inside their shared content stayed blue with Above off and became red with Above on. The competitor retained keyboard focus throughout maintenance. This exercises the real production identity validation and `window.alter_zorder` dispatch at `bin/omapeek:50`, via the maintenance branch at `bin/omapeek:404` (line references at tested commit f2e965b); no real browser was targeted. It proves maintenance can correct overlap, not that the installed widget's event/timer scheduling always invokes it promptly. Local snapshots, exact owned identities, nine pixel samples and results are in `/tmp/omapeek-confidence-20261005-37h7k05w/`. No desktop/incident captures were added to the repository.

Both fixture windows were terminated through their owned process. Original focus, cursor, both monitor workspaces and every pre-existing client's address/PID, geometry, workspace, floating/pinned/fullscreen modes were verified restored. Real plugin runtime JSON remained byte-for-byte unchanged. Focusing windows caused compositor cursor warps; the original cursor was explicitly restored with `hl.dsp.cursor.move`, then read back. No configuration edits, monitor disabling, shell restart, input daemon, privileges, account/profile changes, commit, push or publication occurred.

**Shortcut evidence:** source and installed helper/manifest/panel/dropdown match. The current configured Super+Ctrl+Shift+P command points to the installed helper; live Hyprland binds contains the OmaPeek binding on P with modmask 69. This verifies registration only. Its physical execution remains unverified; no global chord was injected.

**Release recommendation at this stage:** suitable for owner acceptance; hold an unconditional “all live checks passed” claim until these remaining checks are completed. The later physical-test records above supersede the single-shortcut and unplug/hidden/Restore gaps within their stated coverage; full keyboard traversal, three physical shortcut cycles and actual-video competing-window scheduling remain unverified:

1. With the popup visibly focused, physically Tab/Shift+Tab through controls; activate sizes and toggles, select each dropdown, then continue Tab after selection and after moving the float to the other monitor. Confirm the intended control retains focus and keys never reach another app. Isolated Qt passes do not prove layer-shell/compositor routing.
2. From a deliberate, safe desktop focus target, physically press Super+Ctrl+Shift+P for three float/restore cycles. Confirm one action per press, no unrelated application input, and original layout restored. The owner must choose the browser/video and record initial player/authentication state; the earlier incident's unknown playback/authentication state cannot be reconstructed here.
3. Overlap a neutral floating window with the actual video; enable Above, raise/focus the competitor and confirm OmaPeek maintenance returns the video above it without stealing focus (allow the documented 12-second fallback). Disable Above and confirm the competitor can remain above. Neutral production-dispatch evidence does not replace this installed-widget scheduling check.
4. Physically unplug the float's display, check surviving bar ownership/readback and usable controls, Restore with the original display absent, then reconnect and verify one functional owner per bar and no stale popup. Repeat with the float hidden and Follow off. This requires the owner/hardware; simulated readback and controller missing-monitor unit tests do not prove hotplug.

The earlier sign-out incident remains recorded below. Any desired sign-in recovery is a separate user-only action; this follow-up did not inspect or alter browser authentication.

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
