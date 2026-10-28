#!/usr/bin/env python3
"""Make a generator hold its own copy of a fact, and require the probe to say so.

The gate cannot see this one: a generator holding its own copy of a number
reproduces it perfectly, for ever, and every comparison passes. Only moving the
fact and watching nothing follow catches it.

  1. every generator prints its own "$89"            the price is decoration
  2. only the deck does                               the price's named probe names it
  3. the page holds its own copy of the kettle's kind  a dead string fact
  4. the same, exempt with a reason                   reported as exempt, passes
  5. exempt with no reason                            refused
  6. a generator refuses a dearer kettle              backs off, and reaches
  7. --only one fact                                  only that one is moved
  8. --only a pattern that names nothing              refused
  9. a named probe for a fact the source has lost     it probes nothing, and says so
  10. nothing planted                                 and it passes

Usage:  python3 proofs/reach_proof.py
"""
import contextlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _fixture import fresh, git

ROOT = fresh("reach")
from wherefore.prove import Edit, check as _check, report

results = []


def check(name, expect_fail, must_say, *args, forbid=()):
    return _check(results, name, "-m", expect_fail, must_say, "wherefore", "check",
                  "reach", *args, forbid=forbid)


@contextlib.contextmanager
def plant(rel, old, new):
    with Edit(rel) as p:
        s = p.read_text(encoding="utf-8")
        if s.count(old) != 1:
            sys.exit(f"::error::{rel}: the anchor {old!r} is not there once - the case is stale")
        p.write_text(s.replace(old, new), encoding="utf-8")
        yield


@contextlib.contextmanager
def config(edit):
    with Edit("wherefore.json") as p:
        d = json.loads(p.read_text(encoding="utf-8"))
        edit(d["reach"])
        p.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        yield


ONLY = ("--only", "product.price_usd", "product.kind")

with plant("gen/kit.py", '    return f"${x:,}"\n', '    return "$89"\n'):
    check("1. every generator holds its own price -> decoration", True,
          ["product.price_usd moved from 89 to 90 and NOTHING a customer receives changed"],
          *ONLY)

with plant("gen/deck.py", "f\"{dollars(PRODUCT['price_usd'])} · ", 'f"$89 · '):
    check("2. only the deck holds its own price -> its probe names the deck", True,
          ["the price must reach the page, the deck and the notes, and "
           "deck/one-pager.svg did not change"], *ONLY,
          forbid=["site/index.html did not change"])

KIND = "<p>An {PRODUCT['kind']}: "
with plant("gen/landing.py", KIND, "<p>An electric kettle: "):
    check("3. the page holds its own kind of kettle -> a dead string fact", True,
          ["product.kind moved from 'electric kettle' to 'electric kettle (probe)' and NOTHING"],
          *ONLY)
    with config(lambda r: r["exempt"].update({"product.kind": "said aloud by the sales team, never printed"})):
        check("4. the same, exempt with its reason -> passes, saying so", False,
              ["exempt: said aloud by the sales team"], *ONLY)
    with config(lambda r: r["exempt"].update({"product.kind": ""})):
        check("5. exempt with no reason -> refused", True, ["exempt with no reason"], *ONLY)

with plant("gen/kit.py", 'COMPANY = FACTS["company"]\n',
           'COMPANY = FACTS["company"]\nif PRODUCT["price_usd"] > 89.5:\n'
           '    raise SystemExit("nobody buys a kettle at that price")\n'):
    check("6. a generator refuses a dearer kettle -> backs off, and reaches", False,
          ["product.price_usd", "(backed off from 90"], *ONLY)

check("7. --only one fact -> only that one is moved", False,
      ["1 parameters and bands"], "--only", "company.city")

check("8. --only a pattern that names nothing -> refused", True,
      ["--only nothing.here matches no parameter"], "--only", "nothing.here")

with config(lambda r: r["probes"].append({"name": "the colour", "fact": "product.colour",
                                          "reaches": "the deck", "files": ["deck/one-pager.svg"]})):
    check("9. a named probe for a fact the source has lost -> it probes nothing", True,
          ["the colour probes product.colour, which is no longer a number in the spec"], *ONLY)

check("10. nothing planted -> passes", False,
      ["every fact probed reaches something a customer receives"])

left = git(ROOT, "status", "--porcelain").stdout
if left.strip():
    print(f"::error::the proof did not put the fixture back:\n{left}")
    results.append(False)
sys.exit(report(results))
