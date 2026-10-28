#!/usr/bin/env python3
"""Plant a retired value and a retired phrase every way they come back, and
require `wherefore check retired` to say where - and not to cry wolf.

  1. "$79" in the landing page's prose                 the price, retired
  2. "79" alone in a deck label                         a whole label is a claim
  3. "79 degrees" in the speaker notes                  ANOTHER quantity: not a hit
  4. "Stovetop  Kettle" in the README                   case and spacing are no disguise
  5. "$79" in a CHANGELOG                               the design history: excepted
  6. one excused line, one not, in the same file        excused by the LINE, not the file
  7. the value came back (resumed_at_v)                 not stale any more
  8. the same supersession written twice                a register applied twice
  9. "$79" in a file git does not track                 a copy nobody keeps: not swept
  10. an LFS pointer where a document should be         refused, never read as clean
  11. values retired, and no grammar for a claim        refused
  12. an exemption with no reason                       refused
  13. nothing planted                                   and it passes

Usage:  python3 proofs/retired_proof.py
"""
import contextlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _fixture import fresh, git

ROOT = fresh("retired")
from wherefore.prove import Edit, check as _check, report

results = []


def check(name, expect_fail, must_say, forbid=()):
    return _check(results, name, "-m", expect_fail, must_say, "wherefore", "check",
                  "retired", forbid=forbid)


@contextlib.contextmanager
def json_edit(rel, edit):
    with Edit(rel) as p:
        d = json.loads(p.read_text(encoding="utf-8"))
        edit(d)
        p.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        yield


@contextlib.contextmanager
def plant(rel, old, new):
    with Edit(rel) as p:
        s = p.read_text(encoding="utf-8")
        if s.count(old) != 1:
            sys.exit(f"::error::{rel}: the anchor {old!r} is not there once - the case is stale")
        p.write_text(s.replace(old, new), encoding="utf-8")
        yield


@contextlib.contextmanager
def tracked_file(rel, text):
    p = ROOT / rel
    p.write_text(text, encoding="utf-8")
    git(ROOT, "add", "-N", rel)
    try:
        yield
    finally:
        git(ROOT, "rm", "-f", "--quiet", rel)
        p.unlink(missing_ok=True)


PAGE, PRICE = "site/index.html", "for $89.</p>"

with plant(PAGE, PRICE, "for $89 (was $79).</p>"):
    check("1. $79 in the page's prose -> named", True,
          ["FAIL", "79 -> 89", "site/index.html   says"])

with plant("deck/one-pager.svg", ">Fernhollow Kettles</text>", ">79</text>"):
    check("2. a deck label that says only 79 -> named", True,
          ["deck/one-pager.svg   says '79'"])

with plant("deck/speaker-notes.txt", "Say the size", "It keeps water at 79 degrees. Say the size"):
    check("3. 79 degrees is another quantity -> not a hit", False,
          ["ok       79 -> 89"], forbid=["says"])

with plant("README.md", "A fictional company", "A Stovetop  Kettle company"):
    check("4. the phrase, recased and respaced -> named", True,
          ["'stovetop kettle' -> 'electric kettle'", "README.md   says"])

with tracked_file("CHANGELOG.md", "Until the lid changed it cost $79.\n"):
    check("5. $79 in the design history -> excepted", False,
          ["nothing anywhere still claims"])

with plant(PAGE, PRICE, "for $89.</p>\n<p>The $79 keep-warm base</p>\n<p>was $79</p>"), \
        json_edit("wherefore.json", lambda d: d["retired"]["exemptions"].append(
            {"file": PAGE, "value": 79, "says": "keep-warm",
             "why": "the base's own price, not the kettle's"})):
    check("6. one line excused, the other still named -> by the LINE", True,
          ["is not that number", "says 'was $79'"], forbid=["keep-warm base'"])

with plant(PAGE, PRICE, "for $89 (was $79).</p>"), \
        json_edit("facts.json", lambda d: d["retired"]["values"][0].update(
            resumed_at_v=3, resumed="the base is $79 again, as a different thing")):
    check("7. a value that came back -> not stale", False,
          ["came back at V3", "0 retired values"])

with json_edit("facts.json", lambda d: d["retired"]["phrases"].append(
        dict(d["retired"]["phrases"][0]))):
    check("8. one supersession written twice -> applied twice", True,
          ["lists the phrase 'stovetop kettle' 2 times", "has been applied twice"])

draft = ROOT / "site/draft.html"
draft.write_text("<p>$79</p>\n", encoding="utf-8")
try:
    check("9. $79 in a file git does not track -> not swept", False,
          ["nothing anywhere still claims"])
finally:
    draft.unlink()

with Edit(PAGE) as p:
    p.write_text("version https://git-lfs.github.com/spec/v1\noid sha256:00\nsize 1\n",
                 encoding="utf-8")
    check("10. an LFS pointer where a page should be -> refused", True,
          ["this is a git-lfs POINTER, not the file"])

with json_edit("wherefore.json", lambda d: d["retired"].update(assertion_patterns=[])):
    check("11. values retired, no grammar for a claim -> refused", True,
          ["declares no assertion_patterns"])

with json_edit("wherefore.json", lambda d: d["retired"]["exemptions"].append(
        {"file": PAGE, "value": 79, "says": "x", "why": " "})):
    check("12. an exemption with no reason -> refused", True, ["carries no reason"])

check("13. nothing planted -> passes", False,
      ["nothing anywhere still claims a retired value or a retired phrase"])

left = git(ROOT, "status", "--porcelain").stdout
if left.strip():
    print(f"::error::the proof did not put the fixture back:\n{left}")
    results.append(False)
sys.exit(report(results))
