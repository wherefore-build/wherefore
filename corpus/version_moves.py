#!/usr/bin/env python3
"""The engine's version moves whenever its code does.

A client pins the engine by commit, and pip judges an installed package by
name and version - so two commits of src/ under one version are two engines pip
cannot tell apart, and a client that moves its pin installs nothing and says
nothing (#32). The rule that prevents it: if anything under src/ differs from
the newest release tag, pyproject.toml's version must be newer than that tag's.
tests/test_version.py already holds the version the same in pyproject.toml,
wherefore.__version__ and CHANGELOG.md; this holds it moving.

WHAT IT CANNOT SEE: whether the change deserved a patch, a minor or a major
bump. That is the person's call; this only refuses no bump at all.

Usage:  python3 corpus/version_moves.py      (needs the tags: fetch-depth 0)
"""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
VERSION = re.compile(r'^version = "([^"]+)"$', re.M)


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def parsed(v):
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3])


def main():
    tags = [t for t in git("tag", "--list", "v*", "--sort=-v:refname").stdout.split() if t]
    now = VERSION.search((ROOT / "pyproject.toml").read_text(encoding="utf-8")).group(1)
    if not tags:
        print(f"ok   no release is tagged yet, so {now} has nothing to move from")
        return 0
    last = tags[0]
    moved = git("diff", "--quiet", last, "--", "src/").returncode != 0
    if not moved:
        print(f"ok   src/ is as {last} left it; the version need not move")
        return 0
    if parsed(now) <= parsed(last.lstrip("v")):
        print(f"::error::src/ changed since {last} and the version did not move past it "
              f"(pyproject.toml says {now}). Two commits of the engine under one version are "
              f"two engines pip cannot tell apart, and a client moving its pin would keep the "
              f"old one (#32). Move pyproject.toml, wherefore.__version__ and CHANGELOG.md.")
        return 1
    print(f"ok   src/ changed since {last}, and the version moved to {now}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
