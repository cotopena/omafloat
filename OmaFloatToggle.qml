import QtQuick
import qs.Ui

Toggle {
  id: root
  Accessible.role: Accessible.Switch
  Accessible.name: label
  Accessible.description: description
  Accessible.checkable: true
  Accessible.checked: checked
  Accessible.onPressAction: if (root.enabled) root.clicked()
  Accessible.onToggleAction: if (root.enabled) root.clicked()
}
