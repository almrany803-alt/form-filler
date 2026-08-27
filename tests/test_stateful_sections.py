"""Model-based (stateful) test of the sections data model.

Hypothesis generates random sequences of add/remove/rename operations on the
real ProfileStore and, after every step, checks it against a simple reference
model kept in a plain dict. If any operation corrupts the store (loses an entry,
drifts the order, a rename that drops rows), Hypothesis finds a failing sequence
and shrinks it to the shortest one that still breaks. We describe the rules once
and it walks paths we would never hand-script. Pure Python, no wx or browser.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                                "addon", "globalPlugins", "jobFormFiller"))
from core import profile  # noqa: E402

try:
    from hypothesis import settings
    from hypothesis import strategies as st
    from hypothesis.stateful import (RuleBasedStateMachine, rule,
                                     precondition, invariant)
    _HAVE_HYPOTHESIS = True
except ImportError:
    _HAVE_HYPOTHESIS = False


if _HAVE_HYPOTHESIS:
    _names = st.text(alphabet="abcde", min_size=1, max_size=3)
    _rows = st.dictionaries(
        st.sampled_from(["job_title", "employer", "start_date", "end_date"]),
        st.text(alphabet="xyz", max_size=3), max_size=4)

    class SectionsModel(RuleBasedStateMachine):
        def __init__(self):
            super().__init__()
            self.store = profile.ProfileStore(
                os.path.join(tempfile.mkdtemp(), "p.dat"), profile.NullCrypto())
            self.store.load()
            self.store.add_profile("P", {})
            self.store.set_active("P")
            self.model = {}      # section name -> list of row dicts (the truth)

        @rule(name=_names)
        def add_section(self, name):
            if name in self.model:
                return
            self.store.add_section(name)
            self.model[name] = []

        @precondition(lambda self: bool(self.model))
        @rule(data=st.data())
        def add_entry(self, data):
            section = data.draw(st.sampled_from(sorted(self.model)))
            row = data.draw(_rows)
            self.store.add_row(section, row)
            self.model[section].append(dict(row))

        @precondition(lambda self: bool(self.model))
        @rule(data=st.data())
        def remove_section(self, data):
            section = data.draw(st.sampled_from(sorted(self.model)))
            self.store.remove_section(section)
            del self.model[section]

        @precondition(lambda self: any(self.model[s] for s in self.model))
        @rule(data=st.data())
        def remove_entry(self, data):
            section = data.draw(
                st.sampled_from(sorted(s for s in self.model if self.model[s])))
            i = data.draw(st.integers(0, len(self.model[section]) - 1))
            self.store.remove_row(section, i)
            self.model[section].pop(i)

        @precondition(lambda self: bool(self.model))
        @rule(data=st.data(), new=_names)
        def rename_section(self, data, new):
            old = data.draw(st.sampled_from(sorted(self.model)))
            if new in self.model and new != old:
                return
            self.store.rename_section(old, new)
            self.model = {(new if k == old else k): v
                          for k, v in self.model.items()}

        @invariant()
        def store_matches_model(self):
            assert self.store.section_names("P") == list(self.model), (
                "section list drifted",
                self.store.section_names("P"), list(self.model))
            for section, rows in self.model.items():
                assert self.store.section_rows(section, "P") == rows, (
                    "entries drifted in %r" % section,
                    self.store.section_rows(section, "P"), rows)

    SectionsModel.TestCase.settings = settings(
        max_examples=200, stateful_step_count=40)
    TestSectionsModel = SectionsModel.TestCase

else:
    class TestSectionsModel(unittest.TestCase):
        def test_needs_hypothesis(self):
            self.skipTest("hypothesis not installed")


if __name__ == "__main__":
    unittest.main()
