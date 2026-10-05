import QtQuick
import QtQuick.Window
import QtTest
import "AccessibilityChecks.js" as Checks

// QtTest sends events only to this process's offscreen QQuickWindow.
// No compositor input, controller helper, or real window is involved.
TestCase {
  name: "OmaPeekKeyboard"
  when: false
  function check(ok, message) { if (!ok) throw new Error(message) }
  function run(viewport) {
    var commands = []
    viewport.command.connect(function(args) { commands.push(args.join(" ")) })
    var original = viewport.status
    var display = Checks.find(viewport, "displayPicker")
    var placement = Checks.find(viewport, "placementPicker")
    var first = Checks.find(viewport, "visibilityAction")
    var expected = ["Hide float", "Small", "Medium", "Large", "Display",
      "Place top left", "Place top right", "Place bottom left", "Place bottom right",
      "Placement", "Follow workspaces", "Keep above other windows", "Restore original window"]
    var routes = ["hide", "configure --width 400", "configure --width 600", "configure --width 800", null,
      "configure --corner top-left", "configure --corner top-right", "configure --corner bottom-left", "configure --corner bottom-right", null,
      "configure --follow false", "configure --above false", "restore"]
    function focused() { return viewport.Window.window.activeFocusItem }
    function name() { return focused() ? focused().Accessible.name : "<none>" }
    viewport.forceActiveFocus()
    keyClick(Qt.Key_Tab)
    check(first.activeFocus, "Panel focus target Tabs to first control")
    for (var i = 0; i < expected.length; i++) {
      check(name() === expected[i], "Tab " + i + ": expected " + expected[i] + ", got " + name())
      var pos = focused().mapToItem(viewport, 0, 0)
      check(pos.y >= -1 && pos.y + focused().height <= viewport.height + 1, "Focused control visible: " + expected[i])
      if (routes[i]) {
        for (var key of [Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space]) {
          keyClick(key)
          check(commands.pop() === routes[i], "Keyboard route " + expected[i] + " key " + key)
          check(commands.length === 0, "Single command per key")
        }
      } else {
        var picker = i === 4 ? display : placement
        keyClick(Qt.Key_Return); wait(30)
        check(picker.popupOpen && picker.optionView.activeFocus, "Dropdown takes focus")
        keyClick(Qt.Key_Up)
        keyClick(Qt.Key_Return); wait(30)
        check(!picker.popupOpen && picker.accessibleTrigger.activeFocus, "Selection returns trigger focus")
        check(commands.pop() === (i === 4 ? "configure --monitor DP-1" : "configure --corner bottom-left"), "Dropdown keyboard command")
        // Actual monitor readback changes without replacing the focused trigger.
        if (i === 4) {
          viewport.status = Object.assign({}, original, {window: Object.assign({}, original.window, {monitor: 2}),
            monitors: original.monitors.concat([{id:2,name:"HDMI-A-1",width:1080,height:1920,scale:1,transform:0,x:1920,y:0}])})
          check(picker.value === "HDMI-A-1" && picker.accessibleTrigger.activeFocus, "Focus after monitor readback")
          keyClick(Qt.Key_Space); wait(30)
          check(picker.optionView.activeFocus, "Reopened display takes focus")
          keyClick(Qt.Key_Up); keyClick(Qt.Key_Return); wait(30)
          check(commands.pop() === "configure --monitor DP-1", "Display Up/Return selection")
          keyClick(Qt.Key_Return); wait(30)
          keyClick(Qt.Key_Down); keyClick(Qt.Key_Return); wait(30)
          check(commands.pop() === "configure --monitor HDMI-A-1", "Display Down/Return selection")
          check(picker.accessibleTrigger.activeFocus, "Focus after second monitor selection")
          viewport.status = original
        }
        keyClick(Qt.Key_Down); wait(30)
        check(picker.popupOpen && picker.optionView.activeFocus, "Down opens dropdown")
        keyClick(Qt.Key_Escape); wait(30)
        check(!picker.popupOpen && picker.accessibleTrigger.activeFocus, "Escape returns trigger focus")
      }
      keyClick(Qt.Key_Tab)
    }
    check(name() === expected[0], "Forward traversal wraps")
    for (var j = expected.length - 1; j >= 0; j--) {
      keyClick(Qt.Key_Tab, Qt.ShiftModifier)
      check(name() === expected[j], "Reverse traversal " + j + ": " + name())
    }
    console.log("KEYBOARD PASS: 13 controls, forward/reverse traversal, Return/Enter/Space commands, dropdown selection/Escape/reopen, monitor readback focus")
  }
}
