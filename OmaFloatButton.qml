import QtQuick
import qs.Ui

Button {
  id: root
  property string accessibleName: text
  property bool choice: false
  readonly property var pointerArea: children.find(function(item) { return "pressed" in item && "acceptedButtons" in item }) || null
  Accessible.role: choice ? Accessible.RadioButton : Accessible.Button
  Accessible.name: accessibleName
  Accessible.focusable: focusable
  Accessible.checkable: choice
  Accessible.checked: choice && selected
  Accessible.selected: selected
  Accessible.pressed: pointerArea ? pointerArea.pressed : false
  Accessible.onPressAction: if (root.enabled) root.clicked()
  Accessible.onToggleAction: if (root.enabled && root.choice) root.clicked()
}
