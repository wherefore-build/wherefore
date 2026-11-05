"""`wherefore report`: a bug, a question or a feature request, with nothing private in it."""
import os
import pathlib
import stat
import subprocess
import sys
import tempfile
import unittest

from _util import ENGINE, SRC, repo

FIXTURE = ENGINE / "tests" / "fixture"


def run(root, *args, path_extra=None, gh=None):
    """The command, with PATH holding only `gh` (a fake) when given, else no gh at all."""
    bindir = pathlib.Path(tempfile.mkdtemp(prefix="wherefore-report-bin-"))
    if gh is not None:
        (bindir / "gh").write_text(gh, encoding="utf-8")
        (bindir / "gh").chmod((bindir / "gh").stat().st_mode | stat.S_IEXEC)
    env = dict(os.environ, PYTHONPATH=str(SRC), WHEREFORE_ROOT=str(root), PATH=f"{bindir}:{os.path.dirname(sys.executable)}")
    r = subprocess.run([sys.executable, "-m", "wherefore", "report", *args], cwd=root, env=env,
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


class TheReport(unittest.TestCase):
    def test_it_says_the_release_the_shape_and_the_words_and_nothing_private(self):
        root = repo({"wherefore.json": {"wherefore": 1, "name": "fern", "generators": [{"script": "g.py", "cwd": ".", "makes": "x"}]},
                     "g.py": "SECRET_TOKEN = 'hunter2'\n", "notes.txt": "the price is 41\n"})
        code, out = run(root, "feature", "scan", "two", "repositories", "--show")
        self.assertEqual(code, 0, out)
        self.assertIn("# feature request: scan two repositories", out)
        self.assertIn("**Engine:** wherefore ", out)
        self.assertIn("**The corpus:** fern: 1 generators, 0 sources, 0 authored rules, 0 captured groups", out)
        self.assertNotIn("hunter2", out)
        self.assertNotIn("41", out.split("**The corpus:**")[1].split("\n")[0])
        self.assertIn("--show: nothing was sent", out)

    def test_the_output_given_is_in_it_verbatim(self):
        root = repo({"wherefore.json": {"wherefore": 1, "name": "fern"}, "gate.log": "::error::site/a.css is unclassified\n"})
        code, out = run(root, "bug", "the gate refuses a.css", "--from", "gate.log", "--show")
        self.assertEqual(code, 0, out)
        self.assertIn("**What it printed:**", out)
        self.assertIn("::error::site/a.css is unclassified", out)

    def test_no_corpus_is_said_not_hidden(self):
        root = repo({"README.md": "nothing yet\n"})
        code, out = run(root, "ask", "where do I start?", "--show")
        self.assertEqual(code, 0, out)
        self.assertIn("**The corpus:** no corpus here", out)

    def test_without_gh_it_prints_the_link_and_sends_nothing(self):
        root = repo({"wherefore.json": {"wherefore": 1, "name": "fern"}})
        code, out = run(root, "ask", "can a group name two upstreams?")
        self.assertEqual(code, 0, out)
        self.assertIn("gh is not here, or not signed in, so nothing was sent", out)
        self.assertIn("https://github.com/wherefore-build/wherefore/issues/new?title=question%3A+can+a+group", out)
        self.assertIn("labels=question", out)

    def test_with_gh_signed_in_it_opens_the_issue_with_the_kind_as_its_label(self):
        root = repo({"wherefore.json": {"wherefore": 1, "name": "fern"}})
        log = root / "gh.log"
        fake = ("#!/bin/sh\n"
                f"printf '%s\\n' \"$@\" >> '{log}'\n"
                "if [ \"$1\" = auth ]; then exit 0; fi\n"
                "echo https://github.com/wherefore-build/wherefore/issues/999\n")
        code, out = run(root, "bug", "the gate is wrong", gh=fake)
        self.assertEqual(code, 0, out)
        self.assertIn("opened: https://github.com/wherefore-build/wherefore/issues/999", out)
        said = log.read_text(encoding="utf-8").splitlines()
        self.assertEqual(said[:2], ["auth", "status"])
        self.assertIn("--repo", said)
        self.assertIn("wherefore-build/wherefore", said)
        self.assertIn("bug", said[said.index("--label") + 1])
        self.assertIn("bug: the gate is wrong", said[said.index("--title") + 1])

    def test_the_kind_and_the_words_are_required_in_words(self):
        root = repo({"wherefore.json": {"wherefore": 1, "name": "fern"}})
        code, out = run(root, "--show")
        self.assertEqual(code, 2)
        self.assertIn("say what kind of report: bug, ask or feature", out)
        code, out = run(root, "bug")
        self.assertEqual(code, 2)
        self.assertIn("the person's words, not an agent's", out)
        code, out = run(root, "rant", "x")
        self.assertEqual(code, 2)
        self.assertIn("takes bug, ask or feature first", out)


if __name__ == "__main__":
    unittest.main()
