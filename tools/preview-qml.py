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
parser.add_argument('--lint', action='store_true')
args = parser.parse_args()
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
    Timer {
      interval: 900; running: @FOCUS@
      onTriggered: viewport.restoreControl.forceActiveFocus()
    }
    Timer {
      interval: 1400; running: true
      onTriggered: {
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
      .replace('@FOCUS@', 'true' if args.focus_restore else 'false')
      .replace('@ACCESSIBILITY@', 'true' if args.accessibility_check else 'false'))
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software')
    result = subprocess.run(['quickshell', '-p', str(base), '--no-color'], env=env,
                            timeout=15, capture_output=True, text=True)
    print(result.stdout, end='')
    print(result.stderr, end='')
    result.check_returncode()
    if 'ACCESSIBILITY FAILED' in result.stderr + result.stdout or 'FOCUS SCROLL FAILED' in result.stderr + result.stdout or 'Capture failed' in result.stderr + result.stdout:
        raise SystemExit('Preview verification failed')
    if not args.output.is_file():
        raise SystemExit('No screenshot produced')
    print(args.output)
