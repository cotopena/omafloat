import QtQuick
import qs.Commons
import qs.Ui

Panel {
  id: root
  manageIpc: false
  property var anchorItem: null
  property var hostWidget: null
  function open() { controller.show(); hostWidget.refreshStatus() }
  KeyboardPanel {
    id: popup
    anchorItem: root.anchorItem
    bar: root.bar
    owner: root.hostWidget
    open: root.opened
    focusTarget: scroll
    contentWidth: fittedContentWidth(Style.space(360))
    contentHeight: fittedContentHeight(scroll.contentHeight)
    ControlsViewport {
      id: scroll
      anchors.fill: parent
      Keys.onEscapePressed: root.close()
      status: root.hostWidget ? root.hostWidget.details : ({})
      busy: root.hostWidget ? root.hostWidget.busy : false
      error: root.hostWidget ? root.hostWidget.error : ""
      onCommand: function(args) { root.hostWidget.runCommand(args) }
    }
  }
}
