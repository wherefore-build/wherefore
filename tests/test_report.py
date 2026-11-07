"""`wherefore report`: one command for feedback, with a title and a body, and nothing private in it."""
import os
import pathlib
import stat
import subprocess
import sys
import tempfile
import unittest
import urllib.parse

from _util import ENGINE, SRC, repo, scripted

FIXTURE = ENGINE / "tests" / "fixture"

FAKE_GH = ("#!/bin/sh\n"
           "printf '%s\\n' \"$@\" >> '{log}'\n"
           "if [ \"$1\" = auth ]; then exit 0; fi\n"
           "echo https://github.com/wherefore-build/wherefore/issues/999\n")


def run(root, *args, gh=None, root_env=True):
    """The command, with PATH holding only `gh` (a fake) when given, else no gh at all."""
    bindir = pathlib.Path(tempfile.mkdtemp(prefix="wherefore-report-bin-"))
    if gh is not None:
        (bindir / "gh").write_text(gh, encoding="utf-8")
        (bindir / "gh").chmod((bindir / "gh").stat().st_mode | stat.S_IEXEC)
    env = dict(os.environ, PYTHONPATH=str(SRC), PATH=f"{bindir}:{os.path.dirname(sys.executable)}")
    env.pop("WHEREFORE_ROOT", None)
    if root_env:
        env["WHEREFORE_ROOT"] = str(root)
    r = subprocess.run([sys.executable, "-m", "wherefore", "report", *args], cwd=root, env=env,
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def bare():
    """A directory with no wherefore.json in it or above it: outside any git checkout."""
    return pathlib.Path(tempfile.mkdtemp(prefix="wherefore-report-bare-"))


class TheReport(unittest.TestCase):
    def test_it_says_the_title_the_words_the_release_and_the_shape_and_nothing_private(self):
        root = repo({"wherefore.json": {"wherefore": 1, "name": "fern", "generators": [{"script": "g.py", "cwd": ".", "makes": "x"}]},
                     "g.py": "SECRET_TOKEN = 'hunter2'\n", "notes.txt": "the price is 41\n"})
        code, out = run(root, "--title", "Scan two repositories at once", "Point it at a site", "and an app.", "--show")
        self.assertEqual(code, 0, out)
        self.assertIn("# Scan two repositories at once\n\nPoint it at a site and an app.\n", out)
        self.assertIn("**Engine:** wherefore ", out)
        self.assertIn("**The corpus:** fern: 1 generators, 0 sources, 0 authored rules, 0 captured groups", out)
        self.assertNotIn("hunter2", out)
        self.assertNotIn("41", out.split("**The corpus:**")[1].split("\n")[0])
        self.assertIn("--show: nothing was sent", out)

    def test_a_corpus_configured_in_its_own_scripts_is_counted_as_its_gate_counts_it(self):
        inv = {"authored": {"rules": [["checks/*", "the scripts"], ["wherefore.json", "the corpus"],
                                      [".gitignore", "bytecode"]]},
               "captured": {"groups": {"typeface": {"files": ["fonts/*"], "no_stamp": "a font", "why": "third party"}}}}
        root = scripted(inv, gens=("page.py", "sheet.py"))
        code, out = run(root, "--title", "A pendulum-shaped corpus", "Counts.", "--show")
        self.assertEqual(code, 0, out)
        self.assertIn("pendulum-shaped: 2 generators, 0 sources, 3 authored rules, 1 captured groups, "
                      "configured in Python (`entry`)", out)

    def test_words_with_several_points_stay_points_in_the_body_not_the_title(self):
        root = repo({"wherefore.json": {"wherefore": 1, "name": "fern"}})
        words = "Two things.\n\n1. The first.\n2. The second."
        code, out = run(root, "--title", "From a first session", words, "--show")
        self.assertEqual(code, 0, out)
        self.assertIn("# From a first session\n\nTwo things.\n\n1. The first.\n2. The second.\n", out)

    def test_the_output_given_is_in_it_verbatim(self):
        root = repo({"wherefore.json": {"wherefore": 1, "name": "fern"}, "gate.log": "::error::site/a.css is unclassified\n"})
        code, out = run(root, "--title", "The gate refuses a.css", "It is a stylesheet.", "--from", "gate.log", "--show")
        self.assertEqual(code, 0, out)
        self.assertIn("**What it printed:**", out)
        self.assertIn("::error::site/a.css is unclassified", out)

    def test_no_corpus_is_said_and_no_path_is_named(self):
        root = bare()
        code, out = run(root, "--title", "Where do I start?", "Nothing here yet.", "--show", root_env=False)
        self.assertEqual(code, 0, out)
        self.assertIn("**The corpus:** no corpus here\n", out)
        self.assertNotIn(str(root), out)
        self.assertNotIn(root.name, out)

    def test_a_corpus_the_engine_refuses_is_said_without_its_error(self):
        root = repo({"wherefore.json": "{ this is not json"})
        code, out = run(root, "--title", "It will not load", "The file is broken.", "--show")
        self.assertEqual(code, 0, out)
        self.assertIn("**The corpus:** a wherefore.json the engine refuses", out)
        self.assertNotIn(str(root), out)

    def test_without_gh_it_prints_the_link_and_sends_nothing(self):
        root = repo({"wherefore.json": {"wherefore": 1, "name": "fern"}})
        code, out = run(root, "--title", "Can a group name two upstreams?", "Asking for the pendulum.")
        self.assertEqual(code, 0, out)
        self.assertIn("gh is not here, or not signed in, so nothing was sent", out)
        self.assertIn("https://github.com/wherefore-build/wherefore/issues/new?title=Can+a+group", out)
        self.assertNotIn("labels=", out)

    def test_with_gh_signed_in_it_opens_the_issue_with_no_label(self):
        root = repo({"wherefore.json": {"wherefore": 1, "name": "fern"}})
        log = root / "gh.log"
        code, out = run(root, "--title", "The gate is wrong", "It says x.", gh=FAKE_GH.format(log=log))
        self.assertEqual(code, 0, out)
        self.assertIn("opened: https://github.com/wherefore-build/wherefore/issues/999", out)
        said = log.read_text(encoding="utf-8").splitlines()
        self.assertEqual(said[:2], ["auth", "status"])
        self.assertIn("wherefore-build/wherefore", said)
        self.assertEqual(said[said.index("--title") + 1], "The gate is wrong")
        self.assertNotIn("--label", said)

    def test_link_prints_the_link_and_never_sends_even_with_gh_signed_in(self):
        root = repo({"wherefore.json": {"wherefore": 1, "name": "fern"}})
        log = root / "gh.log"
        code, out = run(root, "--title", "A drafted report", "Drafted by the agent.", "--link", gh=FAKE_GH.format(log=log))
        self.assertEqual(code, 0, out)
        self.assertIn("--link: nothing was sent", out)
        url = out.strip().splitlines()[-1]
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        self.assertEqual(q["title"], ["A drafted report"])
        self.assertIn("Drafted by the agent.", q["body"][0])
        self.assertFalse(log.exists() and "issue" in log.read_text(encoding="utf-8"), "gh was asked to send")

    def test_a_report_too_long_for_a_link_says_so_instead_of_a_link_that_opens_nothing(self):
        root = repo({"wherefore.json": {"wherefore": 1, "name": "fern"}, "big.log": "x" * 9000 + "\n"})
        code, out = run(root, "--title", "A long log", "See it.", "--from", "big.log", "--link")
        self.assertEqual(code, 1, out)
        self.assertIn("too long for a link", out)
        self.assertNotIn("issues/new?", out)
        code, out = run(root, "--title", "A long log", "See it.", "--from", "big.log")
        self.assertEqual(code, 1, out)
        self.assertIn("too long for a link", out)
        self.assertNotIn("issues/new?", out)

    def test_the_title_is_one_short_line_and_never_cut(self):
        root = repo({"wherefore.json": {"wherefore": 1, "name": "fern"}})
        code, out = run(root, "--title", "x " * 60, "words", "--show")
        self.assertEqual(code, 2, out)
        self.assertIn("keep it to 100", out)
        code, out = run(root, "--title", "two\nlines", "words", "--show")
        self.assertEqual(code, 0, out)
        self.assertIn("# two lines\n", out)

    def test_a_title_and_words_are_required_in_words(self):
        root = repo({"wherefore.json": {"wherefore": 1, "name": "fern"}})
        code, out = run(root, "just words", "--show")
        self.assertEqual(code, 2)
        self.assertIn("give the report a title", out)
        code, out = run(root, "--title", "only a title", "--show")
        self.assertEqual(code, 2)
        self.assertIn("say it in words after the title", out)
        code, out = run(root, "--title", "t", "w", "--show", "--link")
        self.assertEqual(code, 2)
        self.assertIn("--show or --link, not both", out)

    def test_the_old_kinds_are_gone_and_the_error_says_what_to_type(self):
        root = repo({"wherefore.json": {"wherefore": 1, "name": "fern"}})
        for kind in ("bug", "ask", "feature"):
            code, out = run(root, kind, "the gate is wrong", "--show")
            self.assertEqual(code, 2, out)
            self.assertIn("no longer takes bug, ask or feature", out)
            self.assertIn('wherefore report --title "one line" "the rest"', out)


if __name__ == "__main__":
    unittest.main()
