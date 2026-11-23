#!/usr/bin/env python3
"""Break what `wherefore gate --since` exists to catch, and show where it stops.

--since runs only the generators a change can reach, by the read map the full
gate keeps (since.py). A check is not trusted until it has been shown to fail,
so each case below plants a fault a change could carry and requires --since to
fail on it, as the full gate does. And because it trusts a record of what each
generator read, one case plants the read that record cannot hold, and shows
--since passing it and the full gate catching it: the limit, shown and not
assumed, which is why the full gate stays the backstop on main.

The fixture company gains, in this proof's copy, its own map (`wherefore graph
--json`) and one generator, gen/origin.py, that reads origin.txt through a
shell - a read Python's open() never sees, so the map does not record it.

  1.  a fact moved, nothing rebuilt             the pages that read it differ
  2.  a generator's script changed              its file differs
  3.  a generated file edited by hand           its generator runs: it differs
  4.  the map edited by hand                    the composed map differs
  5.  a generated file deleted                  named as missing
  6.  a map from another release                every generator runs, said, and
                                                the stale map fails it
  7.  nothing broken                            every generator skipped, and it passes
  8.  a read through a shell                    THE LIMIT: --since passes it,
                                                and the full gate does not

Usage:  python3 proofs/since_proof.py
"""
import json
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _fixture import fresh, git

ROOT = fresh("since")
from wherefore.prove import Edit, check as _check, report

results = []
SINCE = ("wherefore", "gate", "--since", "HEAD")
FULL = ("wherefore", "gate")
MAP = [sys.executable, "-m", "wherefore", "graph", "--html", "map/index.html", "--json", "map/map.json"]
ORIGIN = ('"""site/origin.txt: where the kettle is put together - read through a shell."""\n'
          "import subprocess\nfrom kit import ROOT\n"
          'said = subprocess.run(["cat", str(ROOT / "origin.txt")], capture_output=True, text=True, check=True).stdout\n'
          '(ROOT / "site/origin.txt").write_text(said, encoding="utf-8")\n')


def since(name, expect_fail, must_say, forbid=()):
    return _check(results, name, "-m", expect_fail, must_say, *SINCE, forbid=forbid)


def full(name, expect_fail, must_say):
    return _check(results, name, "-m", expect_fail, must_say, *FULL)


def commit(msg):
    git(ROOT, "add", "-A")
    git(ROOT, "-c", "user.email=proof@wherefore", "-c", "user.name=proof", "commit", "-qm", msg)


# ── the copy: a map, and a generator whose read the map cannot see ──────────
(ROOT / "origin.txt").write_text("Assembled in Porto.\n", encoding="utf-8")
(ROOT / "gen/origin.py").write_text(ORIGIN, encoding="utf-8")
cfg = json.loads((ROOT / "wherefore.json").read_text(encoding="utf-8"))
cfg["generators"].append({"script": "origin.py", "cwd": "gen", "makes": "site/origin.txt"})
cfg["generators"].append({"run": MAP, "cwd": ".", "makes": "map/, the map, which --since reads"})
cfg["inventory"]["authored"]["rules"].append(["origin.txt", "where it is put together: a source"])
(ROOT / "wherefore.json").write_text(json.dumps(cfg, indent=1) + "\n", encoding="utf-8")
for _ in range(2):
    subprocess.run([sys.executable, "-m", "wherefore", "build"], cwd=ROOT, capture_output=True)
    git(ROOT, "add", "-A")
commit("the map, and a generator that reads through a shell")

# 1. A FACT MOVED AND NOTHING REBUILT: the generators that read it run, and differ.
with Edit("facts.json") as p:
    p.write_text(p.read_text(encoding="utf-8").replace('"price_usd": 89', '"price_usd": 99'),
                 encoding="utf-8")
    since("a fact moved, nothing rebuilt -> the pages that read it differ",
          True, ["ran      landing.py - it reads facts.json, changed since HEAD",
                 "site/index.html regenerated DIFFERENT"])

# 2. A GENERATOR'S SCRIPT CHANGED: it runs.
with Edit("gen/notes.py") as p:
    p.write_text(p.read_text(encoding="utf-8").replace("Say the size", "Give the size"),
                 encoding="utf-8")
    since("a generator's script changed -> it runs, and its file differs",
          True, ["ran      notes.py - its script, gen/notes.py, changed since HEAD",
                 "deck/speaker-notes.txt regenerated DIFFERENT"])

# 3. A GENERATED FILE EDITED BY HAND: the generator that writes it runs.
with Edit("deck/one-pager.svg") as p:
    p.write_text(p.read_text(encoding="utf-8").replace("</svg>", "<!-- by hand --></svg>"),
                 encoding="utf-8")
    since("a generated file edited by hand -> its generator runs",
          True, ["ran      deck.py - it writes deck/one-pager.svg, changed since HEAD",
                 "deck/one-pager.svg regenerated DIFFERENT"])

# 4. THE MAP EDITED BY HAND: composed, not trusted, and held to its bytes.
with Edit("map/map.json") as p:
    p.write_text(p.read_text(encoding="utf-8").replace('"repository": "fernhollow-kettles"',
                                                       '"repository": "fernhollow"'), encoding="utf-8")
    since("the map edited by hand -> the composed map differs",
          True, ["map/map.json regenerated DIFFERENT"])

# 5. A GENERATED FILE DELETED: its generator runs, and the gate names it.
with Edit("ledger.json") as p:
    p.unlink()
    since("a generated file deleted -> named as missing",
          True, ["ledger.json is tracked and is not in the working tree"])
    p.write_text("deleted\n", encoding="utf-8")       # so Edit sees the bytes moved, and restores

# 6. A MAP FROM ANOTHER RELEASE: every generator runs, and the run says why.
with Edit("map/map.json") as p:
    p.write_text(p.read_text(encoding="utf-8").replace('"engine": "', '"engine": "0.0.', 1),
                 encoding="utf-8")
    commit("a map another engine wrote")
    try:
        # And that full run fails: the committed map is not what this engine writes.
        since("a map from another release -> every generator runs, said",
              True, ["every generator runs - the map at HEAD", "was written by wherefore 0.0.",
                     "map/map.json regenerated DIFFERENT"], forbid=["skipped"])
    finally:
        git(ROOT, "reset", "-q", "--soft", "HEAD~1")
git(ROOT, "reset", "-q")

# 7. NOTHING BROKEN: every generator skipped, the map composed, and it passes.
since("nothing broken -> every generator skipped, and the gate passes",
      False, ["0 ran, 5 skipped, 1 composed", "UNKNOWN        0"])

# 8. THE LIMIT - "a read through a shell". gen/origin.py reads origin.txt by
# running `cat`, which is not Python, so the observer never sees the read and
# the map does not record it. Change origin.txt: --since finds nothing that
# origin.py reads has moved, skips it, and passes a stale site/origin.txt. The
# full gate runs it and fails. This is the case the docs point at.
with Edit("origin.txt") as p:
    p.write_text("Assembled and tested in Porto.\n", encoding="utf-8")
    since("a read through a shell: --since cannot see it, and passes the stale file",
          False, ["skipped  origin.py - nothing it reads or writes has changed since HEAD"])
    full("a read through a shell: the full gate runs it, and fails",
         True, ["site/origin.txt regenerated DIFFERENT"])

left = git(ROOT, "status", "--porcelain").stdout
if left.strip():
    print(f"::error::the proof did not put the fixture back:\n{left}")
    results.append(False)
sys.exit(report(results))
