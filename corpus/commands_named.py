#!/usr/bin/env python3
"""Every `wherefore` command a person is told to type is one the CLI has.

The README's list of commands is generated (corpus/readme.py), so it cannot
name a command that does not exist. The rest of what a user reads cannot be
generated without losing its point - the skill's "find your bearings" names
three commands on purpose, in the order an agent should run them - so it is
held instead: every `wherefore <command>` in its code, inline or fenced, must
be one src/wherefore/commands.json lists, subcommand and all. A command renamed
in the CLI and not in the skill fails here, naming the file and the line.

WHAT IT READS: the documents a person reads to USE Wherefore - the README, the
changelog, the skill (both its files: working in a corpus, and starting one)
and docs/.

WHAT IT CANNOT SEE: a command named in prose outside a code span, and a flag
that does not exist - `wherefore gate --kepe` names the command `gate`, which
does.

Usage:  python3 corpus/commands_named.py
"""
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
COMMANDS = ROOT / "src/wherefore/commands.json"
READ = ("README.md", "CHANGELOG.md", "src/wherefore/skills/*/*.md", "src/wherefore/docs/*.md", "docs/*.md")

FENCED = re.compile(r"```.*?```", re.S)
INLINE = re.compile(r"`[^`\n]+`")
NAMED = re.compile(r"(?<![\w.\-/])(?<!from )(?<!import )wherefore\s+([a-z][\w-]*)(?:\s+([a-z][\w-]*))?")


def known():
    rows = [c["usage"].split() for c in json.loads(COMMANDS.read_text(encoding="utf-8"))["commands"]]
    tops = {r[1] for r in rows}
    subs = {}
    for r in rows:
        if len(r) > 2 and not r[2].startswith(("-", "[")) and not r[2].isupper():
            subs.setdefault(r[1], set()).add(r[2])
    return tops, subs


def files():
    out = subprocess.run(["git", "ls-files", *READ], cwd=ROOT, capture_output=True,
                         text=True, check=True).stdout.split()
    return sorted(set(out))


def faults():
    tops, subs = known()
    found = []
    for rel in files():
        text = (ROOT / rel).read_text(encoding="utf-8")
        spans = [(m.start(), m.group(0)) for m in FENCED.finditer(text)]
        rest = FENCED.sub(lambda m: " " * len(m.group(0)), text)
        spans += [(m.start(), m.group(0)) for m in INLINE.finditer(rest)]
        for at, span in spans:
            for m in NAMED.finditer(span):
                top, sub = m.group(1), m.group(2)
                line = text.count("\n", 0, at + m.start()) + 1
                if top not in tops:
                    found.append(f"{rel}:{line}: `wherefore {top}` - there is no such command")
                elif top in subs and sub not in subs[top]:
                    said = f"wherefore {top} {sub or ''}".strip()
                    found.append(f"{rel}:{line}: `{said}` - "
                                 f"{top} takes {', '.join(sorted(subs[top]))}")
    return found


def main():
    found = faults()
    if found:
        print("::error::a document tells a person to type a command the CLI does not have:\n")
        for f in found:
            print(f"   {f}")
        print("\nRename it where it is written, or add the command to src/wherefore/commands.json "
              "with the code that runs it.")
        return 1
    print(f"ok   every command named in {len(files())} documents is one the CLI has")
    return 0


if __name__ == "__main__":
    sys.exit(main())
