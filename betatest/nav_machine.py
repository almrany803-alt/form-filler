"""Hypothesis + pywinauto navigation machine for the sections dialog.

Each rule drives the REAL dialog through the Windows accessibility API
(pywinauto UIA), and the invariant reads the accessibility tree: whenever we are
back at the top dialog, the Sections list must hold keyboard focus. Hypothesis
generates open / close / add sequences we would never hand-script, and when the
invariant breaks it shrinks to the shortest sequence that triggers it.

This is the layer that targets the re-entry / focus bug, the one the data-model
machine cannot see. Windows only (UIA), so it runs in CI, not the sandbox.

Usage:  python nav_machine.py <addon_dir>
Exit 0 = the invariant always held (no re-entry bug). Non-zero = it found one.
"""

import os
import sys
import time
import unittest

from pywinauto import Application
from pywinauto.keyboard import send_keys

from hypothesis import settings
from hypothesis.stateful import (RuleBasedStateMachine, rule, precondition,
                                 invariant)

ADDON_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    "addon", "globalPlugins", "jobFormFiller")
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "dialog_harness.py")
TITLE = "Job Form Filler: My details and sections"


class NavMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.app = Application(backend="uia").start(
            'python "%s" "%s"' % (HARNESS, os.path.abspath(ADDON_DIR)),
            wait_for_idle=False)
        time.sleep(2)
        self.win = self.app.window(title=TITLE)
        self.win.wait("visible ready", timeout=30)
        self.in_child = False

    def _list(self):
        return self.win.child_window(control_type="List")

    def _button(self, name):
        return self.win.child_window(title=name, control_type="Button")

    @precondition(lambda self: not self.in_child)
    @rule()
    def open_section(self):
        # select Experience (index 1; 0 is Personal information) and Open it
        try:
            self._list().select(1)
        except Exception:
            self._list().set_focus()
            send_keys("{HOME}{DOWN}")
        time.sleep(0.4)
        self._button("Open").invoke()
        time.sleep(0.8)
        self.in_child = True

    @precondition(lambda self: self.in_child)
    @rule()
    def close_child(self):
        send_keys("{ESC}")
        time.sleep(0.8)
        self.in_child = False

    @precondition(lambda self: not self.in_child)
    @rule()
    def add_section(self):
        self._button("Add section").invoke()
        time.sleep(0.5)
        send_keys("z{ENTER}")           # name it and OK
        time.sleep(0.6)

    @invariant()
    def list_has_focus_at_top(self):
        # only meaningful at the top dialog, not while a child dialog is open
        if self.in_child:
            return
        assert self._list().has_keyboard_focus(), \
            "Sections list lost keyboard focus (the re-entry trap)"

    def teardown(self):
        try:
            self.app.kill()
        except Exception:
            pass


NavMachine.TestCase.settings = settings(
    max_examples=12, stateful_step_count=8, deadline=None)
TestNav = NavMachine.TestCase


if __name__ == "__main__":
    unittest.main(argv=["x", "TestNav"], exit=True, verbosity=2)
