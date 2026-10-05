pragma ComponentBehavior: Bound
import QtQuick
import qs.Commons
import qs.Ui

// Shared by the native popup and the isolated fixture capture.
Column {
  id: root
  property var status: ({})
  property bool busy: false
  property string error: ""
  property alias restoreControl: restoreButton
  signal command(var arguments)
  spacing: Style.space(8)
  readonly property var video: status.window || null
  readonly property var options: status.options || ({})
  readonly property var monitors: status.monitors || []
  readonly property var monitor: monitors.find(function(m) { return root.video && m.id === root.video.monitor }) || null
  readonly property var corners: ["top-left", "top-right", "bottom-left", "bottom-right"]
  function configure(args) { if (!busy && status.active === true) command(["configure"].concat(args)) }

  component Label: Text {
    textFormat: Text.PlainText
    color: Color.foreground
    font.family: Style.font.family
    font.pixelSize: Style.font.body
    elide: Text.ElideRight
  }
  component Action: OmaPeekButton {
    width: root.width
    focusable: true
    bordered: true
    enabled: !root.busy
    opacity: enabled ? 1 : 0.5
  }
  Row {
    width: parent.width
    spacing: Style.space(10)
    OPeekIcon { color: Color.accent; anchors.verticalCenter: parent.verticalCenter }
    Column {
      width: parent.width - 42
      Label { text: "OmaPeek"; font.bold: true; font.pixelSize: Style.font.title }
      Label { text: "QUICK CONTROLS · " + (root.busy ? "Working…" : root.status.active ? (root.status.hidden ? "Hidden" : "Floating") : "Ready"); font.pixelSize: Style.font.caption }
    }
  }
  Label { width: parent.width; text: "Active window"; opacity: 0.65; font.pixelSize: Style.font.caption }
  Label { width: parent.width; text: root.video ? root.video.class : "Open a YouTube video"; font.bold: true }
  Label { width: parent.width; text: root.video ? root.video.title : "A Chromium YouTube window is required" }
  Label { width: parent.width; text: root.video ? "Workspace " + root.video.workspace.name : ""; opacity: 0.65; font.pixelSize: Style.font.caption }
  Action {
    objectName: "visibilityAction"
    text: root.status.active ? (root.status.hidden ? "Show float" : "Hide float") : "Float video"
    enabled: !root.busy && !!root.video
    onClicked: if (enabled) root.command([root.status.active ? (root.status.hidden ? "show" : "hide") : "float"])
  }
  Label { text: "SIZE"; font.pixelSize: Style.font.caption }
  Row {
    width: parent.width
    spacing: Style.space(4)
    Repeater {
      model: ["Small", "Medium", "Large"]
      OmaPeekButton {
        required property string modelData
        required property int index
        width: (root.width - Style.space(4) * 2) / 3
        objectName: "size" + modelData
        text: modelData
        choice: true
        focusable: true; bordered: true
        enabled: root.status.active === true && !root.busy
        selected: (root.options.width || 600) === [400, 600, 800][index]
        onClicked: if (enabled) root.configure(["--width", String([400, 600, 800][index])])
      }
    }
  }
  OmaPeekDropdown {
    width: parent.width
    objectName: "displayPicker"
    label: "Display"
    value: root.monitor ? root.monitor.name : ""
    options: root.monitors.map(function(m) { return {value: m.name, label: m.name + (m.description ? " · " + m.description : "")} })
    enabled: root.status.active === true && !root.busy
    onChanged: function(value) {
      root.configure(["--monitor", value])
    }
  }
  Rectangle {
    id: diagram
    width: parent.width
    height: 170
    readonly property real displayWidth: root.monitor ? (root.monitor.transform % 2 ? root.monitor.height : root.monitor.width) / root.monitor.scale : 1920
    readonly property real displayHeight: root.monitor ? (root.monitor.transform % 2 ? root.monitor.width : root.monitor.height) / root.monitor.scale : 1080
    color: Style.selectedFillFor(Color.foreground, Color.accent)
    radius: Style.cornerRadius
    border.color: Color.accent
    Item {
      id: desktop
      width: Math.min(diagram.width, diagram.height * diagram.displayWidth / diagram.displayHeight)
      height: width * diagram.displayHeight / diagram.displayWidth
      anchors.centerIn: parent
      Rectangle {
        anchors.fill: parent
        anchors.margins: 6
        color: Color.popups.background
        opacity: 0.55
        border.color: Color.foreground
        radius: Style.cornerRadius
        Rectangle { x: 9; y: 12; width: parent.width * 0.18; height: parent.height - 22; color: Color.foreground; opacity: 0.08 }
        Column {
          x: parent.width * 0.25; y: 16; spacing: 7
          Repeater { model: 5; Rectangle { required property int index; width: desktop.width * (0.3 + (index % 3) * 0.08); height: 2; color: Color.foreground; opacity: 0.16 } }
        }
      }

    Rectangle {
      visible: root.status.active === true && !!root.video && !!root.monitor
      x: root.video && root.monitor ? Math.max(0, Math.min(parent.width - width, (root.video.at[0] - root.monitor.x) / diagram.displayWidth * desktop.width)) : 0
      y: root.video && root.monitor ? Math.max(0, Math.min(parent.height - height, (root.video.at[1] - root.monitor.y) / diagram.displayHeight * desktop.height)) : 0
      width: root.video ? Math.min(parent.width, root.video.size[0] / diagram.displayWidth * desktop.width) : 0
      height: root.video ? Math.min(parent.height, root.video.size[1] / diagram.displayHeight * desktop.height) : 0
      radius: Style.cornerRadius
      color: Color.popups.background
      border.color: Color.accent; border.width: 2
      opacity: root.status.hidden ? 0.35 : 1
      Label { anchors.centerIn: parent; text: "▶"; color: Color.accent }
    }
    Repeater {
      model: root.corners
      OmaPeekButton {
        required property string modelData
        width: 32; height: 28
        x: modelData.endsWith("left") ? 0 : desktop.width - width
        y: modelData.startsWith("top") ? 0 : desktop.height - height
        text: modelData.startsWith("top") ? (modelData.endsWith("left") ? "⌜" : "⌝") : (modelData.endsWith("left") ? "⌞" : "⌟")
        accessibleName: "Place " + modelData.replace("-", " ")
        selected: (root.options.corner || "bottom-right") === modelData
        tooltipText: modelData.replace("-", " ")
        focusable: true
        enabled: root.status.active === true && !root.busy
        onClicked: if (enabled) root.configure(["--corner", modelData])
      }
    }
    }
  }
  Label { text: "Desktop schematic · select a corner"; font.pixelSize: Style.font.caption; opacity: 0.65 }
  OmaPeekDropdown {
    width: parent.width
    objectName: "placementPicker"
    label: "Placement"; showLabel: false
    value: root.options.corner || "bottom-right"
    options: root.corners.map(function(c) { return {value: c, label: c.replace("-", " ")} })
    enabled: root.status.active === true && !root.busy
    onChanged: function(value) {
      root.configure(["--corner", value])
    }
  }
  OmaPeekToggle {
    width: parent.width; implicitHeight: 42
    objectName: "followToggle"
    label: "Follow workspaces"; titleSize: Style.font.body
    checked: root.status.hidden ? !!root.options.follow : !!root.status.follow
    enabled: root.status.active === true && !root.busy
    onClicked: if (enabled) root.configure(["--follow", checked ? "false" : "true"])
  }
  OmaPeekToggle {
    width: parent.width; implicitHeight: 42
    objectName: "aboveToggle"
    label: "Keep above other windows"; titleSize: Style.font.body
    checked: root.status.above !== false
    enabled: root.status.active === true && !root.busy
    onClicked: if (enabled) root.configure(["--above", checked ? "false" : "true"])
  }
  Action { id: restoreButton; text: "Restore original window"; enabled: root.status.active === true && !root.busy; onClicked: if (enabled) root.command(["restore"]) }
  Label {
    width: parent.width
    text: root.error || root.status.error || (root.video && root.status.active ? root.video.size.join(" × ") + " · " + (root.options.corner || "bottom-right").replace("-", " ") : "Keyboard shortcut floats / restores")
    wrapMode: Text.WordWrap; elide: Text.ElideNone; font.pixelSize: Style.font.caption
  }
}
