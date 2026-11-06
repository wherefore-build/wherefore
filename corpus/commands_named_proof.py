#!/usr/bin/env python3
"""Prove corpus/commands_named.py fails on a document naming a command that does not exist.

Each case breaks a copy of this repository (corpus/_copy.py) and requires the
check to fail in the words of the case, or - for the cases that must not
fire - to pass.

  fails   a command that does not exist, in the skill
          a check `wherefore check` does not have, in the README's template
  passes  `from wherefore import prove`, which names a module, not a command
          a proposed command in CONTRIBUTING.md, a document it does not read
          the documents as they are

Usage:  python3 corpus/commands_named_proof.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _copy                                                       # noqa: E402

_copy.fresh()
from wherefore.prove import Edit, check, report                   # noqa: E402

CHECK = "corpus/commands_named.py"
PASS = "every command named in"


def planted(p, line):
    p.write_text(p.read_text(encoding="utf-8") + f"\n{line}\n", encoding="utf-8")


def main():
    r = []
    with Edit("src/wherefore/skills/wherefore/SKILL.md") as p:
        planted(p, "Then run `wherefore frobnicate` to finish.")
        check(r, "a command that does not exist, in the skill", CHECK, True,
              ["src/wherefore/skills/wherefore/SKILL.md:", "`wherefore frobnicate` - there is no such command"])
    with Edit("docs/README.template.md") as p:
        planted(p, "```\nwherefore check spelling\n```")
        check(r, "a check that does not exist, in the README's template", CHECK, True,
              ["docs/README.template.md:", "`wherefore check spelling` - check takes claims, drift, palette, published, reach, retired, upstream"])
    with Edit("src/wherefore/skills/wherefore/SKILL.md") as p:
        planted(p, "`from wherefore import prove` gives a proof its harness.")
        check(r, "a module named, not a command - must not fire", CHECK, False, [PASS])
    with Edit("CONTRIBUTING.md") as p:
        planted(p, "A later `wherefore describe` would print the engine's facts.")
        check(r, "a proposed command in a document it does not read - must not fire", CHECK, False, [PASS])
    check(r, "the documents as they are", CHECK, False, [PASS])
    return report(r)


if __name__ == "__main__":
    sys.exit(main())
