import contextlib
import copy
import fcntl
from importlib.machinery import SourceFileLoader
import importlib.util
import io
import json
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import call, patch

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_loader("omafloat", SourceFileLoader("omafloat", str(ROOT / "bin/omafloat")))
fv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fv)
CLIENT = dict(address="0x123", pid=42, stableId="42", workspace=dict(id=7, name="7"),
              monitor=1, floating=False, pinned=False, fullscreen=0, fullscreenClient=0,
              at=[12, 38], size=[1800, 1000], grouped=[],
              **{"class": "chrome-youtube.com__-Profile_3", "title": "Example - YouTube"})
MONITOR = dict(id=1, name="DP-1", width=1920, height=1080, x=0, y=0, scale=1,
               reserved=[0, 30, 0, 0], activeWorkspace=dict(id=1, name="1"), focused=True)
FLOATED = dict(CLIENT, floating=True, pinned=True, fullscreenClient=2, workspace=dict(id=1, name="1"))


def fake_hypr(active=CLIENT, monitor=MONITOR):
    def hypr(*args):
        if args == ("-j", "monitors"):
            return json.dumps([monitor])
        if args == ("-j", "activewindow"):
            return json.dumps(active)
        return "true"
    return hypr


def fake_dispatch(live, active=MONITOR["activeWorkspace"]):
    """Model the compositor-side effects the controller verifies."""
    def dispatch(method, **kwargs):
        if method == "window.float":
            live["floating"] = kwargs["action"] == "enable"
            live["fullscreenClient"] = 0
        elif method == "window.fullscreen_state":
            live["fullscreen"], live["fullscreenClient"] = kwargs["internal"], kwargs["client"]
        elif method == "window.pin":
            # Hyprland 0.56.2 pinWindow reassigns the window to the monitor's active workspace.
            live["pinned"] = kwargs["action"] == "enable"
            live["workspace"] = dict(active)
        elif method == "window.move" and "workspace" in kwargs:
            ref = str(kwargs["workspace"])
            live["workspace"] = (dict(id=-1337, name=ref[5:]) if ref.startswith("name:")
                                 else dict(id=int(ref), name=ref))
    return dispatch


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = patch.dict(fv.os.environ, XDG_RUNTIME_DIR=self.temp.name)
        self.env.start()
        self.addCleanup(self.env.stop)
        # Tests must never reach hyprctl, notify-send, or any other real command.
        guard = patch.object(fv.subprocess, "run", side_effect=AssertionError("unmocked subprocess"))
        guard.start()
        self.addCleanup(guard.stop)
        self.controller = fv.Controller()

    def state(self, client=None):
        return dict(version=2, original=client or copy.deepcopy(CLIENT), monitor_name="DP-1",
                    entered_fullscreen=True, sync_fullscreen=True)

    def test_reused_address_does_not_restore_another_window(self):
        self.controller.save(self.state())
        other = dict(CLIENT, stableId="different")
        with patch.object(fv, "read_clients", return_value=[other]), patch.object(fv, "dispatch") as dsp:
            self.controller.restore(self.state())
        dsp.assert_not_called()
        self.assertFalse(self.controller.path.exists())

    def test_restore_layout_and_fullscreen_sync(self):
        original = dict(CLIENT, floating=True, pinned=True, at=[100, 150], size=[800, 450])
        state = self.state(original)
        state["sync_fullscreen"] = False
        self.controller.save(state)
        live = copy.deepcopy(FLOATED)
        with patch.object(fv, "read_clients", side_effect=lambda: [copy.deepcopy(live)]), \
                patch.object(fv, "hypr", return_value=json.dumps([MONITOR])), \
                patch.object(fv, "send_key") as key, \
                patch.object(fv, "dispatch", side_effect=fake_dispatch(live)) as dsp:
            self.controller.restore(state)
        key.assert_called_once_with(FLOATED, "Escape")
        dsp.assert_any_call("window.pin", window="address:0x123", action="disable")
        dsp.assert_any_call("window.move", window="address:0x123", workspace=7, follow=False)
        dsp.assert_any_call("window.resize", window="address:0x123", x=800, y=450, relative=False)
        dsp.assert_any_call("window.move", window="address:0x123", x=100, y=150, relative=False)
        dsp.assert_any_call("window.set_prop", window="address:0x123", prop="sync_fullscreen", value="0")
        self.assertEqual(dsp.call_args.kwargs["action"], "enable")
        self.assertFalse(self.controller.path.exists())

    def test_failed_enter_rolls_back(self):
        def hypr(*args):
            if args == ("-j", "monitors"):
                return json.dumps([MONITOR])
            if args == ("-j", "activewindow"):
                return json.dumps(CLIENT)
            return "true"

        failed = False
        def dispatch(method, **kwargs):
            nonlocal failed
            if method == "window.resize" and not failed:
                failed = True
                raise RuntimeError("resize failed")

        with patch.object(fv, "hypr", side_effect=hypr), \
                patch.object(fv, "read_clients", return_value=[CLIENT]), \
                patch.object(fv, "send_key"), patch.object(fv.time, "sleep"), \
                patch.object(fv, "dispatch", side_effect=dispatch) as dsp:
            with self.assertRaisesRegex(RuntimeError, "resize failed"):
                self.controller.enter(CLIENT, 600)
        dsp.assert_any_call("window.float", window="address:0x123", action="disable")
        dsp.assert_any_call("window.move", window="address:0x123", workspace=7, follow=False)
        self.assertFalse(self.controller.path.exists())

    def test_repeat_float_without_new_client_fullscreen_event(self):
        current = copy.deepcopy(CLIENT)
        def hypr(*args):
            if args == ("-j", "monitors"):
                return json.dumps([MONITOR])
            if args == ("-j", "activewindow"):
                return json.dumps(CLIENT)
            return "true"
        def dispatch(method, **kwargs):
            if method == "window.float":
                current["floating"] = kwargs["action"] == "enable"
                current["fullscreenClient"] = 0
            elif method == "window.fullscreen_state":
                current["fullscreenClient"] = kwargs["client"]
            elif method == "window.pin":
                current["pinned"] = kwargs["action"] == "enable"

        with patch.object(fv, "hypr", side_effect=hypr), \
                patch.object(fv, "read_clients", side_effect=lambda: [current.copy()]), \
                patch.object(fv, "send_key"), patch.object(fv.time, "sleep"), \
                patch.object(fv, "dispatch", side_effect=dispatch):
            self.controller.enter(CLIENT, 600)
        self.assertTrue(current["floating"])
        self.assertTrue(current["pinned"])
        self.assertEqual(current["fullscreenClient"], 2)
        self.assertIsNotNone(self.controller.load())

    def test_failed_restore_keeps_state_for_retry(self):
        state = self.state()
        self.controller.save(state)
        with patch.object(fv, "read_clients", return_value=[FLOATED]), patch.object(fv, "send_key"), \
                patch.object(fv, "dispatch", side_effect=RuntimeError("disconnected")):
            with self.assertRaises(RuntimeError):
                self.controller.restore(state)
        self.assertEqual(self.controller.load(), state)

    def test_already_fullscreen_restore_keeps_client_fullscreen(self):
        state = self.state(dict(CLIENT, fullscreen=2, fullscreenClient=2))
        state["entered_fullscreen"] = False
        self.controller.save(state)
        live = dict(FLOATED, fullscreen=0)
        with patch.object(fv, "read_clients", side_effect=lambda: [copy.deepcopy(live)]), \
                patch.object(fv, "hypr", return_value=json.dumps([MONITOR])), \
                patch.object(fv, "send_key") as key, \
                patch.object(fv, "dispatch", side_effect=fake_dispatch(live)) as dsp:
            self.controller.restore(state)
        key.assert_not_called()
        fullscreen = [c for c in dsp.call_args_list if c.args[0] == "window.fullscreen_state"]
        self.assertTrue(all(c.kwargs["client"] != 0 for c in fullscreen))
        self.assertEqual(fullscreen[-1], call("window.fullscreen_state", window="address:0x123",
                                              action="set", internal=2, client=2))
        self.assertFalse(self.controller.path.exists())

    def test_failed_restore_postcondition_keeps_state(self):
        # An unpinned window whose mode change or workspace move did not take.
        for dropped in ("window.float", "workspace"):
            state = self.state()
            self.controller.save(state)
            live = copy.deepcopy(FLOATED)
            applied = fake_dispatch(live)
            def dispatch(method, **kwargs):
                if method != dropped and dropped not in kwargs:
                    applied(method, **kwargs)
            with self.subTest(dropped=dropped), \
                    patch.object(fv, "read_clients", side_effect=lambda: [copy.deepcopy(live)]), \
                    patch.object(fv, "hypr", return_value=json.dumps([MONITOR])), \
                    patch.object(fv, "send_key"), patch.object(fv, "dispatch", side_effect=dispatch):
                with self.assertRaisesRegex(RuntimeError, "did not return"):
                    self.controller.restore(state)
                self.assertEqual(self.controller.load(), state)

    def test_pinned_window_returns_after_workspace_switch(self):
        original = dict(CLIENT, floating=True, pinned=True, at=[100, 150], size=[800, 450])
        live = copy.deepcopy(original)
        with patch.object(fv, "hypr", side_effect=fake_hypr(active=original)), \
                patch.object(fv, "read_clients", side_effect=lambda: [copy.deepcopy(live)]), \
                patch.object(fv, "send_key"), patch.object(fv.time, "sleep"), \
                patch.object(fv, "dispatch", side_effect=fake_dispatch(live)):
            self.controller.enter(original, 600)
            state = self.controller.load()
            self.assertEqual(state["original"]["workspace"], dict(id=7, name="7"))
            self.controller.restore(state)
        self.assertFalse(self.controller.path.exists())
        self.assertTrue(live["floating"])
        self.assertTrue(live["pinned"])
        self.assertEqual(live["workspace"], MONITOR["activeWorkspace"])

    def test_named_workspaces_use_name_selector(self):
        named = dict(id=-1337, name="video")
        monitor = dict(MONITOR, activeWorkspace=named)
        live = copy.deepcopy(CLIENT)
        with patch.object(fv, "hypr", side_effect=fake_hypr(monitor=monitor)), \
                patch.object(fv, "read_clients", side_effect=lambda: [copy.deepcopy(live)]), \
                patch.object(fv, "send_key"), patch.object(fv.time, "sleep"), \
                patch.object(fv, "dispatch", side_effect=fake_dispatch(live, named)) as dsp:
            self.controller.enter(CLIENT, 600)
        dsp.assert_any_call("window.move", window="address:0x123", workspace="name:video", follow=False)
        self.assertNotIn(-1337, [c.kwargs.get("workspace") for c in dsp.call_args_list])

        state = self.state(dict(CLIENT, workspace=named))
        self.controller.save(state)
        live = copy.deepcopy(FLOATED)
        with patch.object(fv, "read_clients", side_effect=lambda: [copy.deepcopy(live)]), \
                patch.object(fv, "hypr", return_value=json.dumps([MONITOR])), \
                patch.object(fv, "send_key"), \
                patch.object(fv, "dispatch", side_effect=fake_dispatch(live)) as dsp:
            self.controller.restore(state)
        dsp.assert_any_call("window.move", window="address:0x123", workspace="name:video", follow=False)
        self.assertEqual(live["workspace"]["name"], "video")
        self.assertFalse(self.controller.path.exists())

    def test_enter_unpins_only_pinned_windows(self):
        for pinned in (False, True):
            target = dict(CLIENT, pinned=pinned)
            live = copy.deepcopy(target)
            with self.subTest(pinned=pinned), patch.object(fv, "hypr", side_effect=fake_hypr()), \
                    patch.object(fv, "read_clients", side_effect=lambda: [copy.deepcopy(live)]), \
                    patch.object(fv, "send_key"), patch.object(fv.time, "sleep"), \
                    patch.object(fv, "dispatch", side_effect=fake_dispatch(live)) as dsp:
                self.controller.enter(target, 600)
                unpinned = call("window.pin", window="address:0x123", action="disable") in dsp.call_args_list
                self.assertEqual(unpinned, pinned)

    def test_dispatch_raises_on_failed_result(self):
        with patch.object(fv, "hypr", return_value="ok") as hypr:
            fv.dispatch("window.pin", window="address:0x123", action="disable")
        command, code = hypr.call_args.args
        self.assertEqual(command, "eval")
        self.assertIn('local r = hl.dispatch(hl.dsp.window.pin({window="address:0x123",action="disable"}))', code)
        self.assertIn('if r and r.ok == false then error("window.pin: " .. tostring(r.error or r.code), 0) end', code)

    def test_notify_is_best_effort(self):
        for error in (FileNotFoundError("notify-send"), fv.subprocess.TimeoutExpired("notify-send", 4)):
            with self.subTest(error=error), patch.object(fv.subprocess, "run", side_effect=error):
                fv.notify("message")

    def test_no_youtube_does_not_mutate_desktop(self):
        with patch.object(fv, "read_clients", return_value=[]), patch.object(fv, "dispatch") as dsp, \
                patch.object(fv.subprocess, "run", return_value=SimpleNamespace(returncode=1)):
            with self.assertRaisesRegex(RuntimeError, "Open a YouTube video"):
                self.controller.run(SimpleNamespace(action="toggle", window=None, width=600))
        dsp.assert_not_called()

    def test_locked_session_does_not_mutate_desktop(self):
        with patch.object(fv, "read_clients", return_value=[CLIENT]), patch.object(fv, "dispatch") as dsp, \
                patch.object(fv.subprocess, "run", return_value=SimpleNamespace(returncode=0)):
            with self.assertRaisesRegex(RuntimeError, "Unlock"):
                self.controller.run(SimpleNamespace(action="toggle", window=None, width=600))
        dsp.assert_not_called()
        self.assertFalse(self.controller.path.exists())

    def test_reject_group_and_special_workspace(self):
        for client in (dict(CLIENT, grouped=["0x456"]),
                       dict(CLIENT, workspace=dict(id=-98, name="special:scratchpad"))):
            with self.subTest(client=client), self.assertRaises(RuntimeError):
                fv.choose_window([client])

    def test_scaled_and_rotated_geometry_stays_on_display(self):
        for scale, transform in ((1, 0), (1.5, 0), (1, 1), (2, 3)):
            monitor = dict(MONITOR, scale=scale, transform=transform, x=-1920)
            x, y, w, h = fv.corner_geometry(monitor)
            dw, dh = (1080, 1920) if transform % 2 else (1920, 1080)
            self.assertGreaterEqual(x, monitor["x"])
            self.assertGreaterEqual(y, 30)
            self.assertLessEqual(x + w, monitor["x"] + dw / scale)
            self.assertLessEqual(y + h, dh / scale)
            self.assertAlmostEqual(w / h, 16 / 9, delta=.01)

    def hold_lock(self):
        lock = self.controller.lock_path.open("w")
        self.addCleanup(lock.close)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_status_does_not_wait_for_lock(self):
        self.controller.save(self.state())
        self.hold_lock()
        output = io.StringIO()
        with patch.object(fv, "read_clients", return_value=[CLIENT]), contextlib.redirect_stdout(output):
            self.assertEqual(self.controller.run(SimpleNamespace(action="status")), 0)
        self.assertEqual(json.loads(output.getvalue()), {"active": True})

    def test_toggle_runs_unless_a_mutator_holds_lock(self):
        self.controller.save(self.state())
        args = SimpleNamespace(action="toggle", window=None, width=600)
        with patch.object(fv, "read_clients", return_value=[CLIENT]), \
                patch.object(fv.subprocess, "run", return_value=SimpleNamespace(returncode=1)), \
                patch.object(fv.Controller, "restore") as restore:
            with contextlib.redirect_stdout(io.StringIO()):
                self.controller.run(SimpleNamespace(action="status"))
            self.controller.run(args)
            restore.assert_called_once()
            self.hold_lock()
            self.controller.run(args)
            restore.assert_called_once()

    def test_missing_monitor_raises_clear_error(self):
        def hypr(*args):
            return json.dumps([dict(MONITOR, id=9)] if args == ("-j", "monitors") else {})

        with patch.object(fv, "hypr", side_effect=hypr), patch.object(fv, "dispatch") as dsp:
            with self.assertRaisesRegex(RuntimeError, "Could not find the display"):
                self.controller.enter(CLIENT, 600)
        dsp.assert_not_called()

    def test_unexpected_error_notifies(self):
        with patch.object(fv.sys, "argv", ["omafloat"]), patch.object(fv, "notify") as notify, \
                patch.object(fv.Controller, "run", side_effect=KeyError("monitor")), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(fv.main(), 1)
        notify.assert_called_once()

    def test_failed_refocus_keeps_original_error(self):
        other = dict(CLIENT, address="0x456")
        def hypr(*args):
            if args == ("-j", "monitors"):
                return json.dumps([MONITOR])
            if args == ("-j", "activewindow"):
                return json.dumps(other)
            return "true"
        def dispatch(method, **kwargs):
            if method == "window.resize" or (method == "focus" and kwargs["window"] == "address:0x456"):
                raise RuntimeError(method + " failed")

        with patch.object(fv, "hypr", side_effect=hypr), \
                patch.object(fv, "read_clients", return_value=[CLIENT, other]), \
                patch.object(fv, "send_key"), patch.object(fv.time, "sleep"), \
                patch.object(fv, "dispatch", side_effect=dispatch):
            with self.assertRaisesRegex(RuntimeError, "window.resize failed"):
                self.controller.enter(CLIENT, 600)

    def test_widget_version_matches_manifest(self):
        manifest = json.loads((ROOT / "manifest.json").read_text())
        widget = re.search(r'version: "([^"]+)"', (ROOT / "OmaFloatWidget.qml").read_text())
        self.assertEqual(widget.group(1), manifest["version"])

    def test_invalid_state_is_ignored(self):
        for value in ("[1]", '{"version":2}', "broken"):
            self.controller.path.write_text(value)
            self.assertIsNone(self.controller.load())


if __name__ == "__main__":
    unittest.main()
