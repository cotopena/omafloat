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
import threading
import shutil
from types import SimpleNamespace
import unittest
from unittest.mock import call, patch

import subprocess
REAL_SUBPROCESS_RUN = subprocess.run

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_loader("omapeek", SourceFileLoader("omapeek", str(ROOT / "bin/omapeek")))
fv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fv)
CLIENT = dict(address="0x123", pid=42, stableId="1800002b", workspace=dict(id=7, name="7"),
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
        elif method == "window.resize":
            live["size"] = [kwargs["x"], kwargs["y"]]
        elif method == "window.move" and "x" in kwargs:
            live["at"] = [kwargs["x"], kwargs["y"]]
        elif method == "window.move" and "monitor" in kwargs:
            live["monitor"] = 1 if kwargs["monitor"] == "DP-1" else 2
        elif method == "window.move" and "workspace" in kwargs:
            ref = str(kwargs["workspace"])
            live["workspace"] = (dict(id=-99, name=ref) if ref.startswith("special:") else dict(id=-1337, name=ref[5:]) if ref.startswith("name:")
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
            with self.assertRaisesRegex(RuntimeError, "disconnected. Choose Restore original window again to release"):
                self.controller.restore(state)
        self.assertEqual(self.controller.load(), dict(self.state(), restore_failed=True))

    def test_repeated_dispatch_failure_releases_window(self):
        self.controller.save(self.state())
        with patch.object(fv, "read_clients", return_value=[FLOATED]), patch.object(fv, "send_key"), \
                patch.object(fv, "dispatch", side_effect=RuntimeError("disconnected")):
            with self.assertRaisesRegex(RuntimeError, "again to release"):
                self.controller.restore(self.controller.load())
            with self.assertRaisesRegex(RuntimeError, "OmaPeek released the YouTube window"):
                self.controller.restore(self.controller.load())
        self.assertFalse(self.controller.path.exists())

    def hidden_dispatch(self, live, blocked):
        # Both restore attempts fail before return_window reaches the workspace move.
        applied = fake_dispatch(live)
        def dispatch(method, **kwargs):
            if method == "window.fullscreen_state" or kwargs.get("workspace") in blocked:
                raise RuntimeError("fullscreen failed")
            applied(method, **kwargs)
        return dispatch

    def test_repeated_failure_moves_hidden_window_before_release(self):
        # The original workspace is tried first; the focused display's workspace is the fallback.
        for blocked, landed in (((), 7), ((7,), 1)):
            self.controller.save(self.state())
            live = dict(copy.deepcopy(FLOATED), pinned=False, workspace=dict(id=-99, name="special:omapeek-hidden"))
            with self.subTest(blocked=blocked), \
                    patch.object(fv, "read_clients", side_effect=lambda: [copy.deepcopy(live)]), \
                    patch.object(fv, "hypr", side_effect=fake_hypr()), patch.object(fv, "send_key"), \
                    patch.object(fv, "dispatch", side_effect=self.hidden_dispatch(live, blocked)) as dsp:
                with self.assertRaisesRegex(RuntimeError, "fullscreen failed. Choose Restore original window again"):
                    self.controller.restore(self.controller.load())
                with self.assertRaisesRegex(RuntimeError, "fullscreen failed. OmaPeek released the YouTube window"):
                    self.controller.restore(self.controller.load())
                dsp.assert_any_call("window.move", window="address:0x123", workspace=7, follow=False)
                self.assertEqual(live["workspace"]["id"], landed)
                self.assertFalse(self.controller.path.exists())

    def test_hidden_window_is_never_released_while_still_hidden(self):
        self.controller.save(self.state())
        live = dict(copy.deepcopy(FLOATED), pinned=False, workspace=dict(id=-99, name="special:omapeek-hidden"))
        with patch.object(fv, "read_clients", side_effect=lambda: [copy.deepcopy(live)]), \
                patch.object(fv, "hypr", side_effect=fake_hypr()), patch.object(fv, "send_key"):
            with patch.object(fv, "dispatch", side_effect=self.hidden_dispatch(live, (7, 1))) as dsp:
                with self.assertRaisesRegex(RuntimeError, "again to release"):
                    self.controller.restore(self.controller.load())
                # Every later failure keeps tracking instead of stranding an untracked hidden window.
                for _ in range(2):
                    with self.assertRaisesRegex(RuntimeError, "^fullscreen failed. YouTube is still hidden; "
                                                "choose Restore original window again or close"):
                        self.controller.restore(self.controller.load())
            dsp.assert_any_call("window.move", window="address:0x123", workspace=7, follow=False)
            dsp.assert_any_call("window.move", window="address:0x123", workspace=1, follow=False)
            self.assertEqual(live["workspace"]["name"], "special:omapeek-hidden")
            self.assertEqual(self.controller.load(), dict(self.state(), restore_failed=True))
            # Once the compositor cooperates again, Restore returns the window and clears tracking.
            with patch.object(fv, "dispatch", side_effect=fake_dispatch(live)):
                self.controller.restore(self.controller.load())
        self.assertEqual((live["workspace"]["id"], live["floating"]), (7, False))
        self.assertFalse(self.controller.path.exists())

    def migrated_dispatch(self, live):
        # Undock/redock: workspace 7 stayed on eDP-1 although DP-1 is connected again.
        applied = fake_dispatch(live)
        def dispatch(method, **kwargs):
            applied(method, **kwargs)
            if method == "window.move" and kwargs.get("workspace") == 7:
                live["monitor"] = 2
        return dispatch

    def test_workspace_on_another_monitor_restores(self):
        self.controller.save(self.state())
        live = copy.deepcopy(FLOATED)
        laptop = dict(MONITOR, id=2, name="eDP-1", x=1920)
        with patch.object(fv, "read_clients", side_effect=lambda: [copy.deepcopy(live)]), \
                patch.object(fv, "hypr", return_value=json.dumps([MONITOR, laptop])), \
                patch.object(fv, "send_key"), patch.object(fv, "dispatch", side_effect=self.migrated_dispatch(live)) as dsp:
            self.controller.restore(self.controller.load())
        dsp.assert_any_call("window.move", window="address:0x123", monitor="DP-1")
        dsp.assert_any_call("window.move", window="address:0x123", workspace=7, follow=False)
        self.assertEqual((live["monitor"], live["workspace"]["id"], live["floating"]), (2, 7, False))
        self.assertFalse(self.controller.path.exists())

    def test_floating_original_on_moved_workspace_restores_size_only(self):
        self.controller.save(self.state(dict(CLIENT, floating=True, at=[100, 150], size=[800, 450])))
        live = copy.deepcopy(FLOATED)
        laptop = dict(MONITOR, id=2, name="eDP-1", x=1920)
        with patch.object(fv, "read_clients", side_effect=lambda: [copy.deepcopy(live)]), \
                patch.object(fv, "hypr", return_value=json.dumps([MONITOR, laptop])), \
                patch.object(fv, "send_key"), patch.object(fv, "dispatch", side_effect=self.migrated_dispatch(live)) as dsp:
            self.controller.restore(self.controller.load())
        dsp.assert_any_call("window.resize", window="address:0x123", x=800, y=450, relative=False)
        self.assertFalse(any(c.args[0] == "window.move" and "x" in c.kwargs for c in dsp.call_args_list))
        self.assertEqual((live["at"], live["size"]), (FLOATED["at"], [800, 450]))
        self.assertFalse(self.controller.path.exists())

    def test_failed_rollback_message_does_not_repeat_guidance(self):
        def dispatch(method, **kwargs):
            if method == "window.resize":
                raise RuntimeError("resize failed")
        with patch.object(fv, "hypr", side_effect=fake_hypr()), \
                patch.object(fv, "read_clients", return_value=[FLOATED]), \
                patch.object(fv, "send_key"), patch.object(fv.time, "sleep"), \
                patch.object(fv, "dispatch", side_effect=dispatch):
            with self.assertRaises(RuntimeError) as raised:
                self.controller.enter(CLIENT, 600)
        self.assertEqual(str(raised.exception), "resize failed Return failed: YouTube did not return to its "
                         "previous layout. Choose Restore original window again to release the window as it is.")
        self.assertTrue(self.controller.load()["restore_failed"])

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
                with self.assertRaisesRegex(RuntimeError, "did not return.*again to release the window"):
                    self.controller.restore(state)
                self.assertEqual(self.controller.load(), dict(self.state(), restore_failed=True))
                # A second consecutive failure releases the window instead of retrying forever.
                with self.assertRaisesRegex(RuntimeError, "did not return.*OmaPeek released"):
                    self.controller.restore(self.controller.load())
                self.assertFalse(self.controller.path.exists())

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
        with patch.object(fv, "read_clients", return_value=[CLIENT]), patch.object(fv, "hypr", side_effect=fake_hypr()), contextlib.redirect_stdout(output):
            self.assertEqual(self.controller.run(SimpleNamespace(action="status")), 0)
        self.assertTrue(json.loads(output.getvalue())["active"])

    def test_toggle_runs_unless_a_mutator_holds_lock(self):
        self.controller.save(self.state())
        args = SimpleNamespace(action="toggle", window=None, width=600)
        with patch.object(fv, "read_clients", return_value=[CLIENT]), \
                patch.object(fv.subprocess, "run", return_value=SimpleNamespace(returncode=1)), \
                patch.object(fv.Controller, "restore") as restore, patch.object(fv, "hypr", side_effect=fake_hypr()):
            with contextlib.redirect_stdout(io.StringIO()):
                self.controller.run(SimpleNamespace(action="status"))
            self.controller.run(args)
            restore.assert_called_once()
            self.hold_lock()
            with self.assertRaisesRegex(RuntimeError, "busy"):
                with patch.object(fv.time, "monotonic", side_effect=[0, 4]):
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
        with patch.object(fv.sys, "argv", ["omapeek"]), patch.object(fv, "notify") as notify, \
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
        widget = re.search(r'version: "([^"]+)"', (ROOT / "OmaPeekWidget.qml").read_text())
        self.assertEqual(widget.group(1), manifest["version"])

    def configure_args(self, action="configure", **values):
        return SimpleNamespace(action=action, width=None, corner=None, monitor=None,
                               follow=None, above=None, **{}) if not values else SimpleNamespace(
            **dict(dict(action=action, width=None, corner=None, monitor=None, follow=None, above=None), **values))

    def test_monitor_change_repins_exactly_once(self):
        live = copy.deepcopy(FLOATED)
        state = self.state()
        other = dict(MONITOR, id=2, name="HDMI-A-1")
        with patch.object(fv, "hypr", return_value=json.dumps([MONITOR, other])), patch.object(
                fv, "dispatch", side_effect=fake_dispatch(live)) as dsp:
            self.controller.configure(state, live, self.configure_args(monitor="HDMI-A-1"))
        pins = [c.kwargs["action"] for c in dsp.call_args_list if c.args[0] == "window.pin"]
        self.assertEqual(pins, ["disable", "enable"])
        self.assertTrue(live["pinned"])

    def test_hide_is_idempotent_and_show_repins_once(self):
        live = copy.deepcopy(FLOATED)
        state = self.state()
        with patch.object(fv, "hypr", return_value=json.dumps([MONITOR])), patch.object(
                fv, "dispatch", side_effect=fake_dispatch(live)) as dsp:
            self.controller.configure(state, live, self.configure_args("hide"))
            visible = copy.deepcopy(state["visible_workspace"])
            self.controller.configure(state, live, self.configure_args("hide"))
            self.assertEqual(state["visible_workspace"], visible)
            dsp.reset_mock()
            self.controller.configure(state, live, self.configure_args("show"))
        pins = [c.kwargs["action"] for c in dsp.call_args_list if c.args[0] == "window.pin"]
        self.assertEqual(pins, ["enable"])

    def test_behavior_changes_preserve_geometry_and_original(self):
        live = copy.deepcopy(FLOATED)
        state = self.state()
        original = copy.deepcopy(state["original"])
        state["options"] = dict(width=800, corner="top-left", follow=True, above=True)
        with patch.object(fv, "hypr", return_value=json.dumps([MONITOR])), patch.object(fv, "dispatch") as dsp:
            self.controller.configure(state, live, self.configure_args(follow=False, above=False))
        self.assertEqual(state["original"], original)
        self.assertEqual(state["options"]["width"], 800)
        self.assertFalse(any(c.args[0] in {"window.resize", "window.move"} for c in dsp.call_args_list))

    def test_disconnected_selection_does_not_mutate(self):
        with patch.object(fv, "hypr", return_value=json.dumps([MONITOR])), patch.object(fv, "dispatch") as dsp:
            with self.assertRaisesRegex(RuntimeError, "no longer connected"):
                self.controller.configure(self.state(), FLOATED, self.configure_args(monitor="missing"))
        dsp.assert_not_called()

    def test_all_corners_and_tiny_display(self):
        for corner in ("top-left", "top-right", "bottom-left", "bottom-right"):
            x, y, w, h = fv.corner_geometry(MONITOR, 800, corner)
            self.assertGreaterEqual(x, 20)
            self.assertGreaterEqual(y, 50)
            self.assertLessEqual(x + w, 1900)
            self.assertLessEqual(y + h, 1060)
        with self.assertRaisesRegex(RuntimeError, "too small"):
            fv.corner_geometry(dict(MONITOR, width=70, height=70))

    def test_failed_configure_retains_original_for_restore(self):
        state = self.state()
        with patch.object(fv, "hypr", return_value=json.dumps([MONITOR])), patch.object(
                fv, "dispatch", side_effect=RuntimeError("disconnected")):
            with self.assertRaisesRegex(RuntimeError, "disconnected"):
                self.controller.configure(state, FLOATED, self.configure_args(corner="top-left"))
        self.assertEqual(self.controller.load()["original"], CLIENT)

    def test_show_preserves_manually_moved_geometry(self):
        live = copy.deepcopy(FLOATED)
        live["at"], live["size"] = [123, 234], [700, 394]
        state = self.state()
        state["options"] = dict(width=600, corner="bottom-right", follow=True, above=False)
        with patch.object(fv, "hypr", return_value=json.dumps([MONITOR])), patch.object(
                fv, "dispatch", side_effect=fake_dispatch(live)):
            self.controller.configure(state, live, self.configure_args("hide"))
            self.controller.configure(state, live, self.configure_args("show"))
        self.assertEqual(live["at"], [123, 234])
        self.assertEqual(live["size"], [700, 394])

    def test_hidden_monitor_selection_stays_hidden(self):
        live = dict(FLOATED, pinned=False, workspace=dict(id=-99, name="special:omapeek-hidden"))
        state = self.state()
        state["options"] = dict(width=600, corner="bottom-right", follow=True, above=False)
        other = dict(MONITOR, id=2, name="HDMI-A-1")
        with patch.object(fv, "hypr", return_value=json.dumps([MONITOR, other])), patch.object(
                fv, "dispatch", side_effect=fake_dispatch(live)):
            self.controller.configure(state, live, self.configure_args(monitor="HDMI-A-1"))
        self.assertEqual(live["workspace"]["name"], "special:omapeek-hidden")
        self.assertFalse(live["pinned"])

    def test_maintenance_only_raises_visible_enabled_float(self):
        for hidden, above in ((False, True), (True, True), (False, False)):
            state = self.state()
            state["options"] = dict(above=above)
            live = dict(FLOATED, workspace=dict(id=-99, name="special:omapeek-hidden")) if hidden else FLOATED
            with patch.object(fv, "hypr", return_value=json.dumps([MONITOR])), patch.object(fv, "raise_window") as raise_win, patch.object(fv, "dispatch") as dsp:
                self.controller.configure(state, live, self.configure_args("maintain"))
            self.assertEqual(raise_win.called, above and not hidden)
            dsp.assert_not_called()

    def test_state_file_private_and_malformed_nested_state_rejected(self):
        self.controller.save(self.state())
        self.assertEqual(self.controller.path.stat().st_mode & 0o777, 0o600)
        for key, value in (("workspace", []), ("size", [0, 100]), ("at", [1]), ("floating", "false")):
            state = self.state()
            state["original"][key] = value
            self.controller.save(state)
            self.assertIsNone(self.controller.load())
        for marker in ("true", 1, None):
            self.controller.save(dict(self.state(), restore_failed=marker))
            self.assertIsNone(self.controller.load())
        self.controller.save(dict(self.state(), restore_failed=True))
        self.assertTrue(self.controller.load()["restore_failed"])

    def test_hidden_display_then_show_follow_off_keeps_destination(self):
        live = copy.deepcopy(FLOATED)
        live["pinned"] = False
        state = self.state()
        state["options"] = dict(width=600, corner="bottom-right", follow=False, above=False)
        other = dict(MONITOR, id=2, name="HDMI-A-1", x=1920, width=2560,
                     activeWorkspace=dict(id=9, name="9"))
        def effects(method, **kwargs):
            fake_dispatch(live)(method, **kwargs)
            if method == "window.move" and "workspace" in kwargs:
                if kwargs["workspace"] == 1:
                    live["monitor"] = 1
                elif kwargs["workspace"] == 9:
                    live["monitor"] = 2
        with patch.object(fv, "hypr", return_value=json.dumps([MONITOR, other])), patch.object(
                fv, "dispatch", side_effect=effects):
            self.controller.configure(state, live, self.configure_args("hide"))
            self.controller.configure(state, live, self.configure_args(monitor="HDMI-A-1"))
            self.assertEqual(live["workspace"]["name"], "special:omapeek-hidden")
            self.assertEqual(state["visible_destination"], dict(monitor_name="HDMI-A-1", workspace=dict(id=9, name="9")))
            self.controller.configure(state, live, self.configure_args("show"))
        self.assertEqual(live["monitor"], 2)
        self.assertEqual(live["workspace"]["id"], 9)
        self.assertFalse(live["pinned"])
        x, y, w, h = fv.corner_geometry(other)
        self.assertEqual(live["at"], [x, y])
        self.assertEqual(live["size"], [w, h])
        self.assertEqual(state["original"], CLIENT)

    def hide_then_unplug(self, follow):
        # Hide on the external display, then undock: only the focused laptop panel remains.
        laptop = dict(MONITOR, name="eDP-1")
        external = dict(MONITOR, id=2, name="HDMI-A-1", x=1920, width=2560, focused=False,
                        activeWorkspace=dict(id=9, name="9"))
        live = dict(copy.deepcopy(FLOATED), monitor=2, workspace=dict(id=9, name="9"), at=[3800, 900], pinned=follow)
        state = self.state()
        state["options"] = dict(width=600, corner="bottom-right", follow=follow, above=False)
        def effects(method, **kwargs):
            fake_dispatch(live)(method, **kwargs)
            if method == "window.move" and "monitor" in kwargs:
                live["monitor"] = 1 if kwargs["monitor"] == "eDP-1" else 2
        with patch.object(fv, "hypr", return_value=json.dumps([laptop, external])), patch.object(
                fv, "dispatch", side_effect=effects):
            self.controller.configure(state, live, self.configure_args("hide"))
        self.assertEqual(state["visible_destination"]["monitor_name"], "HDMI-A-1")
        return state, live, laptop, effects

    def test_show_after_hidden_display_unplugged_uses_focused_display(self):
        for follow in (True, False):
            with self.subTest(follow=follow):
                state, live, laptop, effects = self.hide_then_unplug(follow)
                with patch.object(fv, "hypr", return_value=json.dumps([laptop])), patch.object(
                        fv, "dispatch", side_effect=effects) as dsp:
                    self.controller.configure(state, live, self.configure_args("show"))
                dsp.assert_any_call("window.move", window="address:0x123", monitor="eDP-1")
                dsp.assert_any_call("window.move", window="address:0x123", workspace=1, follow=False)
                self.assertNotIn(9, [c.kwargs.get("workspace") for c in dsp.call_args_list])
                x, y, w, h = fv.corner_geometry(laptop)
                self.assertEqual((live["monitor"], live["at"], live["size"]), (1, [x, y], [w, h]))
                self.assertEqual(live["workspace"], dict(id=1, name="1"))
                self.assertEqual(live["pinned"], follow)
                pins = [c.kwargs["action"] for c in dsp.call_args_list if c.args[0] == "window.pin"]
                self.assertEqual(pins, ["enable"] if follow else [])
                self.assertEqual(self.controller.load()["visible_destination"],
                                 dict(monitor_name="eDP-1", workspace=dict(id=1, name="1")))

    def test_hidden_configure_with_unplugged_display_retargets_destination(self):
        state, live, laptop, effects = self.hide_then_unplug(True)
        with patch.object(fv, "hypr", return_value=json.dumps([laptop])), patch.object(
                fv, "dispatch", side_effect=effects) as dsp:
            self.controller.configure(state, live, self.configure_args("maintain"))
            dsp.assert_not_called()
            self.controller.configure(state, live, self.configure_args(width=800))
            self.controller.configure(state, live, self.configure_args(follow=False))
            with self.assertRaisesRegex(RuntimeError, "no longer connected"):
                self.controller.configure(state, live, self.configure_args(monitor="HDMI-A-1"))
        self.assertEqual(live["workspace"]["name"], "special:omapeek-hidden")
        saved = self.controller.load()
        self.assertEqual(saved["visible_destination"]["monitor_name"], "eDP-1")
        self.assertNotIn("visible_geometry", saved)
        self.assertEqual((saved["options"]["width"], saved["options"]["follow"]), (800, False))

    def test_user_command_waits_for_background_lock_then_runs(self):
        self.controller.save(self.state())
        for action in ("toggle", "hide"):
            with self.subTest(action=action), self.controller.lock_path.open("w") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                release = threading.Timer(0.06, lambda: fcntl.flock(lock, fcntl.LOCK_UN))
                release.start()
                try:
                    with patch.object(fv, "read_clients", return_value=[FLOATED]), patch.object(
                            fv.subprocess, "run", return_value=SimpleNamespace(returncode=1)), patch.object(
                            fv.Controller, "restore") as restore, patch.object(fv.Controller, "configure") as configure:
                        self.controller.run(SimpleNamespace(action=action))
                    (restore if action == "toggle" else configure).assert_called_once()
                finally:
                    release.join()

    def test_maintenance_skips_lock_without_waiting_or_reading(self):
        self.hold_lock()
        with patch.object(fv.time, "sleep") as sleep, patch.object(fv, "read_clients") as read:
            self.assertEqual(self.controller.run(SimpleNamespace(action="maintain")), 0)
        sleep.assert_not_called()
        read.assert_not_called()

    def test_raise_rejects_missing_or_malformed_identity_before_eval(self):
        for stable in (None, "", "different", "0x42", "-42", " 42", "42 ",
                       "4.2", 42, True, "8000000000000000"):
            with self.subTest(stable=stable), patch.object(fv, "hypr") as hypr:
                with self.assertRaisesRegex(RuntimeError, "Cannot safely identify"):
                    fv.raise_window(dict(CLIENT, stableId=stable))
                hypr.assert_not_called()
        for key in ("stableId", "pid"):
            client = dict(CLIENT)
            del client[key]
            with self.subTest(missing=key), patch.object(fv, "hypr") as hypr:
                with self.assertRaisesRegex(RuntimeError, "Cannot safely identify"):
                    fv.raise_window(client)
                hypr.assert_not_called()
        for pid in (None, "42", True):
            with self.subTest(pid=pid), patch.object(fv, "hypr") as hypr:
                with self.assertRaisesRegex(RuntimeError, "Cannot safely identify"):
                    fv.raise_window(dict(CLIENT, pid=pid))
                hypr.assert_not_called()

    @unittest.skipUnless(shutil.which("lua"), "Lua interpreter needed for compositor eval regression")
    def test_raise_eval_identity_races_and_failed_result(self):
        # Execute the production eval in Lua, with a compositor stub. Never hyprctl.
        # Include digit-only JSON IDs: "42" is hexadecimal 66, not decimal 42.
        for stable, integer in (("1800002b", 402653227), ("42", 66), ("1800002B", 402653227)):
            window = ('{pid=42,stable_id=' + str(integer) +
                      ',mapped=true,floating=true,workspace={name="1"}}')
            cases = {
                "missing": ("nil", "false:0"),
                "missing_stable": (window.replace('stable_id=' + str(integer), 'stable_id=nil'), "false:0"),
                "reused": (window.replace('stable_id=' + str(integer), 'stable_id=99'), "false:0"),
                "wrong_pid": (window.replace('pid=42', 'pid=99'), "false:0"),
                "hidden": (window.replace('name="1"', 'name="special:omapeek-hidden"'), "true:0"),
                "unmapped": (window.replace('mapped=true', 'mapped=false'), "true:0"),
                "tiled": (window.replace('floating=true', 'floating=false'), "true:0"),
                "visible": (window, "true:1"),
                "failed": (window, "false:1"),
            }
            if stable == "42":
                cases["decimal_mismatch"] = (window.replace('stable_id=66', 'stable_id=42'), "false:0")
            for name, (current, expected) in cases.items():
                with self.subTest(stable=stable, case=name):
                    script = ('local count=0; local current=' + current + '; '
                              'hl={get_window=function(s) assert(s=="address:0x123"); return current end, '
                              'dsp={window={alter_zorder=function(a) assert(a.window=="address:0x123" and a.mode=="top"); return a end}}, '
                              'dispatch=function(a) count=count+1; return {ok=' + ('false' if name == "failed" else 'true') + ',error="denied"} end}; '
                              'local ok,err=pcall(function() ' + fv.raise_script(dict(CLIENT, stableId=stable)) + ' end); '
                              'print(tostring(ok)..":"..count); '
                              'if not ok then print(err) end')
                    # Bypass the subprocess guard only for this Lua executable and stdin.
                    with patch.object(fv.subprocess, "run", wraps=REAL_SUBPROCESS_RUN):
                        result = subprocess.run([shutil.which("lua"), "-"], input=script,
                                                text=True, capture_output=True, check=True, timeout=2)
                    lines = result.stdout.splitlines()
                    self.assertEqual(lines[0], expected)
                    if expected == "false:0":
                        self.assertIn("closed or changed identity", lines[1])
                    elif name == "failed":
                        self.assertIn("window.alter_zorder: denied", lines[1])

    def test_invalid_state_is_ignored(self):
        for value in ("[1]", '{"version":2}', "broken"):
            self.controller.path.write_text(value)
            self.assertIsNone(self.controller.load())


if __name__ == "__main__":
    unittest.main()
