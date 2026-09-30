import QtQuick
import Quickshell
import Quickshell.Io
import qs.Ui
import qs.Commons

BarWidget {
  id: root
  moduleName: "io.github.cotopena.omafloat"
  implicitWidth: root.vertical ? root.barSize : icon.implicitWidth + Style.space(18)
  implicitHeight: root.barSize
  property bool floatingVideo: false
  readonly property bool tooltipHovered: visible && opacity > 0 && mouseArea.containsMouse
  readonly property string helper: decodeURIComponent(Qt.resolvedUrl("bin/omafloat").toString().replace(/^file:\/\//, ""))

  function activate() {
    if (!toggleProcess.running) toggleProcess.running = true
  }

  function refreshStatus() {
    if (!statusProcess.running && !toggleProcess.running) statusProcess.running = true
  }

  Process {
    id: toggleProcess
    command: ["python3", root.helper]
    onExited: root.refreshStatus()
  }

  Process {
    id: statusProcess
    command: ["python3", root.helper, "status"]
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        try { root.floatingVideo = JSON.parse(this.text).active === true }
        catch (error) { /* Keep the last state while a toggle holds the lock. */ }
      }
    }
  }

  Timer {
    interval: 2000
    running: true
    repeat: true
    triggeredOnStart: true
    onTriggered: root.refreshStatus()
  }

  IpcHandler {
    target: "io.github.cotopena.omafloat"
    function toggle(): void { root.activate() }
    function status(): string {
      return JSON.stringify({version: "0.3.0", active: root.floatingVideo, label: root.floatingVideo ? "Return video" : "Float video", iconOnly: true, busy: toggleProcess.running})
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
    onClicked: root.activate()
    onEntered: if (root.bar) root.bar.showTooltip(root, "OmaFloat")
    onExited: if (root.bar) root.bar.hideTooltip(root)
  }
}
