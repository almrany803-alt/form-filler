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
        adds, fills, leftover = rowfill.plan_section_fill(self.rows, self.bf, blocks_present=1)
        self.assertEqual(adds, 2)                       # 3 rows, 1 block -> add 2
        self.assertEqual(len(fills), 3)
        self.assertEqual(fills[0][0], 0)
        # description omitted because the block does not expose it
        self.assertNotIn("description", fills[0][1])
        # empty end_date omitted for the last row
        self.assertNotIn("end_date", fills[2][1])

    def test_enough_blocks_needs_no_adds(self):
        adds, _, _ = rowfill.plan_section_fill(self.rows, self.bf, blocks_present=3)
        self.assertEqual(adds, 0)

    def test_empty_row_is_skipped(self):
        adds, fills, _ = rowfill.plan_section_fill(
            [{"job_title": "X"}, {}], self.bf, blocks_present=1)
        self.assertEqual(len(fills), 1)
        self.assertEqual(adds, 0)

    def test_no_rows(self):
        self.assertEqual(rowfill.plan_section_fill([], self.bf), (0, [], 0))


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestOrderingAndMax(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {"job_title": "Old", "start_date": "2015", "end_date": "2017"},
            {"job_title": "Current", "start_date": "2021", "end_date": ""},
            {"job_title": "Middle", "start_date": "2018", "end_date": "2020"},
        ]

    def test_most_recent_first(self):
        ordered = rowfill.order_recent_first(self.rows)
        self.assertEqual([r["job_title"] for r in ordered],
                         ["Current", "Middle", "Old"])   # ongoing first

    def test_max_blocks_limits_and_reports_leftover(self):
        bf = ["job_title", "start_date", "end_date"]
        adds, fills, leftover = rowfill.plan_section_fill(
            self.rows, bf, blocks_present=1, max_blocks=2)
        self.assertEqual(len(fills), 2)
        self.assertEqual(leftover, 1)
        self.assertEqual(adds, 1)     # 2 to place, 1 present -> add 1


class TestDetectBlocks(unittest.TestCase):
    def test_one_and_many_blocks(self):
        bf = ["job_title", "employer", "start_date", "end_date"]
        self.assertEqual(rowfill.detect_blocks(bf), (bf, 1))
        self.assertEqual(rowfill.detect_blocks(bf * 3), (bf, 3))
        self.assertEqual(rowfill.detect_blocks([]), ([], 0))
