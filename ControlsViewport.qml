import QtQuick
import QtQuick.Window

Flickable {
  id: root
  property alias status: controls.status
  property alias busy: controls.busy
  property alias error: controls.error
  property alias restoreControl: controls.restoreControl
  signal command(var arguments)
  clip: true
  contentWidth: width
  contentHeight: controls.implicitHeight
  boundsBehavior: Flickable.StopAtBounds
  function revealFocus() {
    var window = root.Window.window
    var item = window ? window.activeFocusItem : null
    var ancestor = item
    while (ancestor && ancestor !== controls) ancestor = ancestor.parent
    if (!ancestor) return
    var pos = item.mapToItem(controls, 0, 0)
    if (pos.y < contentY) contentY = pos.y
    else if (pos.y + item.height > contentY + height)
      contentY = Math.max(0, Math.min(contentHeight - height, pos.y + item.height - height))
  }
  Connections {
    target: root.Window.window
    function onActiveFocusItemChanged() { root.revealFocus() }
  }
  QuickControls {
    id: controls
    width: root.width
    onCommand: function(args) { root.command(args) }
  }
}
