import copy
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

fv = SourceFileLoader("float_video", str(Path(__file__).parents[1] / "bin/omafloat")).load_module()
CLIENT = dict(address="0x123", pid=42, stableId="42", workspace=dict(id=7, name="7"),
              monitor=1, floating=False, pinned=False, fullscreen=0, fullscreenClient=0,
              at=[12, 38], size=[1800, 1000], grouped=[],
              **{"class": "chrome-youtube.com__-Profile_3", "title": "Example - YouTube"})
MONITOR = dict(id=1, name="DP-1", width=1920, height=1080, x=0, y=0, scale=1,
               reserved=[0, 30, 0, 0], activeWorkspace=dict(id=1), focused=True)


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = patch.dict(fv.os.environ, XDG_RUNTIME_DIR=self.temp.name)
        self.env.start()
        self.addCleanup(self.env.stop)
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
        with patch.object(fv, "read_clients", return_value=[CLIENT]), \
                patch.object(fv, "hypr", return_value=json.dumps([MONITOR])), \
                patch.object(fv, "send_key") as key, patch.object(fv, "dispatch") as dsp:
            self.controller.restore(state)
        key.assert_called_once_with(CLIENT, "Escape")
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
        with patch.object(fv, "read_clients", return_value=[CLIENT]), \
                patch.object(fv, "dispatch", side_effect=RuntimeError("disconnected")):
            with self.assertRaises(RuntimeError):
                self.controller.restore(state)
        self.assertEqual(self.controller.load(), state)

    def test_already_fullscreen_restore_does_not_send_escape(self):
        state = self.state(dict(CLIENT, fullscreen=2, fullscreenClient=2))
        state["entered_fullscreen"] = False
        with patch.object(fv, "read_clients", return_value=[CLIENT]), \
                patch.object(fv, "hypr", return_value=json.dumps([MONITOR])), \
                patch.object(fv, "send_key") as key, patch.object(fv, "dispatch") as dsp:
            self.controller.restore(state)
        key.assert_not_called()
        dsp.assert_any_call("window.fullscreen_state", window="address:0x123", action="set", internal=2, client=2)

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

    def test_invalid_state_is_ignored(self):
        for value in ("[1]", '{"version":2}', "broken"):
            self.controller.path.write_text(value)
            self.assertIsNone(self.controller.load())


if __name__ == "__main__":
    unittest.main()
