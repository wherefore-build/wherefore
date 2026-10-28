#!/usr/bin/env python3
"""Make the copy say what the facts do not, and require `wherefore check claims`
to name the sentence and the word - and not to fire on a sentence that states
the rule.

  1. "Made in Portugal" on the page                  never: the element is bought in
  2. "Assembled, tested, and boxed in Portugal"      boxed: nothing justifies it
  3. 'It is never "made in Portugal"'                states the rule: not a claim
  4. "Made in Portugal - not negotiable."            a negation elsewhere excuses nothing
  5. "MADE   IN  portugal" in the deck               case, spacing and a drawing's label
  6. the same in the design history                  excepted
  7. a may_say with no reason                        refused
  8. nothing planted                                 and it passes

Usage:  python3 proofs/claims_proof.py
"""
import contextlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _fixture import fresh, git

ROOT = fresh("claims")
from wherefore.prove import Edit, check as _check, report

results = []


def check(name, expect_fail, must_say, forbid=()):
    return _check(results, name, "-m", expect_fail, must_say, "wherefore", "check",
                  "claims", forbid=forbid)


@contextlib.contextmanager
def plant(rel, old, new):
    with Edit(rel) as p:
        s = p.read_text(encoding="utf-8")
        if s.count(old) != 1:
            sys.exit(f"::error::{rel}: the anchor {old!r} is not there once - the case is stale")
        p.write_text(s.replace(old, new), encoding="utf-8")
        yield


PAGE, LINE = "site/index.html", "<p>Assembled and tested in Portugal."

with plant(PAGE, LINE, "<p>Made in Portugal."):
    check("1. made in Portugal -> never, and why", True,
          ["site/index.html says 'Made in Portugal.", "made: the heating element is bought in"])

with plant(PAGE, LINE, "<p>Assembled, tested, and boxed in Portugal."):
    check("2. boxed in Portugal -> nothing justifies it", True,
          ["boxed: nothing in may_say justifies 'boxed' in Portugal"],
          forbid=["tested: nothing"])

with plant(PAGE, LINE, '<p>It is never "made in Portugal". Assembled and tested in Portugal.'):
    check("3. a sentence that states the rule -> not a claim", False,
          ["every claim says only what its rule allows"])

with plant(PAGE, LINE, "<p>Made in Portugal - not negotiable. Assembled and tested in Portugal."):
    check("4. a negation that does not govern the claim -> still a claim", True,
          ["made: the heating element is bought in"])

with plant("deck/one-pager.svg", ">Fernhollow Kettles</text>", ">MADE   IN  portugal</text>"):
    check("5. recased and respaced, in a drawing's label -> named", True,
          ["deck/one-pager.svg says 'MADE   IN  portugal'"])

p = ROOT / "CHANGELOG.md"
p.write_text("The first batch was made in Portugal, element and all.\n", encoding="utf-8")
git(ROOT, "add", "-N", "CHANGELOG.md")
try:
    check("6. the design history -> excepted", False, ["every claim says only what"])
finally:
    git(ROOT, "rm", "-f", "--quiet", "CHANGELOG.md")
    p.unlink(missing_ok=True)

with Edit("wherefore.json") as q:
    d = json.loads(q.read_text(encoding="utf-8"))
    d["claims"][0]["may_say"]["designed"] = ""
    q.write_text(json.dumps(d, indent=1) + "\n", encoding="utf-8")
    check("7. may_say with no reason -> refused", True, ["may_say 'designed' carries no reason"])

check("8. nothing planted -> passes", False, ["every claim says only what its rule allows"])

left = git(ROOT, "status", "--porcelain").stdout
if left.strip():
    print(f"::error::the proof did not put the fixture back:\n{left}")
    results.append(False)
sys.exit(report(results))
