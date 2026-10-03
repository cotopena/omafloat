// Runtime assertions against the actual QML controls and focused dropdown trigger.
function check(condition, message) {
  if (!condition) throw new Error(message)
}
function find(item, name) {
  if (item.objectName === name) return item
  for (var i = 0; i < item.children.length; i++) {
    var found = find(item.children[i], name)
    if (found) return found
  }
  return null
}
function run(viewport) {
  var commands = []
  viewport.command.connect(function(args) { commands.push(args) })
  var original = viewport.status
  var hide = find(viewport, "visibilityAction")
  var medium = find(viewport, "sizeMedium")
  var display = find(viewport, "displayPicker")
  var placement = find(viewport, "placementPicker")
  var follow = find(viewport, "followToggle")
  var above = find(viewport, "aboveToggle")
  var restore = viewport.restoreControl
  check(hide.Accessible.role === 0x2b && hide.Accessible.name === "Hide float", "Hide button role/name")
  check(medium.Accessible.role === 0x2d && medium.Accessible.checked, "Medium radio checked state")
  check(follow.Accessible.role === 0x87 && follow.Accessible.name === "Follow workspaces" && follow.Accessible.checked, "Follow switch")
  check(above.Accessible.role === 0x87 && above.Accessible.checked, "Above switch")
  check(restore.Accessible.role === 0x2b && restore.Accessible.name === "Restore original window", "Restore button")
  display.accessibleTrigger.forceActiveFocus()
  check(display.accessibleTrigger.activeFocus, "Dropdown trigger owns focus")
  check(display.accessibleTrigger.Accessible.role === 0x2e && display.accessibleTrigger.Accessible.name === "Display", "Focused display trigger role/name")
  check(display.accessibleTrigger.Accessible.description.indexOf("DP-1") !== -1, "Display selected value")
  check(placement.accessibleTrigger.Accessible.name === "Placement" && placement.accessibleTrigger.Accessible.description === "bottom right", "Placement value/name")
  hide.Accessible.pressAction()
  check(commands.pop()[0] === "hide", "Hide accessible activation")
  medium.Accessible.pressAction()
  check(commands.pop().join(" ") === "configure --width 600", "Preset accessible activation")
  follow.Accessible.toggleAction()
  check(commands.pop().join(" ") === "configure --follow false", "Switch accessible activation")
  restore.Accessible.pressAction()
  check(commands.pop()[0] === "restore", "Restore accessible activation")
  display.accessibleTrigger.Accessible.pressAction()
  check(display.popupOpen && display.accessibleTrigger.Accessible.pressed, "Accessible dropdown opens")
  var option = display.optionView.itemAtIndex(0)
  check(option && option.Accessible.role === 0x22 && option.Accessible.name.indexOf("DP-1") !== -1 && option.Accessible.selected, "Actual dropdown option role/name/selected")
  option.Accessible.pressAction()
  check(commands.pop().join(" ") === "configure --monitor DP-1", "Accessible option selects")
  check(!display.popupOpen, "Option closes dropdown")
  // Selection must preserve the caller binding: only status readback changes value.
  viewport.status = Object.assign({}, original, {
    window: Object.assign({}, original.window, {monitor: 2}),
    monitors: original.monitors.concat([{id: 2, name: "HDMI-A-1", width: 1920, height: 1080, scale: 1, transform: 0, x: 1920, y: 0}])
  })
  check(display.value === "HDMI-A-1" && display.accessibleTrigger.Accessible.description === "HDMI-A-1", "External display readback survives selection")
  placement.open()
  placement.optionView.currentIndex = 3
  var firstCorner = placement.optionView.itemAtIndex(0)
  var touchArea = firstCorner.children.find(function(item) { return "acceptedButtons" in item })
  check(!!touchArea, "Actual option pointer handler exists")
  touchArea.clicked(null) // direct touch/click, with no preceding hover event
  check(commands.pop().join(" ") === "configure --corner top-left", "Corner selection intent")
  check(placement.value === "bottom-right", "Selection does not optimistically replace controller value")
  viewport.status = Object.assign({}, original, {options: Object.assign({}, original.options, {corner: "top-right"})})
  check(placement.value === "top-right" && placement.accessibleTrigger.Accessible.description === "top right", "External corner readback survives selection")
  viewport.status = original
  viewport.status = Object.assign({}, original, {hidden: true, follow: false, above: false, options: {follow: false}})
  check(hide.Accessible.name === "Show float" && !follow.Accessible.checked && !above.Accessible.checked, "Accessible state follows controller status")
  viewport.status = original
  viewport.busy = true
  var count = commands.length
  var buttons = [hide, medium, follow, above, restore]
  for (var i = 0; i < buttons.length; i++) {
    check(!buttons[i].enabled, "Busy disables actual item")
    buttons[i].Accessible.pressAction()
    buttons[i].Accessible.toggleAction()
    buttons[i].clicked() // direct signals must not bypass disabled command guards
  }
  display.accessibleTrigger.Accessible.pressAction()
  placement.accessibleTrigger.Accessible.pressAction()
  display.open()
  display.optionView.currentIndex = 0
  display.optionView.selectCurrent()
  check(!display.popupOpen && !placement.popupOpen, "Disabled dropdown stays closed")
  check(commands.length === count, "Disabled activation emits no commands")
  viewport.busy = false
  console.log("Accessibility roles, names, states, actions and disabled guards verified")
}
