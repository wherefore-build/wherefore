"""Every release, said once: src/wherefore/releases.json.

The company's changelog page reads the releases from the release it pins, so
the list must be whole and true. These hold it to CHANGELOG.md (the long
account of each release), to features.json (each feature arrived in a release
that is here), to the version pyproject.toml states (a release cannot be cut
without its entry), and the newest release's picture to what the engine does
now: its command is run again and must print what the picture says.
"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from _util import ENGINE, SRC
import wherefore

DATA = SRC / "wherefore"
ELIDED = "…"


def releases():
    return json.loads((DATA / "releases.json").read_text(encoding="utf-8"))["releases"]


def version(v):
    return tuple(int(x) for x in v.split("."))


class EveryReleaseIsSaid(unittest.TestCase):
    def test_the_changelog_and_the_releases_name_the_same_releases_on_the_same_days(self):
        headings = re.findall(r"^## (\d+\.\d+\.\d+) \((\d{4}-\d\d-\d\d)\)$",
                              (ENGINE / "CHANGELOG.md").read_text(encoding="utf-8"), re.M)
        self.assertEqual([(r["version"], r["date"]) for r in releases()], headings,
                         "releases.json and CHANGELOG.md disagree about which releases were cut, or when")

    def test_the_newest_release_is_this_one(self):
        self.assertEqual(releases()[0]["version"], wherefore.__version__,
                         "the version moved and releases.json has no entry for it")

    def test_newest_first_one_each_with_words_and_a_picture(self):
        vs = [version(r["version"]) for r in releases()]
        self.assertEqual(vs, sorted(set(vs), reverse=True), "newest first, each release once")
        for r in releases():
            for key in ("title", "says"):
                self.assertTrue(r.get(key, "").strip(), f"{r['version']} has no {key}")
            shows = r.get("shows", {})
            self.assertTrue(shows.get("run", "").startswith("wherefore "), f"{r['version']}: run a wherefore command")
            self.assertTrue([l for l in shows.get("output", []) if l.strip() and l != ELIDED],
                            f"{r['version']} shows no output")
            self.assertLessEqual(set(shows) - {"run", "output", "files", "fixture"}, set(),
                                 f"{r['version']}: shows says something the test cannot set up")

    def test_every_feature_arrived_in_a_release_that_is_here(self):
        cut = {r["version"] for r in releases()}
        for f in json.loads((DATA / "features.json").read_text(encoding="utf-8"))["features"]:
            self.assertIn(f["since"], cut, f"{f['id']} says it arrived in {f['since']}, a release never cut")


class TheNewestPictureIsTrue(unittest.TestCase):
    """The picture of this release is run again: a change that moves what the
    command prints fails here until the picture says what it now prints."""

    def test_the_newest_release_prints_what_its_picture_shows(self):
        shows = releases()[0]["shows"]
        base = pathlib.Path(tempfile.mkdtemp(prefix="wherefore-release-"))
        try:
            root = base / "fernhollow"
            if shows.get("fixture"):
                shutil.copytree(ENGINE / "tests/fixture", root)
            else:
                root.mkdir()
            for rel, text in shows.get("files", {}).items():
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_text(text, encoding="utf-8")
            for args in (["init", "-q"], ["add", "-A"],
                         ["-c", "user.email=t@wherefore", "-c", "user.name=t", "commit", "-qm", "x", "--allow-empty"]):
                subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
            env = dict(os.environ, PYTHONPATH=str(SRC))
            env.pop("WHEREFORE_ROOT", None)
            argv = shows["run"].split()[1:]
            r = subprocess.run([sys.executable, "-m", "wherefore", *argv], cwd=root, env=env,
                               capture_output=True, text=True)
            printed = [l.rstrip() for l in (r.stdout + r.stderr).replace(str(root), "~/fernhollow").splitlines()]
        finally:
            shutil.rmtree(base, ignore_errors=True)
        at = 0
        for line in shows["output"]:
            if not line.strip() or line == ELIDED:
                continue
            try:
                at = printed.index(line.rstrip(), at) + 1
            except ValueError:
                self.fail(f"`{shows['run']}` no longer prints, in this order:\n  {line}\n"
                          f"It printed:\n" + "\n".join(printed))


if __name__ == "__main__":
    unittest.main()
