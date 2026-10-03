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

  // Register with the bar like WidgetButton so an open popup's dismiss layer
  // forwards bar clicks here; only the left button toggles Quick Controls.
  property var registeredBar: null
  function triggerPress(button) {
    if (root.bar) root.bar.hideTooltip(root)
    if (button === Qt.LeftButton) menu.toggle()
  }
  function syncClickRegistration() {
    if (registeredBar && registeredBar.unregisterClickTarget) registeredBar.unregisterClickTarget(root)
    registeredBar = root.bar
    if (registeredBar && registeredBar.registerClickTarget) registeredBar.registerClickTarget(root)
  }
  onBarChanged: syncClickRegistration()
  Component.onCompleted: syncClickRegistration()
  Component.onDestruction: if (registeredBar && registeredBar.unregisterClickTarget) registeredBar.unregisterClickTarget(root)

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

  // One bar instance exists per monitor; only the first one does background
  // work. Elected per call because moduleWidgets() is not reactive.
  function owner() {
    var items = root.bar && typeof root.bar.moduleWidgets === "function" ? root.bar.moduleWidgets(root.moduleName) : []
    return items && items.length > 0 && items[0] ? items[0] : root
  }
  function backgroundRefresh() { if (menu.opened || root.owner() === root) root.refreshStatus() }

  readonly property bool maintaining: floatingVideo && details.above !== false && !details.hidden
  property bool maintainPending: false
  // Floats started outside the widget arrive through the status refresh.
  onMaintainingChanged: if (maintaining) maintainTimer.restart()
  function maintain() {
    if (!root.maintaining || root.busy || root.owner() !== root) return
    if (maintainProcess.running) { root.maintainPending = true; return }
    root.maintainPending = false
    maintainProcess.running = true
  }

  Connections {
    target: Hyprland
    function onRawEvent(event) {
      if (!event || !event.name) return
      var name = String(event.name)
      if (["openwindow", "closewindow", "movewindowv2", "changefloatingmode", "pin", "fullscreen"]
          .indexOf(name) !== -1) eventTimer.restart()
      // Hyprland raises floating windows on focus or open, which can cover the video.
      if (root.maintaining && ["activewindowv2", "openwindow", "changefloatingmode", "movewindowv2",
          "workspacev2", "focusedmonv2", "fullscreen", "pin"].indexOf(name) !== -1) maintainTimer.restart()
    }
  }

  Timer {
    id: eventTimer
    interval: 300
    onTriggered: root.backgroundRefresh()
  }

  // Events cover window changes; this catches anything they miss.
  Timer {
    interval: menu.opened ? 1000 : 30000
    running: true
    repeat: true
    triggeredOnStart: true
    onTriggered: root.backgroundRefresh()
  }

  Process {
    id: maintainProcess
    command: ["python3", root.helper, "maintain"]
    onExited: if (root.maintainPending) root.maintain()
  }
  Timer { id: maintainTimer; interval: 200; onTriggered: root.maintain() }
  // Safety net for stacking changes no event reports.
  Timer { interval: 12000; repeat: true; running: root.maintaining; onTriggered: root.maintain() }

  IpcHandler {
    target: "io.github.cotopena.omafloat"
    function toggle(): void { root.activate() }
    // Any instance may receive this; the owner keeps the freshest state.
    function status(): string {
      var state = root.owner()
      var active = state.floatingVideo === true
      return JSON.stringify({version: "0.3.1", active: active, label: active ? "Return video" : "Float video", iconOnly: true, busy: state.busy === true || root.busy})
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
    onClicked: function(mouse) { root.triggerPress(mouse.button) }
    onEntered: if (root.bar) root.bar.showTooltip(root, "OmaFloat")
    onExited: if (root.bar) root.bar.hideTooltip(root)
  }
}
