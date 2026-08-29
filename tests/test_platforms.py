"""Platform detection must recognise the major ATS by URL, and fall back to DOM
markers when the URL isn't available. Pure logic."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                                "addon", "globalPlugins", "jobFormFiller"))
from core import platforms  # noqa: E402


class TestPlatformByUrl(unittest.TestCase):
    CASES = {
        "https://acme.wd1.myworkdayjobs.com/en-US/careers": "workday",
        "https://boards.greenhouse.io/discord/jobs/123": "greenhouse",
        "https://job-boards.greenhouse.io/acme/jobs/1": "greenhouse",
        "https://jobs.lever.co/acme/abc": "lever",
        "https://jobs.ashbyhq.com/acme/xyz": "ashby",
        "https://jobs.smartrecruiters.com/Acme/123": "smartrecruiters",
        "https://careers.icims.com/jobs/1": "icims",
        "https://acme.taleo.net/careersection/1": "taleo",
        "https://performancemanager.successfactors.eu/x": "successfactors",
        "https://acme.bamboohr.com/careers/12": "bamboohr",
        "https://apply.workable.com/acme/j/ABC": "workable",
        "https://example.com/careers": "",
    }

    def test_urls(self):
        for url, expected in self.CASES.items():
            self.assertEqual(platforms.detect(url), expected, url)


class TestPlatformByMarkup(unittest.TestCase):
    def test_dom_markers_when_no_url(self):
        self.assertEqual(platforms.detect("", "select__control", ""), "greenhouse")
        self.assertEqual(platforms.detect("", "", "source--source"), "workday")
        self.assertEqual(platforms.detect("", "sapMInput ui5", ""), "successfactors")
        self.assertEqual(platforms.detect("", "select2-container", ""), "select2")
        self.assertEqual(platforms.detect("", "", "ashby-field-1"), "ashby")

    def test_unknown_is_empty(self):
        self.assertEqual(platforms.detect("", "form-control", "email"), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
