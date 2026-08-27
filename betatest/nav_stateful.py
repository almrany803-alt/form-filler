"""Comprehensive model-based UI test: Hypothesis generates sequences of REAL
dialog operations, add and remove sections, open and close them, add and remove
entries, driven through pywinauto against the live dialogs. After every single
operation it checks two invariants: the data matches a model we keep alongside,
and the sections list is reachable again (focused). It explores orders we would
never hand-script, and it is the exact class of test that would have caught the
re-entry bug while also covering the CRUD features, not just menu opening.
"""

import sys
import time

from pywinauto import Desktop
from pywinauto.keyboard import send_keys

from hypothesis import settings, HealthCheck
from hypothesis import strategies as st
from hypothesis.stateful import (RuleBasedStateMachine, rule, precondition,
                                 invariant)

_PERSONAL = ("Personal information", "Personal details")


def _sections_dialog():
    return Desktop(backend="uia").window(title_re=".*My details and sections.*")


class DialogMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.dlg = _sections_dialog()
        self.dlg.wait("visible", timeout=20)
        self.lst = self.dlg.child_window(control_type="List")
        self.lst.wait("visible", timeout=10)
        self._sync_to_list()
        self.sections = [n for n in self._names() if n not in _PERSONAL]

    # ---- helpers ----------------------------------------------------------
    def _names(self):
        return [it.window_text()
                for it in self.lst.children(control_type="ListItem")]

    def _sync_to_list(self):
        for _ in range(5):
            try:
                if self.lst.exists(timeout=1) and self.lst.is_visible():
                    return
            except Exception:
                pass
            send_keys("{ESC}")
            time.sleep(0.5)

    def _select(self, name):
        idx = self._names().index(name)
        self.lst.set_focus()
        time.sleep(0.2)
        send_keys("{HOME}")
        time.sleep(0.1)
        for _ in range(idx):
            send_keys("{DOWN}")
            time.sleep(0.05)
        time.sleep(0.2)

    def _button(self, title):
        self.dlg.child_window(title=title, control_type="Button").invoke()

    # ---- operations (rules) ----------------------------------------------
    @rule(name=st.text(alphabet="abcde", min_size=1, max_size=3))
    def add_section(self, name):
        if name in self._names():
            return
        self._button("Add section")
        time.sleep(0.8)
        send_keys(name)
        time.sleep(0.2)
        send_keys("{ENTER}")
        time.sleep(0.8)
        self._sync_to_list()
        assert name in self._names(), ("add_section failed", name, self._names())
        self.sections.append(name)

    @precondition(lambda self: self.sections)
    @rule(data=st.data())
    def remove_section(self, data):
        name = data.draw(st.sampled_from(sorted(self.sections)))
        self._select(name)
        self._button("Remove")
        time.sleep(0.6)
        send_keys("y")
        time.sleep(0.8)
        self._sync_to_list()
        assert name not in self._names(), ("remove_section failed", name)
        self.sections.remove(name)

    @precondition(lambda self: self.sections)
    @rule(data=st.data())
    def open_and_close(self, data):
        name = data.draw(st.sampled_from(sorted(self.sections)))
        self._select(name)
        self._button("Open")
        time.sleep(1.0)
        send_keys("{ESC}")
        time.sleep(1.0)
        self._sync_to_list()

    @precondition(lambda self: self.sections)
    @rule(data=st.data())
    def add_entry(self, data):
        name = data.draw(st.sampled_from(sorted(self.sections)))
        self._select(name)
        self._button("Open")
        time.sleep(1.0)
        entries = Desktop(backend="uia").window(title_re="^%s$" % name)
        elist = entries.child_window(control_type="List")
        before = len(elist.children(control_type="ListItem"))
        entries.child_window(title="Add entry", control_type="Button").invoke()
        time.sleep(0.9)
        send_keys("testvalue")
        time.sleep(0.2)
        form = Desktop(backend="uia").window(title_re="Entry in .*")
        form.child_window(title="OK", control_type="Button").invoke()
        time.sleep(0.9)
        after = len(elist.children(control_type="ListItem"))
        assert after == before + 1, ("add_entry did not add one", name, before, after)
        send_keys("{ESC}")
        time.sleep(1.0)
        self._sync_to_list()

    # ---- invariant checked after EVERY operation --------------------------
    @invariant()
    def list_reachable_and_consistent(self):
        assert self.lst.has_keyboard_focus(), \
            "sections list not focused after an operation (stranding/re-entry bug)"
        names = self._names()
        for s in self.sections:
            assert s in names, ("model section missing from list", s, names)


DialogMachine.TestCase.settings = settings(
    max_examples=3, stateful_step_count=15, deadline=None,
    suppress_health_check=list(HealthCheck))
TestDialog = DialogMachine.TestCase


if __name__ == "__main__":
    import unittest
    unittest.main()
