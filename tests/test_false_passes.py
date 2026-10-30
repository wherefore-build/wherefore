"""The faults a fresh review of 0.2.0 found, each planted, each refused.

A false pass is the worst thing this engine can do: a gate that says every
file holds when one does not is worse than no gate, because it is believed.
Each case here is one the review reproduced on the fixture company, and each
requires the failure - or, for a crash, a message instead of a traceback.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

from _util import ENGINE, SRC, git, repo, wherefore
from wherefore import retired


def fixture():
    """The fixture company, committed, in a directory of its own."""
    root = pathlib.Path(tempfile.mkdtemp(prefix="wherefore-review-")) / "fernhollow"
    shutil.copytree(ENGINE / "tests/fixture", root, ignore=shutil.ignore_patterns("__pycache__"))
    git(root, "init", "-q")
    git(root, "add", "-A")
    commit(root, "base")
    return root


def commit(root, message):
    git(root, "-c", "user.email=t@w", "-c", "user.name=t", "commit", "-qam", message)


def edit_json(path, change):
    doc = json.loads(path.read_text(encoding="utf-8"))
    change(doc)
    path.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")


class SecondPass(unittest.TestCase):
    def test_a_generator_that_throws_on_the_second_pass_fails_the_gate(self):
        root = fixture()
        marker = root.parent / "ran-once"
        notes = root / "gen/notes.py"
        notes.write_text(
            "import pathlib, sys\n"
            f"m = pathlib.Path({str(marker)!r})\n"
            "if m.exists():\n    sys.exit('second pass: choked on what the first wrote')\n"
            "m.write_text('x')\n" + notes.read_text(encoding="utf-8"), encoding="utf-8")
        commit(root, "a generator that only works once")
        code, out = wherefore(root, "gate")
        self.assertEqual(code, 1, out)
        self.assertIn("notes.py failed on the second pass", out)


class MissingFromTheTree(unittest.TestCase):
    def test_a_tracked_generated_file_deleted_locally_is_not_compared_with_nothing(self):
        root = fixture()
        edit_json(root / "facts.json", lambda d: d["company"].update(city="Lisbon"))
        commit(root, "the city moved, and nothing was rebuilt")
        (root / "deck/speaker-notes.txt").unlink()
        code, out = wherefore(root, "gate")
        self.assertEqual(code, 1, out)
        self.assertIn("deck/speaker-notes.txt is tracked and is not in the working tree", out)
        # and the gate puts the tree back as it found it: still deleted
        self.assertFalse((root / "deck/speaker-notes.txt").exists())


class Restamp(unittest.TestCase):
    def test_restamp_needs_one_group(self):
        root = fixture()
        code, out = wherefore(root, "gate", "--restamp")
        self.assertEqual(code, 2, out)
        self.assertIn("--restamp takes exactly one GROUP", out)
        stamp = json.loads((root / "wherefore.json").read_text())["inventory"]["captured"]
        self.assertEqual(stamp["groups"]["the product photograph"]["stamp"], "b7725982e1a370ff")

    def test_a_group_that_says_neither_what_nor_why_is_refused(self):
        root = fixture()
        edit_json(root / "wherefore.json", lambda d: d["inventory"]["captured"]["groups"][
            "the product photograph"].pop("spec_values"))
        commit(root, "a capture made from nothing, and not saying so")
        code, out = wherefore(root, "gate")
        self.assertEqual(code, 1, out)
        self.assertIn("says neither what it was made from", out)
        self.assertNotIn("Traceback", out)

    def test_a_group_with_no_files_is_refused(self):
        root = fixture()
        edit_json(root / "wherefore.json", lambda d: d["inventory"]["captured"]["groups"][
            "the product photograph"].pop("files"))
        commit(root, "a capture of nothing")
        code, out = wherefore(root, "gate")
        self.assertEqual(code, 1, out)
        self.assertIn("needs `files`", out)
        self.assertNotIn("Traceback", out)


class Flags(unittest.TestCase):
    def test_an_unknown_flag_is_refused_not_ignored(self):
        root = fixture()
        code, out = wherefore(root, "gate", "--kep")
        self.assertEqual(code, 2, out)
        self.assertIn("does not take --kep", out)
        self.assertNotIn("tracked files", out)

    def test_help_says_how_and_runs_nothing(self):
        root = fixture()
        code, out = wherefore(root, "gate", "--help")
        self.assertEqual(code, 0, out)
        self.assertIn("wherefore gate --restamp GROUP", out)
        self.assertNotIn("tracked files", out)
        code, out = wherefore(root, "build", "--everything")
        self.assertEqual(code, 2, out)


class Proofs(unittest.TestCase):
    def test_a_glob_that_matches_nothing_proves_nothing(self):
        root = repo({"wherefore.json": {"wherefore": 1, "name": "t",
                                        "proofs": {"glob": "checks/*_prooof.py"}}})
        code, out = wherefore(root, "prove")
        self.assertEqual(code, 1, out)
        self.assertIn("matches no file", out)


class Crashes(unittest.TestCase):
    def test_no_inventory_captured_section_is_not_a_keyerror(self):
        root = fixture()
        edit_json(root / "wherefore.json", lambda d: d["inventory"].pop("captured"))
        commit(root, "no captures declared at all")
        code, out = wherefore(root, "gate")
        self.assertNotIn("Traceback", out)
        self.assertIn("photos/hero.svg is unclassified", out)

    def test_a_generator_cwd_that_does_not_exist_is_said(self):
        root = fixture()
        edit_json(root / "wherefore.json", lambda d: d["generators"][0].update(cwd="gne"))
        commit(root, "a typo in a cwd")
        code, out = wherefore(root, "gate")
        self.assertEqual(code, 1, out)
        self.assertIn("is not a directory", out)
        self.assertNotIn("Traceback", out)

    def test_outside_a_git_repository_says_so(self):
        root = pathlib.Path(tempfile.mkdtemp(prefix="wherefore-nogit-"))
        shutil.copytree(ENGINE / "tests/fixture", root / "f",
                        ignore=shutil.ignore_patterns("__pycache__"))
        env = dict(os.environ, PYTHONPATH=str(SRC), WHEREFORE_ROOT=str(root / "f"),
                   GIT_CEILING_DIRECTORIES=str(root))
        r = subprocess.run([sys.executable, "-m", "wherefore", "gate"], cwd=root / "f",
                           env=env, capture_output=True, text=True)
        out = r.stdout + r.stderr
        self.assertNotEqual(r.returncode, 0, out)
        self.assertIn("is not a git repository", out)
        self.assertNotIn("Traceback", out)


class RetiredNumbers(unittest.TestCase):
    PATTERNS = [r"\$\s*{v}(?!\d|[.,]\d)"]

    def found(self, value, text):
        return retired.hits(value, [text], self.PATTERNS)

    def test_a_large_number_is_searched_for_written_out(self):
        self.assertTrue(self.found(1000000, "now $1000000"))
        self.assertTrue(self.found(1000000, "now $1,000,000"))
        self.assertTrue(self.found(1234567, "was $1,234,567"))

    def test_trailing_zeros_are_the_same_number(self):
        self.assertTrue(self.found(12.5, "$12.50 a month"))
        self.assertTrue(self.found(79, "$79.00"))

    def test_a_different_number_is_not_this_one(self):
        self.assertFalse(self.found(12.5, "$12.55 a month"))
        self.assertFalse(self.found(79, "$79.5"))
        self.assertFalse(self.found(79, "$790"))
        self.assertFalse(self.found(79, "$79,000"))


class NonAsciiPaths(unittest.TestCase):
    def test_a_page_whose_name_is_not_ascii_is_still_read(self):
        # git quotes such a name unless asked not to, and the quoted name
        # matched no file on disk: the page was never read at all.
        root = fixture()
        (root / "site/précis.html").write_text("<p>Still only $79.</p>\n", encoding="utf-8")
        git(root, "add", "-A")
        commit(root, "a page with an accent in its name, claiming the old price")
        code, out = wherefore(root, "check", "retired")
        self.assertEqual(code, 1, out)
        self.assertIn("précis.html", out)


if __name__ == "__main__":
    unittest.main()
