"""Navigation test that reads the real accessibility (UI Automation) tree with
pywinauto instead of counting keystrokes and guessing from speech.

It walks the sections list: for each section it selects it, opens it, closes the
child dialog, and then checks the invariant that actually broke, the sections
list must have keyboard focus again (so it is reachable). On the fixed build this
holds for every section; on the 0.9.53 build, where focus was left on a button,
it fails, which is exactly how we prove the test has teeth.

This is the pywinauto layer; a Hypothesis generator can drive these same steps in
random orders on top of it.
"""

import sys
import time

from pywinauto import Desktop
from pywinauto.keyboard import send_keys


def _dialog():
    dlg = Desktop(backend="uia").window(title_re=".*My details and sections.*")
    dlg.wait("visible", timeout=25)
    return dlg


def main():
    dlg = _dialog()
    lst = dlg.child_window(control_type="List")
    lst.wait("visible", timeout=10)
    labels = [it.window_text() for it in lst.children(control_type="ListItem")]
    n = len(labels)
    print("SECTIONS LIST: %d items: %s" % (n, labels))
    if n < 2:
        print("not enough sections to test re-entry")
        sys.exit(2)

    failures = []
    for idx in range(1, n):     # skip Personal information at 0
        # select item idx from the top, by keyboard, on the real list
        lst.set_focus()
        time.sleep(0.3)
        send_keys("{HOME}")
        time.sleep(0.2)
        for _ in range(idx):
            send_keys("{DOWN}")
            time.sleep(0.1)
        time.sleep(0.3)
        # open the section by double-clicking it: works on both the current
        # build and 0.9.53, since the Open button was removed in 0.9.58 but
        # double-click has always opened.
        try:
            lst.children(control_type="ListItem")[idx].double_click_input()
        except Exception as exc:
            print("  double-click failed (%s), using Enter" % exc)
            send_keys("{ENTER}")
        time.sleep(1.3)
        # close the child dialog and return to the sections list
        send_keys("{ESC}")
        time.sleep(1.3)
        # INVARIANT: the sections list must have keyboard focus again
        try:
            focused = lst.has_keyboard_focus()
        except Exception as exc:
            print("  focus read error:", exc)
            focused = None
        print("  %-22s open+close -> list focused: %s" % (labels[idx], focused))
        if not focused:
            failures.append(labels[idx])

    if failures:
        print("REENTRY BUG: after closing these sections the list was NOT "
              "reachable (focus stranded elsewhere): %s" % failures)
        sys.exit(1)
    print("OK: the sections list is reachable (focused) after every open+close")
    sys.exit(0)


if __name__ == "__main__":
    main()
