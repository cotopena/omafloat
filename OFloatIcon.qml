import QtQuick
import QtQuick.Shapes
import qs.Commons

Item {
  id: root
  property real iconSize: Style.font.icon
  property color color: Color.foreground
  implicitWidth: iconSize
  implicitHeight: iconSize

  Item {
    width: 24
    height: 24
    scale: root.iconSize / 24
    transformOrigin: Item.TopLeft

    // Open O silhouette leaves a clear gap around the floating video pane.
    Shape {
      anchors.fill: parent
      antialiasing: true
      layer.enabled: true
      layer.samples: 4
      ShapePath {
        strokeColor: root.color
        strokeWidth: 2
        fillColor: "transparent"
        capStyle: ShapePath.FlatCap
        PathSvg { path: "M 18 11 L 18 8 Q 18 3 13 3 L 9 3 Q 4 3 4 8 L 4 16 Q 4 21 9 21 L 12 21" }
      }
    }

    Rectangle {
      x: 13
      y: 14
      width: 10
      height: 7
      radius: 1
      color: root.color
      antialiasing: true
    }
  }
}
