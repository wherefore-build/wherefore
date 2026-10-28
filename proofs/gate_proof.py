#!/usr/bin/env python3
"""Break each bug the coverage gate exists to catch, and require it to notice.

The rule this engine exists to enforce is that a check is not trusted until it
has been shown to FAIL on the thing it was written for. This is that proof for
the gate, on the fixture company rather than on the repository the gate was
extracted from - whose own proof stays there, planting into its own files, as
the evidence that the extraction changed nothing.

The breaks mirror that proof's, case for case, and add the ones the engine's
contract makes worth stating: a write the observer cannot see, a child process
it can, and a generator that throws.

  1.  nothing invokes the landing page's generator    mode 2: its page goes UNKNOWN
  2.  it writes only when the page changed            the mtime trap: UNKNOWN too
  3.  a generated file edited by hand                 not what the generator makes
  4.  a new tracked file nobody classified            UNKNOWN
  4b. a generated file dropped from the index         named as untracked
  5.  a capture's source moved                        the re-make list
  5b. a group that says known_stale                   refused, not honoured
  6.  a rule claiming a generated file                a contradiction
  7.  the ledger moved                                the corpus does not settle
  8.  a generator writes a file nobody tracks         named as untracked
  9.  a generator throws                              it covered nothing
  10. the page written by a shell, not by Python      invisible to the observer,
                                                      so UNKNOWN - the loud side
  11. the page written by a child python             seen, and the gate passes
  12. nothing broken                                  and it passes

Usage:  python3 proofs/gate_proof.py
"""
import contextlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _fixture import fresh, git

ROOT = fresh("gate")
from wherefore.prove import Edit, check as _check, report

GATE = ("-m", "wherefore", "gate")
results = []


def check(name, expect_fail, must_say, forbid=()):
    return _check(results, name, GATE[0], expect_fail, must_say, *GATE[1:], forbid=forbid)


@contextlib.contextmanager
def config(edit):
    """Plant a fault in wherefore.json by changing its parsed form."""
    with Edit("wherefore.json") as p:
        d = json.loads(p.read_text(encoding="utf-8"))
        edit(d)
        p.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        yield


def planted(path, old, new):
    """Replace one anchor in a file, failing loudly if the anchor has moved."""
    p = ROOT / path
    s = p.read_text(encoding="utf-8")
    if s.count(old) != 1:
        sys.exit(f"::error::{path}: the anchor {old!r} is not there once - the case is stale")
    p.write_text(s.replace(old, new), encoding="utf-8")


WRITE = 'OUT.write_text(html, encoding="utf-8")'

# 1. MODE 2 - a generator that is never invoked.
with config(lambda d: d["generators"].pop(0)):
    check("mode 2: nothing invokes landing.py -> its page goes UNKNOWN",
          True, ["site/index.html is unclassified"])

# 2. THE mtime TRAP.
with Edit("gen/landing.py"):
    planted("gen/landing.py", WRITE,
            'if not OUT.exists() or OUT.read_text(encoding="utf-8") != html:\n'
            '    ' + WRITE)
    check("the trap: the page written only when it changed -> UNKNOWN",
          True, ["site/index.html is unclassified"])

# 3. A GENERATED FILE EDITED BY HAND.
with Edit("deck/one-pager.svg") as p:
    p.write_text(p.read_text(encoding="utf-8").replace("</svg>", "<!-- by hand --></svg>"),
                 encoding="utf-8")
    check("a generated file edited by hand -> regenerated DIFFERENT",
          True, ["deck/one-pager.svg regenerated DIFFERENT"])

# 4. A NEW FILE NOBODY CLASSIFIED.
new = ROOT / "site/about.html"
new.write_text("<p>about</p>\n", encoding="utf-8")
git(ROOT, "add", "-N", "site/about.html")
try:
    check("a new tracked file matching no rule -> UNKNOWN",
          True, ["site/about.html is unclassified"])
finally:
    git(ROOT, "rm", "-f", "--quiet", "site/about.html")
    new.unlink(missing_ok=True)

# 4b. A GENERATED FILE GIT DOESN'T TRACK.
mode, sha = git(ROOT, "ls-files", "-s", "--", "site/index.html").stdout.split()[:2]
try:
    git(ROOT, "rm", "--cached", "--quiet", "--", "site/index.html")
    check("a generated page dropped from the index -> named",
          True, ["site/index.html is a generated file git doesn't track"])
finally:
    git(ROOT, "update-index", "--add", "--cacheinfo", f"{mode},{sha},site/index.html")

# 5. MODE 3 - the source of a capture moves and the capture does not.
with Edit("facts.json") as p:
    d = json.loads(p.read_text(encoding="utf-8"))
    d["product"]["capacity_l"] = 1.7
    p.write_text(json.dumps(d, indent=1) + "\n", encoding="utf-8")
    check("mode 3: the kettle's size moved -> re-make the photograph",
          True, ["'the product photograph' was made from has moved",
                 "NEED RE-MAKING", "photos/hero.svg"])

# 5b. known_stale, which used to excuse a moved source for ever.
with config(lambda d: d["inventory"]["captured"]["groups"]["the product photograph"]
                .update(known_stale="drawn before the lid changed")):
    check("a group that says known_stale -> refused",
          True, ["'the product photograph' carries known_stale, which this gate no longer honors"])

# 6. A DECLARATION AND A GENERATOR CLAIMING THE SAME FILE.
with config(lambda d: d["inventory"]["authored"]["rules"]
                .insert(0, ["site/*.html", "a deliberately wrong rule"])):
    check("a rule claiming a generated file -> contradiction",
          True, ["is declared authored (site/*.html)"])

# 7. THE LEDGER MOVED: read first, written last, so one pass does not settle it.
with Edit("ledger.json") as p:
    p.write_text('{\n "deck": "000000000000"\n}\n', encoding="utf-8")
    check("the ledger moved -> the corpus does not settle in one pass",
          True, ["the corpus is not a fixed point"])

# 8. A GENERATED FILE NOBODY TRACKS OR IGNORES.
with Edit("gen/deck.py"):
    planted("gen/deck.py", 'OUT.write_text(svg, encoding="utf-8")\n',
            'OUT.write_text(svg, encoding="utf-8")\n'
            '(ROOT / "deck/draft.svg").write_text(svg, encoding="utf-8")\n')
    try:
        check("a generator writes a file git does not track -> named",
              True, ["deck/draft.svg is a generated file git doesn't track"])
    finally:
        (ROOT / "deck/draft.svg").unlink(missing_ok=True)

# 9. A GENERATOR THAT THROWS covers nothing.
with Edit("gen/notes.py") as p:
    p.write_text(p.read_text(encoding="utf-8") + 'raise SystemExit("no notes today")\n',
                 encoding="utf-8")
    check("a generator throws -> it covered nothing",
          True, ["notes.py failed while the gate ran it"])

# 10. A WRITE THE OBSERVER CANNOT SEE: the page written by a shell. The engine's
# contract is that this fails LOUDLY - the page lands as unclassified - and never
# passes as covered.
with Edit("gen/landing.py"):
    planted("gen/landing.py", WRITE,
            'import subprocess\n'
            'subprocess.run(["sh", "-c", f"cat > \'{OUT}\'"], input=html, text=True, check=True)')
    check("the page written by a shell, which Python's open() never sees -> UNKNOWN",
          True, ["site/index.html is unclassified"])

# 11. A WRITE IT CAN: a child python inherits the observer through PYTHONPATH.
with Edit("gen/landing.py"):
    planted("gen/landing.py", WRITE,
            'import subprocess, sys\n'
            'subprocess.run([sys.executable, "-c", "import sys, pathlib; '
            'pathlib.Path(sys.argv[1]).write_text(sys.stdin.read(), encoding=\'utf-8\')", '
            'str(OUT)], input=html, text=True, check=True)')
    check("the page written by a child python -> seen, and the gate passes",
          False, ["UNKNOWN        0"])

# 12. AND IT PASSES WHEN NOTHING IS BROKEN.
check("clean tree -> the gate passes", False, ["UNKNOWN        0", "0 groups out of date"])

left = git(ROOT, "status", "--porcelain").stdout
if left.strip():
    print(f"::error::the proof did not put the fixture back:\n{left}")
    results.append(False)
sys.exit(report(results))
