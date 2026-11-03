#!/usr/bin/env python3
"""Prove the gate fails this repository's own corpus when it should.

The gate that judges this repository is the previous release's (CI installs it
from requirements-engine.txt), and this proves it is not just running but
catching: each case breaks a copy of the repository (corpus/_copy.py) the way
this corpus could plausibly go wrong, and requires the gate to fail in the
words of the case.

  fails   the README edited by hand, instead of its template
          a command added to the source, the README not regenerated
          a new file committed that nothing classifies
  passes  the repository as it is

Usage:  python3 corpus/gate_proof.py
"""
import json
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _copy                                                       # noqa: E402

ROOT = _copy.fresh()
from wherefore.prove import Edit, check, report                   # noqa: E402

PASS = "every tracked file is classified"
DIFFERENT = "README.md regenerated DIFFERENT from what is committed"


def gate(r, name, fails, words):
    return check(r, name, "-m", fails, words, "wherefore", "gate")


def main():
    r = []
    with Edit("README.md") as p:
        p.write_text(p.read_text(encoding="utf-8").replace(
            "**Your company, compiled.**",
            "**Your company, shipped.**", 1), encoding="utf-8")
        gate(r, "the README edited by hand, instead of its template", True, [DIFFERENT])

    with Edit("src/wherefore/commands.json") as p:
        doc = json.loads(p.read_text(encoding="utf-8"))
        doc["commands"].insert(0, {"usage": "wherefore describe", "does": "print the engine's facts"})
        p.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        gate(r, "a command added to the source, the README not regenerated", True, [DIFFERENT])

    notes = ROOT / "notes.txt"
    notes.write_text("a file nobody declared\n", encoding="utf-8")
    subprocess.run(["git", "add", "notes.txt"], cwd=ROOT, check=True)
    try:
        gate(r, "a new file committed that nothing classifies", True,
             ["notes.txt is unclassified"])
    finally:
        subprocess.run(["git", "rm", "-q", "--cached", "notes.txt"], cwd=ROOT, check=True)
        notes.unlink()

    gate(r, "the repository as it is", False, [PASS])
    return report(r)


if __name__ == "__main__":
    sys.exit(main())
