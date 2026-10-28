#!/usr/bin/env python3
"""The origin rule holds end to end: put "made" among what happens in Porto, and
the copy the generators write from it must be refused.

A client's proof, written the way any client writes one: break the SOURCE, let
the generators carry the break into what a customer reads, and require the
check to name it in its own words. Every byte is put back.
"""
import json
import sys

from wherefore.prove import Edit, Tree, check, report, run

results = []
with Tree(), Edit("facts.json") as p:
    d = json.loads(p.read_text(encoding="utf-8"))
    d["origin"]["activities"] = ["made", "tested"]
    p.write_text(json.dumps(d, indent=1) + "\n", encoding="utf-8")
    code, out = run("-m", "wherefore", "build")
    check(results, "made, in the facts -> refused in the copy", "-m", True,
          ["made: the heating element is bought in"], "wherefore", "check", "claims")
sys.exit(report(results))
