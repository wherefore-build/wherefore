#!/usr/bin/env python3
"""Prove corpus/version_moves.py refuses an engine change under an old version.

On a copy of this repository (corpus/_copy.py), with its current version tagged
as a release:

  fails   src/ changed and committed, the version left as the tag's
  passes  the same change with the version moved past it
          nothing under src/ changed
          no release tagged at all

Usage:  python3 corpus/version_moves_proof.py
"""
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _copy                                                       # noqa: E402

ROOT = _copy.fresh()
from wherefore.prove import check, report                         # noqa: E402

CHECK = "corpus/version_moves.py"


def git(*args):
    subprocess.run(["git", "-c", "user.email=proof@wherefore", "-c", "user.name=proof", *args],
                   cwd=ROOT, check=True, capture_output=True)


def version():
    return re.search(r'^version = "([^"]+)"$', (ROOT / "pyproject.toml").read_text(), re.M).group(1)


def main():
    r = []
    check(r, "no release tagged at all", CHECK, False, ["no release is tagged yet"])
    v = version()
    git("tag", f"v{v}")
    check(r, "nothing under src/ changed", CHECK, False, [f"src/ is as v{v} left it"])

    init = ROOT / "src/wherefore/__init__.py"
    init.write_text(init.read_text() + "\n# an engine change\n")
    git("commit", "-qam", "an engine change")
    check(r, "src/ changed, the version left as the tag's", CHECK, True,
          [f"src/ changed since v{v} and the version did not move past it"])

    major, minor, patch = (int(x) for x in v.split(".")[:3])
    bumped = f"{major}.{minor}.{patch + 1}"
    py = ROOT / "pyproject.toml"
    py.write_text(py.read_text().replace(f'version = "{v}"', f'version = "{bumped}"', 1))
    git("commit", "-qam", "the version moves")
    check(r, "the same change with the version moved past it", CHECK, False,
          [f"src/ changed since v{v}, and the version moved to {bumped}"])
    return report(r)


if __name__ == "__main__":
    sys.exit(main())
