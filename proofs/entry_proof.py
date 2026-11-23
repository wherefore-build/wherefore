#!/usr/bin/env python3
"""A corpus that hands its gate to its own script is held to the schemas its
wherefore.json declares - a `params` source's among them - and the gate names
every fact of the wrong type by its identity.

0.27.0 typed a source's facts only when the engine configured the gate from
wherefore.json itself. A corpus shaped like the pendulum names its gate in
`entry`, and its own checks/coverage_gate.py calls gate.configure() with the
inventory and the comparators it keeps - and no schemas, since the call takes
none. It declared `sources.spec` (a `params` source) and `sources.site` with
schemas, and its gate never checked either.

This copy is that shape: a generator that draws a page from the parameters,
the two scripts, and the two sources, typed. Its script is not told about
schemas, and must not need to be.

  1. the corpus as it is                         passes, both sources typed
  2. a parameter's nominal of the wrong type     named by its identity, the
                                                 name the params adapter gives
  3. a value of the wrong type in the leaves     named by its identity
     source beside it
  4. a glob in the schema that names nothing     named: it types nothing
  5. the script run bare, as CI runs it          the same fault, the same words

Usage:  python3 proofs/entry_proof.py
"""
import json
import os
import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _fixture import ENGINE, git

ROOT = pathlib.Path(tempfile.mkdtemp(prefix="wherefore-entry-")) / "pendulum"
SPEC = {"units": "mm",
        "hardware": {"bearing": {"params": {"bore": {"nominal": 8.0, "tol": [0, 0.01], "provenance": "drawing 4"},
                                            "count": {"value": 2, "provenance": "drawing 4"}}}},
        "geometry": {"arm": {"params": {"length": {"value": 240.0, "provenance": "the sketch"},
                                        "points": {"value": [[0, 0], [240, 0]], "provenance": "the sketch"}}}}}
SITE = {"company": {"name": "Pendulum Works", "since": 2019}}
FILES = {
    "wherefore.json": {
        "wherefore": 1, "name": "pendulum-shaped",
        "sources": {"spec": {"path": "spec/mk3.params.json", "adapter": "params", "why": "the object",
                             "schema": {"hardware.*": "number", "geometry.arm.length": "number",
                                        "geometry.arm.points": "array"}},
                    "site": {"path": "spec/site.json", "why": "the company",
                             "schema": {"company.name": "string", "company.since": "number"}}},
        "entry": {"why": "its lists live in the scripts its proofs plant into",
                  "list": "checks/generators.py", "gate": "checks/coverage_gate.py"}},
    "checks/generators.py": (
        "import pathlib, sys\n"
        "from wherefore import generators as G\n"
        "ROOT = pathlib.Path(__file__).resolve().parents[1]\n"
        "G.configure(ROOT, [G.Gen('page.py', 'gen', 'site/index.html, the page')])\n"
        "if __name__ == '__main__':\n    sys.exit(G.main())\n"),
    "checks/coverage_gate.py": (
        "import json, pathlib, sys\n"
        "import generators\n"
        "from wherefore import gate\n"
        "ROOT = pathlib.Path(__file__).resolve().parents[1]\n"
        "INV = ROOT / 'checks/inventory.json'\n"
        "gate.configure(ROOT, lambda: json.loads(INV.read_text()), None, 'checks/inventory.json',\n"
        "               'spec/mk3.params.json', 'params', gate.COMPARE)\n"
        "if __name__ == '__main__':\n    sys.exit(gate.main())\n"),
    "checks/inventory.json": {
        "authored": {"rules": [["*.py", "code"], ["wherefore.json", "the corpus"],
                               ["checks/inventory.json", "the inventory"], ["spec/*.json", "THE SOURCES"],
                               [".gitignore", "bytecode"]]},
        "captured": {"groups": {}}},
    "gen/page.py": (
        "import json, pathlib\n"
        "ROOT = pathlib.Path(__file__).resolve().parents[1]\n"
        "spec = json.loads((ROOT / 'spec/mk3.params.json').read_text())\n"
        "site = json.loads((ROOT / 'spec/site.json').read_text())\n"
        "arm = spec['geometry']['arm']['params']['length']['value']\n"
        "(ROOT / 'site').mkdir(exist_ok=True)\n"
        "(ROOT / 'site/index.html').write_text(f\"<p>{site['company']['name']}: a {arm} mm arm</p>\\n\")\n"),
    "spec/mk3.params.json": SPEC,
    "spec/site.json": SITE,
    ".gitignore": "__pycache__/\n",
}
for rel, body in FILES.items():
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body if isinstance(body, str) else json.dumps(body, indent=1) + "\n", encoding="utf-8")
(ROOT / "site").mkdir()
(ROOT / "site/index.html").write_text("<p>Pendulum Works: a 240.0 mm arm</p>\n", encoding="utf-8")
git(ROOT, "init", "-q")
git(ROOT, "add", "-A")
git(ROOT, "-c", "user.email=proof@wherefore", "-c", "user.name=proof", "commit", "-qm", "the pendulum's shape")
BASE = git(ROOT, "rev-parse", "HEAD").stdout.strip()

src = str(ENGINE / "src")
os.environ["PYTHONPATH"] = os.pathsep.join([src] + ([os.environ["PYTHONPATH"]] if os.environ.get("PYTHONPATH") else []))
os.environ["WHEREFORE_ROOT"] = str(ROOT)
sys.path.insert(0, src)
from wherefore import prove
prove.set_root(ROOT)
from wherefore.prove import Edit, check as _check, report

results = []
PASSES = "every tracked file is classified, and every generated one was"


def gate(name, expect_fail, must_say):
    return _check(results, name, "-m", expect_fail, must_say, "wherefore", "gate")


def rewrite(p, old, new):
    s = p.read_text(encoding="utf-8")
    if s.count(old) != 1:
        sys.exit(f"::error::{p.name}: the anchor {old!r} is not there once - the case is stale")
    p.write_text(s.replace(old, new), encoding="utf-8")


gate("1. the corpus as it is -> passes, both sources typed", False,
     [PASSES, "ok   6 facts in 2 sources typed by a schema, 0 faults"])

with Edit("spec/mk3.params.json") as p:
    rewrite(p, '"nominal": 8.0', '"nominal": "8.0"')
    gate("2. a parameter's nominal of the wrong type -> named by the name the params adapter gives", True,
         ['spec:hardware.bearing.bore is a string ("8.0"), and the schema says hardware.* is number',
          "fix it in spec/mk3.params.json",
          "FAIL 6 facts in 2 sources typed by a schema, 1 fault"])

with Edit("spec/site.json") as p:
    rewrite(p, '"since": 2019', '"since": "2019"')
    gate("3. a value of the wrong type in the leaves source beside it -> named by its identity", True,
         ['site:company.since is a string ("2019"), and the schema says company.since is number'])

with Edit("wherefore.json") as p:
    rewrite(p, '"geometry.arm.length": "number"', '"geometry.arm.lenght": "number"')
    gate("4. a glob in the schema that names nothing -> named: it types nothing", True,
         ["spec: the schema's 'geometry.arm.lenght' names no fact - a mistyped glob types nothing"])

with Edit("spec/mk3.params.json") as p:
    rewrite(p, '"value": 2,', '"value": "two",')
    _check(results, "5. the script run bare, as CI runs it -> the same fault, the same words",
           "checks/coverage_gate.py", True,
           ['spec:hardware.bearing.count is a string ("two"), and the schema says hardware.* is number'])

gate("the corpus, put back -> passes", False, [PASSES])
left = git(ROOT, "status", "--porcelain").stdout
if left.strip() or git(ROOT, "rev-parse", "HEAD").stdout.strip() != BASE:
    print(f"::error::the proof did not put the copy back:\n{left}")
    results.append(False)
shutil.rmtree(ROOT.parent, ignore_errors=True)
sys.exit(report(results))
