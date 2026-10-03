import QtQuick
import Quickshell
import Quickshell.Hyprland
import Quickshell.Io
import qs.Ui
import qs.Commons

BarWidget {
  id: root
  moduleName: "io.github.cotopena.omafloat"
  implicitWidth: root.vertical ? root.barSize : icon.implicitWidth + Style.space(18)
  implicitHeight: root.barSize
  property bool floatingVideo: details.active === true
  property var details: ({})
  property string error: ""
  readonly property bool busy: toggleProcess.running
  readonly property bool opened: menu.opened
  readonly property bool popoutSwitchClosing: menu.popoutSwitchClosing
  function open() { menu.open() }
  function close() { menu.close() }
  function closeForPopoutSwitch() { menu.closeForPopoutSwitch() }
  function runCommand(args) {
    if (busy) return
    error = ""
    toggleProcess.command = ["python3", helper].concat(args)
    toggleProcess.running = true
  }
  OmaFloatPanel { id: menu; bar: root.bar; anchorItem: root; hostWidget: root }
  property bool refreshPending: false
  readonly property bool tooltipHovered: visible && opacity > 0 && mouseArea.containsMouse
  property string helper: decodeURIComponent(Qt.resolvedUrl("bin/omafloat").toString().replace(/^file:\/\//, ""))

  function activate() {
    root.runCommand(["toggle"])
  }

  function refreshStatus() {
    if (toggleProcess.running) return
    // A running check may predate the change, so check again once it lands.
    if (statusProcess.running) {
      root.refreshPending = true
      return
    }
    root.refreshPending = false
    statusProcess.running = true
  }

  Process {
    id: toggleProcess
    command: ["python3", root.helper]
    onExited: { root.refreshStatus(); root.broadcast("refreshStatus") }
    stderr: StdioCollector { onStreamFinished: if (this.text.trim()) root.error = this.text.trim() }
  }

  Process {
    id: statusProcess
    command: ["python3", root.helper, "status"]
    onExited: if (root.refreshPending) root.refreshStatus()
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        try { root.details = JSON.parse(this.text) }
        catch (error) { /* Keep the last state if the helper printed nothing. */ }
      }
    }
  }

  Connections {
    target: Hyprland
    function onRawEvent(event) {
      if (!event || !event.name) return
      if (["openwindow", "closewindow", "movewindowv2", "changefloatingmode", "pin", "fullscreen"]
          .indexOf(String(event.name)) !== -1) eventTimer.restart()
    }
  }

  Timer {
    id: eventTimer
    interval: 300
    onTriggered: root.refreshStatus()
  }

  // Events cover window changes; this catches anything they miss.
  Timer {
    interval: menu.opened ? 1000 : 5000
    running: true
    repeat: true
    triggeredOnStart: true
    onTriggered: root.refreshStatus()
  }

  Process { id: maintainProcess; command: ["python3", root.helper, "maintain"] }
  Timer {
    interval: 1000; repeat: true; running: root.floatingVideo && root.details.above !== false && !root.details.hidden
    onTriggered: if (!root.busy && !maintainProcess.running) maintainProcess.running = true
  }

  IpcHandler {
    target: "io.github.cotopena.omafloat"
    function toggle(): void { root.activate() }
    function status(): string {
      return JSON.stringify({version: "0.3.1", active: root.floatingVideo, label: root.floatingVideo ? "Return video" : "Float video", iconOnly: true, busy: toggleProcess.running})
    }
  }

  OFloatIcon {
    id: icon
    anchors.centerIn: parent
    color: root.bar ? root.bar.barForeground : Color.foreground
  }

  MouseArea {
    id: mouseArea
    anchors.fill: parent
    hoverEnabled: true
    cursorShape: Qt.PointingHandCursor
    onClicked: menu.toggle()
    onEntered: if (root.bar) root.bar.showTooltip(root, "OmaFloat")
    onExited: if (root.bar) root.bar.hideTooltip(root)
  }
}
