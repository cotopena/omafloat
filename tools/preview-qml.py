#!/usr/bin/env python3
"""Render the real QuickControls component using fixture data, never hyprctl mutations."""
import os
from pathlib import Path
import subprocess
import tempfile
import argparse
import json

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, default=root / 'docs/screenshots/omapeek-quick-controls.png')
parser.add_argument('--width', type=int, default=360)
parser.add_argument('--height', type=int, default=760)
parser.add_argument('--monitor-width', type=int, default=1920)
parser.add_argument('--monitor-height', type=int, default=1080)
parser.add_argument('--runtime-check', action='store_true', help='Load the complete widget hidden on Wayland; no window dispatches')
parser.add_argument('--focus-restore', action='store_true', help='Verify focus scrolls Restore into view')
parser.add_argument('--accessibility-check', action='store_true', help='Assert actual control roles, names, state, actions and disabled guards')
parser.add_argument('--keyboard-check', action='store_true', help='Deliver QtTest keys only to an offscreen fixture window')
parser.add_argument('--maintenance-budget-check', action='store_true',
                    help='Count helper spawns per event for 1/2 offscreen bars with a fake helper and stub panel')
parser.add_argument('--lint', action='store_true')
args = parser.parse_args()


def maintenance_budget_check():
    """Run the real widget offscreen; the helper only logs and prints fixture status."""
    from collections import Counter
    from concurrent.futures import ThreadPoolExecutor
    # Offscreen has no PanelWindow backend; keep the panel's open/refresh contract.
    panel = ('import QtQuick\nItem { property var bar; property var anchorItem; property var hostWidget; '
             'property bool opened: false; property bool popoutSwitchClosing: false; '
             'function open() { opened = true; hostWidget.refreshStatus() } function close() { opened = false } '
             'function toggle() { opened ? close() : open() } function closeForPopoutSwitch() { close() } }\n')

    def run(bars, above, event=None, quit_ms=6500, open_at=None, opener=0):
        with tempfile.TemporaryDirectory(prefix='omapeek-budget-') as temp:
            base = Path(temp)
            for module in ('Ui', 'Commons'):
                (base / module).symlink_to(Path('/usr/share/omarchy/shell') / module)
            for name in ('OmaPeekWidget.qml', 'OPeekIcon.qml'):
                (base / name).symlink_to(root / name)
            (base / 'OmaPeekPanel.qml').write_text(panel)
            (base / 'runtime').mkdir(mode=0o700)
            log = base / 'spawns.log'
            status = dict(active=True, hidden=False, follow=True, above=above, options=dict(above=above),
                          window=dict(monitor=1, at=[1, 2], size=[600, 338]))
            helper = base / 'fixture-helper'
            helper.write_text(f"import json, sys, time\nopen({str(log)!r}, 'a').write('%.3f %s\\n' % (time.time(), ' '.join(sys.argv[1:])))\n"
                              f"if sys.argv[1:] == ['status']: print(json.dumps({status!r}))\n")
            ids = [f'w{i}' for i in range(bars)]
            every = '[' + ', '.join(ids) + ']'
            stale = 'function(w) { w.details = Object.assign({}, w.details, {window: {monitor: 99}}) }'
            widgets = '\n'.join(f'  OmaPeekWidget {{ id: {i}; visible: false; helper: {json.dumps(str(helper))}; bar: fakeBar }}'
                                 for i in ids)
            inject = '' if event is None else f'{every}.forEach(function(w) {{ w.handleEvent({{name: {json.dumps(event)}}}) }})'
            # Opening a menu: stale its state, open it, then stale it again (a geometry-only
            # recovery emits no event) so only the open-menu polling can refresh it.
            opening = '' if open_at is None else f'''
  Timer {{ interval: {3000 + open_at}; running: true; onTriggered: {{ ({stale})(w{opener}); w{opener}.open() }} }}
  Timer {{ interval: {3000 + open_at + 1200}; running: true; onTriggered: ({stale})(w{opener}) }}'''
            (base / 'shell.qml').write_text(f'''import QtQuick
import Quickshell
ShellRoot {{
  QtObject {{ id: fakeBar; property color barForeground: "white"; property var items: []
    function moduleWidgets(id) {{ return items }} }}
{widgets}
  Component.onCompleted: fakeBar.items = {every}
  Timer {{ interval: 3000; running: true; onTriggered: {{ {every}.forEach({stale}); console.log("INJECT " + (Date.now() / 1000).toFixed(3)); {inject} }} }}{opening}
  Timer {{ interval: {quit_ms}; running: true; onTriggered: {{
    console.log("FRESH " + {every}.map(function(w) {{ return w.details && w.details.window && w.details.window.monitor === 1 }}).join(","))
    Qt.quit() }} }}
}}
''')
            env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software',
                       XDG_RUNTIME_DIR=str(base / 'runtime'), QT_QPA_PLATFORMTHEME='')
            for key in ('HYPRLAND_INSTANCE_SIGNATURE', 'WAYLAND_DISPLAY', 'DISPLAY'):
                env.pop(key, None)
            result = subprocess.run(['quickshell', '-p', str(base), '--no-color'], env=env,
                                    timeout=60, capture_output=True, text=True)
            result.check_returncode()
            out = result.stdout + result.stderr
            start = [float(l.split('INJECT ')[1].split()[0]) for l in out.splitlines() if 'INJECT ' in l]
            fresh = [l.split('FRESH ')[1].strip().split(',') for l in out.splitlines() if 'FRESH ' in l]
            if not start or not fresh:
                raise SystemExit('Budget fixture did not run:\n' + out[-2000:])
            lines = log.read_text().splitlines() if log.exists() else []
            spawns = Counter(l.split(' ', 1)[1] for l in lines if float(l.split()[0]) >= start[0])
            return dict(spawns), [f == 'true' for f in fresh[0]]

    cases = []
    for bars in (1, 2):
        for above in (True, False):
            cases += [((bars, above, 'activewindowv2'), {'maintain': 1}, False),
                      ((bars, above, 'monitorremovedv2'), {'maintain': 1, 'status': 1}, True),
                      ((bars, above, 'movewindowv2'), {'maintain': 1, 'status': 1}, True),
                      ((bars, above, None, 17000), {'maintain': 1}, False)]
            # Menu opened after a recovery-triggering event, on the owner and on a peer.
            for opener in range(bars):
                cases.append(((bars, above, 'activewindowv2', 6500, 1000, opener), None, opener))
    failures = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda case: run(*case[0]), cases))
    for (case, expected, check), (spawns, fresh) in zip(cases, results):
        label = f'bars={case[0]} above={case[1]} ' + (case[2] or 'idle 3-17s') + (f' open=w{case[5]}' if len(case) > 4 else '')
        ok = True
        if expected is None:
            # Menu open: one immediate refresh plus 1 s polling; owner still maintains once.
            ok = spawns.get('maintain') == 1 and spawns.get('status', 0) >= 2 and fresh[check]
        else:
            ok = spawns == expected and (not check or all(fresh))
        print(('PASS ' if ok else 'FAIL ') + label, spawns, 'fresh=' + ','.join(map(str, fresh)))
        if not ok:
            failures.append(label)
    if failures:
        raise SystemExit(f'{len(failures)} maintenance budget case(s) failed')
    print(f'MAINTENANCE BUDGET PASS: {len(cases)} cases')


if args.maintenance_budget_check:
    maintenance_budget_check()
    raise SystemExit(0)
args.output.parent.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix='omapeek-preview-') as temp:
    base = Path(temp)
    # qs imports use the config root at runtime; qmllint uses an explicit qs folder.
    (base / 'qs').mkdir()
    for module in ('Ui', 'Commons'):
        (base / module).symlink_to(Path('/usr/share/omarchy/shell') / module)
        (base / 'qs' / module).symlink_to(Path('/usr/share/omarchy/shell') / module)
    for name in ('QuickControls.qml', 'OPeekIcon.qml', 'OmaPeekWidget.qml', 'OmaPeekPanel.qml', 'ControlsViewport.qml', 'OmaPeekButton.qml', 'OmaPeekToggle.qml', 'OmaPeekDropdown.qml'):
        (base / name).symlink_to(root / name)
    (base / 'KeyboardChecks.qml').symlink_to(root / 'tests/KeyboardChecks.qml')
    (base / 'AccessibilityChecks.js').symlink_to(root / 'tests/AccessibilityChecks.js')
    if args.lint:
        raise SystemExit(subprocess.run(['/usr/lib/qt6/bin/qmllint', '-I', str(base),
            *[str(base / n) for n in ('QuickControls.qml', 'ControlsViewport.qml', 'OmaPeekPanel.qml', 'OmaPeekWidget.qml', 'OmaPeekButton.qml', 'OmaPeekToggle.qml', 'OmaPeekDropdown.qml')]]).returncode)
    fixture = dict(active=True, hidden=False, follow=True, above=True,
        options=dict(width=600, corner='bottom-right', follow=True, above=True),
        window={'class': 'Chromium', 'title': 'Designing a calmer desktop - YouTube',
                'workspace': {'id': 2, 'name': '2'}, 'monitor': 1,
                'at': [args.monitor_width - 620, args.monitor_height - 358], 'size': [600, 338]},
        monitors=[dict(id=1, name='DP-1', description='Main display', width=args.monitor_width,
                       height=args.monitor_height, x=0, y=0, scale=1, transform=0)])
    if args.runtime_check:
        # Never point the runtime check at the real controller or live session state.
        helper = base / 'fixture-helper'
        helper.write_text('import json, sys\nstatus = ' + repr(fixture) +
                          '\nif sys.argv[1:] == ["status"]: print(json.dumps(status))\n')
        (base / 'shell.qml').write_text("""import QtQuick
import Quickshell
ShellRoot {
  OmaPeekWidget { visible: false; helper: HELPER }
  Timer { interval: 1800; running: true; onTriggered: Qt.quit() }
}
""".replace("HELPER", json.dumps(str(helper))))
        env = dict(os.environ, QT_QPA_PLATFORM='wayland')
        subprocess.run(['quickshell', '-p', str(base), '--no-color'], env=env, timeout=10, check=True)
        raise SystemExit(0)
    (base / 'shell.qml').write_text('''import QtQuick
import Quickshell
import qs.Commons
import qs.Ui
import "AccessibilityChecks.js" as Checks
ShellRoot {
  FloatingWindow {
    id: win
    visible: true
    implicitWidth: WIDTH; implicitHeight: HEIGHT
    color: "transparent"
    BorderSurface {
      id: capture
      anchors.fill: parent
      color: Color.popups.background
      borderSpec: Border.surfaceSpec("popups", "border", Color.popups.border, Math.max(1, Style.space(2)))
      radius: Style.cornerRadius
      padding: Style.spacing.popupPadding
      ControlsViewport {
        id: viewport
        anchors.fill: parent
        anchors.leftMargin: capture.contentLeftInset
        anchors.rightMargin: capture.contentRightInset
        anchors.topMargin: capture.contentTopInset
        anchors.bottomMargin: capture.contentBottomInset
        status: FIXTURE
      }
    }
    Loader { id: keyboardChecks; active: @KEYBOARD@; source: "KeyboardChecks.qml" }
    Timer {
      interval: 900; running: @FOCUS@
      onTriggered: viewport.restoreControl.forceActiveFocus()
    }
    Timer {
      interval: 1400; running: true
      onTriggered: {
        if (@KEYBOARD@) {
          try { keyboardChecks.item.run(viewport) }
          catch (error) { console.error("KEYBOARD FAILED: " + error) }
        }
        if (@ACCESSIBILITY@) {
          try { Checks.run(viewport) }
          catch (error) { console.error("ACCESSIBILITY FAILED: " + error) }
        }
        if (@FOCUS@) {
          var pos = viewport.restoreControl.mapToItem(viewport, 0, 0)
          if (pos.y < 0 || pos.y + viewport.restoreControl.height > viewport.height + 1)
            console.error("FOCUS SCROLL FAILED")
          else console.log("Restore focus scroll verified")
        }
        capture.grabToImage(function(result) {
          if (!result.saveToFile(OUTPUT)) console.error("Capture failed")
          Qt.quit()
        })
      }
    }
  }
}
'''.replace('WIDTH', str(args.width)).replace('HEIGHT', str(args.height))
      .replace('FIXTURE', json.dumps(fixture)).replace('OUTPUT', json.dumps(str(args.output.resolve())))
      .replace('@KEYBOARD@', 'true' if args.keyboard_check else 'false')
      .replace('@FOCUS@', 'true' if args.focus_restore else 'false')
      .replace('@ACCESSIBILITY@', 'true' if args.accessibility_check else 'false'))
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software')
    result = subprocess.run(['quickshell', '-p', str(base), '--no-color'], env=env,
                            timeout=15, capture_output=True, text=True)
    print(result.stdout, end='')
    print(result.stderr, end='')
    result.check_returncode()
    if 'KEYBOARD FAILED' in result.stderr + result.stdout or 'ACCESSIBILITY FAILED' in result.stderr + result.stdout or 'FOCUS SCROLL FAILED' in result.stderr + result.stdout or 'Capture failed' in result.stderr + result.stdout:
        raise SystemExit('Preview verification failed')
    if args.keyboard_check and 'KEYBOARD PASS:' not in result.stderr + result.stdout:
        raise SystemExit('Keyboard checks did not complete')
    if not args.output.is_file():
        raise SystemExit('No screenshot produced')
    print(args.output)
