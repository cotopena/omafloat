import QtQuick
import Quickshell
import Quickshell.Io
import qs.Ui
import qs.Commons

BarWidget {
  id: root
  moduleName: "io.github.cotopena.omafloat"
  implicitWidth: root.vertical ? root.barSize : label.implicitWidth + Style.space(18)
  implicitHeight: root.barSize
  property bool floatingVideo: false
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
      return JSON.stringify({version: "0.3.0", active: root.floatingVideo, label: label.text, busy: toggleProcess.running})
    }
  }

  Text {
    id: label
    anchors.centerIn: parent
    text: root.vertical ? "▣" : "▣  " + (root.floatingVideo ? "Return video" : "Float video")
    color: root.bar ? root.bar.barForeground : "white"
    font.family: root.bar ? root.bar.fontFamily : "sans-serif"
    font.pixelSize: Style.font.body
    textFormat: Text.PlainText
  }

  MouseArea {
    anchors.fill: parent
    hoverEnabled: true
    cursorShape: Qt.PointingHandCursor
    onClicked: root.activate()
    onEntered: if (root.bar) root.bar.showTooltip(root, "OmaFloat · " + (root.floatingVideo ? "Return YouTube to its workspace" : "Keep YouTube above your apps"))
    onExited: if (root.bar) root.bar.hideTooltip(root)
  }
}
