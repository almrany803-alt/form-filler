import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                                "addon", "globalPlugins", "jobFormFiller"))
from core import rowfill  # noqa: E402


class TestRowConcept(unittest.TestCase):
    def test_maps_block_labels_to_row_fields(self):
        cases = {
            "Job Title": "job_title", "Position": "job_title", "Title": "job_title",
            "Company": "employer", "Employer Name": "employer",
            "University": "institution", "School": "institution",
            "Degree": "qualification", "Field of Study": "field_of_study",
            "Major": "field_of_study", "Start Date": "start_date", "From": "start_date",
            "End Date": "end_date", "To": "end_date",
            "Description": "description", "Responsibilities": "description",
            "Grade": "grade",
        }
        for label, want in cases.items():
            self.assertEqual(rowfill.row_concept(label), want, label)

    def test_longest_wins_and_unknown_is_none(self):
        self.assertEqual(rowfill.row_concept("Job Title"), "job_title")  # not "title"
        self.assertEqual(rowfill.row_concept("Start Date"), "start_date")  # not "start"
        self.assertIsNone(rowfill.row_concept("Favourite Colour"))


class TestPlanSectionFill(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {"job_title": "Engineer", "employer": "Acme",
             "start_date": "2020", "end_date": "2022", "description": "built"},
            {"job_title": "Teacher", "employer": "Riyadh School",
             "start_date": "2018", "end_date": "2020"},
            {"job_title": "Volunteer", "employer": "Look UK",
             "start_date": "2017", "end_date": ""},
        ]
        self.bf = ["job_title", "employer", "start_date", "end_date"]

    def test_adds_and_fills(self):
        adds, fills = rowfill.plan_section_fill(self.rows, self.bf, blocks_present=1)
        self.assertEqual(adds, 2)                       # 3 rows, 1 block -> add 2
        self.assertEqual(len(fills), 3)
        self.assertEqual(fills[0][0], 0)
        # description omitted because the block does not expose it
        self.assertNotIn("description", fills[0][1])
        # empty end_date omitted for the last row
        self.assertNotIn("end_date", fills[2][1])

    def test_enough_blocks_needs_no_adds(self):
        adds, _ = rowfill.plan_section_fill(self.rows, self.bf, blocks_present=3)
        self.assertEqual(adds, 0)

    def test_empty_row_is_skipped(self):
        adds, fills = rowfill.plan_section_fill(
            [{"job_title": "X"}, {}], self.bf, blocks_present=1)
        self.assertEqual(len(fills), 1)
        self.assertEqual(adds, 0)

    def test_no_rows(self):
        self.assertEqual(rowfill.plan_section_fill([], self.bf), (0, []))


if __name__ == "__main__":
    unittest.main(verbosity=2)
