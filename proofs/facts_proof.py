#!/usr/bin/env python3
"""Back the facts with a store, and require the gate to refuse every way the
file it materializes can stop saying what the store says - and to pass the
corpus as it is.

The fixture company, in this proof's copy, keeps its facts in the reference
store (facts.db, SQLite) instead of in facts.json: its wherefore.json says so
beside the source's path, types the facts a customer reads with a schema, and
lists the generator that materializes the store into facts.json first. The
facts are imported, pulled and built, and the copy committed. facts.json is
then a generated file, and every generator reads it as it always did.

  1. the corpus as it is                         passes
  2. facts.json edited by hand                   differs from the store at the
                                                 pinned version: named
  3. a value of the wrong type, in the file      named by its identity
  4. a value of the wrong type, to the store     refused when it is written,
                                                 named by its identity, and
                                                 the store does not move
  5. the schema tightened under the store        what the store holds is
                                                 checked too: named
  6. the store moved, the file not pulled        the generator says the store
                                                 is ahead of the pin, and fails
  7. ... then pulled and built                  passes
  8. a pin the store never reached               not the store it was pulled from

Usage:  python3 proofs/facts_proof.py
"""
import json
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _fixture import fresh, git

ROOT = fresh("facts")
from wherefore.prove import Edit, Tree, check as _check, report

results = []
GATE = ("wherefore", "gate")
PASSES = "every tracked file is classified, and every generated one was"


def wherefore(*args):
    r = subprocess.run([sys.executable, "-m", "wherefore", *args], cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"::error::the proof's own setup failed: wherefore {' '.join(args)}\n{r.stdout}{r.stderr}")
    return r.stdout


def gate(name, expect_fail, must_say):
    return _check(results, name, "-m", expect_fail, must_say, *GATE)


def facts(name, expect_fail, must_say, *args):
    return _check(results, name, "-m", expect_fail, must_say, "wherefore", "facts", *args)


def rewrite(p, old, new):
    s = p.read_text(encoding="utf-8")
    if s.count(old) != 1:
        sys.exit(f"::error::{p.name}: the anchor {old!r} is not there once - the case is stale")
    p.write_text(s.replace(old, new), encoding="utf-8")


def config(change):
    p = ROOT / "wherefore.json"
    cfg = json.loads(p.read_text(encoding="utf-8"))
    change(cfg)
    p.write_text(json.dumps(cfg, indent=1) + "\n", encoding="utf-8")


# ── the copy: its facts in the reference store ──────────────────────────────
def backed(cfg):
    src = cfg["sources"]["facts"]
    src["store"] = {"protocol": "wherefore-store/1", "at": "facts.db"}
    src["schema"] = {"product.price_usd": "number", "product.capacity_l": "number", "product.name": "string",
                     "company.*": "string"}
    cfg["generators"].insert(0, {"script": "-m wherefore.facts", "cwd": ".", "probe": False,
                                 "makes": "facts.json, from the store",
                                 "why": "it writes the source the reach probe moves, and would put the store's value back"})
    for rule in cfg["inventory"]["authored"]["rules"]:
        if rule[0] == "facts.json":
            rule[0], rule[1] = "facts.db", "THE SOURCE: the store; facts.json is made from it"


config(backed)
wherefore("facts", "import", "--decided-by", "fern-founder")
wherefore("facts", "pull")
subprocess.run([sys.executable, "-m", "wherefore", "build"], cwd=ROOT, capture_output=True)
git(ROOT, "add", "-A")
git(ROOT, "-c", "user.email=proof@wherefore", "-c", "user.name=proof", "commit", "-qm", "the facts, in a store")
BASE = git(ROOT, "rev-parse", "HEAD").stdout.strip()

gate("1. the corpus as it is -> passes", False,
     [PASSES, "ok   6 facts in 1 source typed by a schema, 0 faults"])

with Edit("facts.json") as p:
    rewrite(p, '"price_usd": 89', '"price_usd": 95')
    gate("2. facts.json edited by hand -> differs from the store at the pinned version", True,
         ["facts.json regenerated DIFFERENT from what is committed (written by -m wherefore.facts)",
          'committed: "price_usd": 95,'])

with Edit("facts.json") as p:
    rewrite(p, '"price_usd": 89', '"price_usd": "89"')
    gate("3. a value of the wrong type, in the file -> named by its identity", True,
         ['facts:product.price_usd is a string ("89"), and the schema says product.price_usd is number',
          "FAIL 6 facts in 1 source typed by a schema, 1 fault"])

with Edit("facts.db", unchanged_ok=True) as p:
    was = p.read_bytes()
    facts("4. a value of the wrong type, to the store -> refused, named by its identity", True,
          ['refused: facts:product.price_usd is a string ("ninety"), and the schema says product.price_usd is number'],
          "set", "product.price_usd", "ninety", "--as", "string", "--decided-by", "sam")
    if p.read_bytes() != was:
        print("  MISS  4. ... and the store did not move: it did")
        results.append(False)

with Edit("wherefore.json") as p:
    config(lambda cfg: cfg["sources"]["facts"]["schema"].update({"product.name": "number"}))
    gate("5. the schema tightened under what the store holds -> named by its identity", True,
         ['facts:product.name is a string ("Fernhollow One"), and the schema says product.name is number'])

with Tree(), Edit("facts.db") as db, Edit("facts.json") as fj, Edit("wherefore.json") as wj:
    wherefore("facts", "set", "product.price_usd", "95", "--decided-by", "fern-founder")
    gate("6. the store moved, the file not pulled -> the store is ahead of the pin", True,
         ["-m wherefore.facts failed while the gate ran it",
          "facts: the store facts.db is at version 2, and facts.json is pulled at version 1",
          "run `wherefore facts pull`"])
    wherefore("facts", "pull")
    subprocess.run([sys.executable, "-m", "wherefore", "build"], cwd=ROOT, capture_output=True)
    gate("7. ... then pulled and built -> passes, the price moved in the file and the pin", False,
         [PASSES, "ok   5 generated files, 0 differ from what is committed"])
    if '"price_usd": 95' not in fj.read_text(encoding="utf-8") or '"version": 2' not in wj.read_text(encoding="utf-8"):
        print("  MISS  7. ... the pull did not write the price and the pin")
        results.append(False)

with Edit("wherefore.json") as p:
    config(lambda cfg: cfg["sources"]["facts"]["store"].update({"version": 7}))
    gate("8. a pin the store never reached -> not the store the file was pulled from", True,
         ["wherefore.json pins version 7, and the store facts.db holds versions up to 1"])

gate("the corpus, put back -> passes", False, [PASSES])
left = git(ROOT, "status", "--porcelain").stdout
if left.strip() or git(ROOT, "rev-parse", "HEAD").stdout.strip() != BASE:
    print(f"::error::the proof did not put the copy back:\n{left}")
    results.append(False)
sys.exit(report(results))
