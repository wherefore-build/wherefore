"""Drift: src/wherefore/drift.py, `wherefore check drift`, and the map that draws it.

A value said by hand in two or more files that no source holds is drift.
What can go wrong: a value a source holds counted as drift; a value in a
generated file or in code counted, which is not by hand; a value said once
counted; the allowance letting more through than it says, or not asking to
come down; an ignored file read; the map not drawing what the check names.
"""
import json
import os
import subprocess
import sys
import unittest

from _util import ENGINE, SRC, repo, wherefore
from wherefore import config as cfgmod, drift

BASE = {"wherefore": 1, "name": "t",
        "sources": {"facts": {"path": "facts.json", "why": "the source"}},
        "generators": [],
        "inventory": {"authored": {"rules": [["*.md", "prose"], ["facts.json", "the source"],
                                             ["wherefore.json", "this"], ["*.py", "code"]]},
                      "captured": {"groups": {"sketch": {"files": ["sketch.svg"], "why": "drawn",
                                                         "no_stamp": "drawn by hand"}}}}}
FACTS = {"price_usd": 89, "trial_days": 14, "tagline": "Ships in 5 working days"}


def corpus(files, extra=None):
    doc = json.loads(json.dumps(BASE))
    doc.update(extra or {})
    all_files = {"wherefore.json": doc, "facts.json": FACTS, ".gitignore": "__pycache__/\n"}
    all_files.update(files)
    return repo(all_files)


class WhatDrifts(unittest.TestCase):
    def test_a_value_said_by_hand_in_two_files_that_no_source_holds(self):
        root = corpus({"README.md": "Our kettle boils in 3 minutes.\n", "docs/faq.md": "It boils in 3 minutes flat.\n"})
        found = drift.find(cfgmod.load(root))
        self.assertEqual([(v["value"], v["files"]) for v in found["values"]], [("3", ["README.md", "docs/faq.md"])])
        self.assertEqual(found["values"][0]["says"], "boils in {} minutes")

    def test_a_value_a_source_holds_is_not_drift_even_as_money_or_in_a_sentence(self):
        root = corpus({"README.md": "The kettle costs $89 today, with a 14 day trial.\n",
                       "docs/pricing.md": "Price: 89 dollars; the trial runs 14 days. Ships in 5 working days.\n",
                       "docs/faq.md": "Ships in 5 working days, always.\n"})
        found = drift.find(cfgmod.load(root))
        self.assertEqual(found["values"], [], "89, 14 and 5 are all held by facts.json")
        self.assertGreaterEqual(found["held"], 1, "5 working days, said in two files, is held")

    def test_a_value_said_once_and_a_value_in_code_or_a_generated_file_are_not_drift(self):
        root = corpus({"README.md": "Boils in 3 minutes.\n", "gen/make.py": 'X = "Boils in 3 minutes"\n',
                       "site/index.html": "<p>Boils in 3 minutes</p>\n"},
                      {"generators": [{"script": "make.py", "cwd": "gen", "makes": "site/index.html"}]})
        (root / "gen/make.py").write_text('import pathlib\npathlib.Path("../site/index.html").write_text("<p>Boils in 3 minutes</p>\\n")\n',
                                          encoding="utf-8")
        found = drift.find(cfgmod.load(root))
        self.assertEqual(found["values"], [], "README says it once; the script is code; the page is generated")

    def test_a_captured_drawing_counts_and_an_ignored_file_does_not(self):
        root = corpus({"README.md": "Boils in 3 minutes.\n",
                       "sketch.svg": '<svg xmlns="http://www.w3.org/2000/svg"><text>Boils in 3 minutes</text></svg>\n',
                       "vendor/NOTICE.md": "Boils in 3 minutes, says a third party.\n"},
                      {"inventory": dict(BASE["inventory"], authored={"rules": BASE["inventory"]["authored"]["rules"] + [["vendor/**", "theirs"]]})})
        found = drift.find(cfgmod.load(root))
        self.assertEqual(found["values"][0]["files"], ["README.md", "sketch.svg", "vendor/NOTICE.md"])
        (root / "wherefore.json").write_text(json.dumps(dict(json.loads((root / "wherefore.json").read_text()),
                                                             drift={"allow": 1, "why": "the boil time, tracked next",
                                                                    "ignore": {"vendor/**": "third-party text"}})), encoding="utf-8")
        found = drift.find(cfgmod.load(root))
        self.assertEqual(found["values"][0]["files"], ["README.md", "sketch.svg"])


class TheCheck(unittest.TestCase):
    def test_without_a_section_it_reports_and_passes_and_says_what_to_declare(self):
        root = corpus({"README.md": "Boils in 3 minutes.\n", "docs/faq.md": "Boils in 3 minutes.\n"})
        code, out = wherefore(root, "check", "drift")
        self.assertEqual(code, 0, out)
        self.assertIn('  3            "boils in {} minutes"  in 2 files, 2x: README.md, docs/faq.md', out)
        self.assertIn('1 value drifts: said by hand in two or more of 2 files, held by no source; 0 held', out)
        self.assertIn('"drift": {"allow": 1, "why": ...}', out)

    def test_nothing_drifting_is_said_in_one_line(self):
        root = corpus({"README.md": "Costs $89.\n", "docs/faq.md": "Costs 89 dollars.\n"})
        code, out = wherefore(root, "check", "drift")
        self.assertEqual(code, 0, out)
        self.assertIn("ok   nothing drifts: every value said by hand in two or more of 2 files is held by a source", out)

    def test_the_allowance_fails_more_and_asks_to_come_down_on_fewer(self):
        files = {"README.md": "Boils in 3 minutes; holds 1.5 litres.\n", "docs/faq.md": "Boils in 3 minutes; holds 1.5 litres.\n"}
        root = corpus(files, {"drift": {"allow": 1, "why": "the boil time, tracked next"}})
        code, out = wherefore(root, "check", "drift")
        self.assertEqual(code, 1, out)
        self.assertIn("::error::2 values drift", out)
        self.assertIn("wherefore.json allows 1", out)
        root = corpus(files, {"drift": {"allow": 2, "why": "both, tracked next"}})
        code, out = wherefore(root, "check", "drift")
        self.assertEqual(code, 0, out)
        self.assertIn("the 2 allowed", out)
        root = corpus(files, {"drift": {"allow": 5, "why": "a budget nobody tightened"}})
        code, out = wherefore(root, "check", "drift")
        self.assertEqual(code, 0, out)
        self.assertIn("under the 5 allowed: lower drift.allow to 2", out)

    def test_the_section_is_checked(self):
        for bad, said in (({"drift": {"allow": "two", "why": "x"}}, "whole number"),
                          ({"drift": {"allow": 2}}, "drift.why"),
                          ({"drift": {"allow": 2, "why": "x", "ignore": ["vendor/**"]}}, "drift.ignore"),
                          ({"drift": {"allow": 2, "why": "x", "max": 1}}, "does not take")):
            root = corpus({"README.md": "x\n"}, bad)
            code, out = wherefore(root, "check", "drift")
            self.assertNotEqual(code, 0, bad)
            self.assertIn(said, out, bad)


class OnTheMap(unittest.TestCase):
    def test_the_map_draws_what_the_check_names_and_counts_it(self):
        root = corpus({"README.md": "Boils in 3 minutes.\n", "docs/faq.md": "Boils in 3 minutes.\n"},
                      {"drift": {"allow": 1, "why": "the boil time, tracked next"}})
        code, out = wherefore(root, "graph", "--json", "map.json", "--html", "map.html")
        self.assertEqual(code, 0, out)
        self.assertIn("1 value drifts", out)
        m = json.loads((root / "map.json").read_text(encoding="utf-8"))
        self.assertEqual(m["counts"]["drifting"], 1)
        self.assertEqual(m["drift"]["allow"], 1)
        self.assertEqual(m["drift"]["values"][0]["files"], ["README.md", "docs/faq.md"])
        page = (root / "map.html").read_text(encoding="utf-8")
        self.assertIn('id="drift"', page)
        self.assertIn("seen shrinking", page)


if __name__ == "__main__":
    unittest.main()
