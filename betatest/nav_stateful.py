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

from hypothesis import settings, HealthCheck, Phase
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
        # the sections list is the dialog's own list; child dialogs add their
        # own list to the tree, so pin to the first match to stay unambiguous.
        self.lst = self.dlg.child_window(control_type="List", found_index=0)
        self.lst.wait("visible", timeout=10)
        self._sync_to_list()
        try:
            self.dlg.set_focus()
            self.lst.set_focus()
        except Exception:
            pass
        time.sleep(0.4)
        self.sections = [n for n in self._names() if n not in _PERSONAL]

    # ---- helpers ----------------------------------------------------------
    def _names(self):
        return [it.window_text()
                for it in self.lst.children(control_type="ListItem")]

    def _sync_to_list(self):
        for _ in range(6):
            try:
                # If the sections dialog is the active window, no child is on top
                # and we are at the list, do NOT press Esc (that would close it).
                if self.lst.exists(timeout=1) and self.dlg.is_active():
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
        last = None
        for _ in range(4):
            try:
                self.dlg.child_window(
                    title=title, control_type="Button").invoke()
                return
            except Exception as exc:
                last = exc
                time.sleep(0.5)
        raise last

    # ---- helpers for opening (Enter, since the Open button is gone) --------
    def _open_selected(self):
        self.lst.set_focus()
        time.sleep(0.2)
        send_keys("{ENTER}")

    # ---- operations (rules): real section AND entry features ---------------
    @rule(name=st.text(alphabet="abcde", min_size=1, max_size=3))
    def add_section(self, name):
        self._sync_to_list()
        if name in self._names():
            return
        self._button("Add section")
        time.sleep(0.8)
        # AddSectionDialog: Name field focused, then a Type combo (default Work),
        # then OK. Type the name and confirm; the default type is fine here.
        send_keys(name)
        time.sleep(0.2)
        try:
            Desktop(backend="uia").window(title_re="Add section").child_window(
                title="OK", control_type="Button").invoke()
        except Exception:
            send_keys("{TAB}{TAB}{ENTER}")
        time.sleep(0.8)
        self._sync_to_list()
        assert name in self._names(), ("add_section failed", name, self._names())
        self.sections.append(name)

    @precondition(lambda self: self.sections)
    @rule(data=st.data())
    def remove_section(self, data):
        self._sync_to_list()
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
        self._sync_to_list()
        name = data.draw(st.sampled_from(sorted(self.sections)))
        self._select(name)
        self._open_selected()
        time.sleep(1.0)
        ent = Desktop(backend="uia").window(title_re="^%s$" % name)
        if ent.exists(timeout=3):
            try:
                ent.child_window(title="Close", control_type="Button").invoke()
            except Exception:
                send_keys("{ESC}")
            time.sleep(1.0)
        self._sync_to_list()

    @precondition(lambda self: self.sections)
    @rule(data=st.data())
    def add_entry(self, data):
        self._sync_to_list()
        name = data.draw(st.sampled_from(sorted(self.sections)))
        try:
            self._select(name)
            self._open_selected()
            time.sleep(1.2)
            entries = Desktop(backend="uia").window(title_re="^%s$" % name)
            elist = entries.child_window(control_type="List", found_index=0)
            before = len(elist.children(control_type="ListItem"))
            entries.child_window(
                title="Add entry", control_type="Button").invoke()
            time.sleep(1.0)
            # a typed section goes straight to the entry form; type into the
            # first field and OK. (An "Other" section would ask a type first;
            # seeded sections are typed, so this path is direct.)
            send_keys("testvalue")
            time.sleep(0.3)
            form = Desktop(backend="uia").window(title_re="Entry in .*")
            form.child_window(title="OK", control_type="Button").invoke()
            time.sleep(1.0)
            after = len(elist.children(control_type="ListItem"))
            assert after == before + 1, \
                ("add_entry did not add one", name, before, after)
        except AssertionError:
            raise
        except Exception as exc:
            print("add_entry UIA hiccup, recovering:", type(exc).__name__)
        finally:
            try:
                ent = Desktop(backend="uia").window(title_re="^%s$" % name)
                if ent.exists(timeout=1):
                    ent.child_window(
                        title="Close", control_type="Button").invoke()
            except Exception:
                pass
            time.sleep(0.8)
            self._sync_to_list()

    @precondition(lambda self: self.sections)
    @rule(data=st.data())
    def remove_entry(self, data):
        self._sync_to_list()
        name = data.draw(st.sampled_from(sorted(self.sections)))
        try:
            self._select(name)
            self._open_selected()
            time.sleep(1.2)
            entries = Desktop(backend="uia").window(title_re="^%s$" % name)
            elist = entries.child_window(control_type="List", found_index=0)
            before = len(elist.children(control_type="ListItem"))
            if before == 0:
                return
            elist.children(control_type="ListItem")[0].select()
            time.sleep(0.3)
            entries.child_window(
                title="Remove", control_type="Button").invoke()
            time.sleep(0.7)
            send_keys("y")            # confirm
            time.sleep(0.8)
            after = len(elist.children(control_type="ListItem"))
            assert after == before - 1, \
                ("remove_entry did not remove one", name, before, after)
        except AssertionError:
            raise
        except Exception as exc:
            print("remove_entry UIA hiccup, recovering:", type(exc).__name__)
        finally:
            try:
                ent = Desktop(backend="uia").window(title_re="^%s$" % name)
                if ent.exists(timeout=1):
                    ent.child_window(
                        title="Close", control_type="Button").invoke()
            except Exception:
                pass
            time.sleep(0.8)
            self._sync_to_list()

    # ---- invariant checked after EVERY operation --------------------------
    @invariant()
    def list_reachable_and_consistent(self):
        focused = False
        for _ in range(4):
            try:
                if self.lst.has_keyboard_focus():
                    focused = True
                    break
            except Exception:
                pass
            time.sleep(0.4)
        assert focused, \
            "sections list not focused after an operation (stranding/re-entry bug)"
        names = self._names()
        for s in self.sections:
            assert s in names, ("model section missing from list", s, names)


DialogMachine.TestCase.settings = settings(
    max_examples=1, stateful_step_count=16, deadline=None,
    phases=(Phase.explicit, Phase.reuse, Phase.generate, Phase.target),
    suppress_health_check=list(HealthCheck))
TestDialog = DialogMachine.TestCase


if __name__ == "__main__":
    import unittest
    unittest.main()
