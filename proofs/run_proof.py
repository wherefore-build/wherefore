#!/usr/bin/env python3
"""Break a generator that is not Python, and require the gate to be as strict.

A `run` generator - node, sh, a CAD exporter - never loads the observer, so
what it writes is seen by picturing the tree before and after it runs
(generators.watching). That is a second way of seeing, and a check is not
trusted until it has been shown to fail: so each fault gate_proof.py plants in
a Python generator is planted here in a shell one, and the gate must say the
same thing about it.

The fixture company gains one shell generator in this proof's copy - gen/robots.sh,
writing site/robots.txt from the kettle's name - committed, so the copy is a
corpus with both kinds. Then:

  1.  nothing invokes it                           its file goes UNKNOWN
  2.  it writes only when the file changed         the mtime trap: UNKNOWN too
  3.  its output edited by hand                    regenerated DIFFERENT
  4.  it writes a file nobody tracks               named as untracked
  5.  it exits non-zero                            it covered nothing
  6.  it writes, then puts the old mtime back      seen anyway: ctime moved
  7.  the write is made by its own child process   seen, and the gate passes
  8.  nothing broken                               and it passes

Usage:  python3 proofs/run_proof.py
"""
import contextlib
import json
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _fixture import fresh, git

ROOT = fresh("run")
from wherefore.prove import Edit, check as _check, report

GATE = ("-m", "wherefore", "gate")
results = []

ROBOTS = ('name=$(sed -n \'s/.*"name": *"\\([^"]*\\)".*/\\1/p\' ../facts.json | head -n 1)\n'
          'printf "# %s\\nUser-agent: *\\nAllow: /\\n" "$name" > ../site/robots.txt\n')
WRITE = '> ../site/robots.txt\n'


def check(name, expect_fail, must_say, forbid=()):
    return _check(results, name, GATE[0], expect_fail, must_say, *GATE[1:], forbid=forbid)


@contextlib.contextmanager
def config(edit):
    with Edit("wherefore.json") as p:
        d = json.loads(p.read_text(encoding="utf-8"))
        edit(d)
        p.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        yield


def planted(path, old, new):
    p = ROOT / path
    s = p.read_text(encoding="utf-8")
    if s.count(old) != 1:
        sys.exit(f"::error::{path}: the anchor {old!r} is not there once - the case is stale")
    p.write_text(s.replace(old, new), encoding="utf-8")


# The shell generator, added to the copy and committed with what it makes.
(ROOT / "gen/robots.sh").write_text(ROBOTS, encoding="utf-8")
d = json.loads((ROOT / "wherefore.json").read_text(encoding="utf-8"))
d["generators"].insert(1, {"run": ["sh", "robots.sh"], "cwd": "gen",
                           "makes": "site/robots.txt, what crawlers are told"})
d["inventory"]["authored"]["rules"].insert(1, ["gen/*.sh", "code: a generator in shell"])
(ROOT / "wherefore.json").write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n",
                                     encoding="utf-8")
subprocess.run(["sh", "robots.sh"], cwd=ROOT / "gen", check=True)
if "User-agent" not in (ROOT / "site/robots.txt").read_text(encoding="utf-8"):
    sys.exit("::error::gen/robots.sh did not write site/robots.txt - the proof's setup is stale")
git(ROOT, "add", "-A")
git(ROOT, "-c", "user.email=proof@wherefore", "-c", "user.name=proof", "commit", "-qm",
    "a generator in shell")

# 1. MODE 2 - a command that is never invoked.
with config(lambda d: d["generators"].pop(1)):
    check("nothing invokes sh robots.sh -> its file goes UNKNOWN",
          True, ["site/robots.txt is unclassified"])

# 2. THE mtime TRAP, in shell: write somewhere else, copy only if it moved.
with Edit("gen/robots.sh"):
    planted("gen/robots.sh", WRITE,
            '> ../robots.new\ncmp -s ../robots.new ../site/robots.txt || cp ../robots.new ../site/robots.txt\n'
            'rm -f ../robots.new\n')
    check("the trap: robots.txt written only when it changed -> UNKNOWN",
          True, ["site/robots.txt is unclassified"])

# 3. ITS OUTPUT EDITED BY HAND.
with Edit("site/robots.txt") as p:
    p.write_text(p.read_text(encoding="utf-8") + "Disallow: /drafts/\n", encoding="utf-8")
    check("robots.txt edited by hand -> regenerated DIFFERENT",
          True, ["site/robots.txt regenerated DIFFERENT"])

# 4. A FILE IT WRITES THAT NOBODY TRACKS.
with Edit("gen/robots.sh"):
    planted("gen/robots.sh", WRITE, WRITE + 'cp ../site/robots.txt ../site/robots.bak\n')
    try:
        check("it writes a file git does not track -> named",
              True, ["site/robots.bak is a generated file git doesn't track (written by sh robots.sh)"])
    finally:
        (ROOT / "site/robots.bak").unlink(missing_ok=True)

# 5. IT FAILS.
with Edit("gen/robots.sh") as p:
    p.write_text(p.read_text(encoding="utf-8") + 'echo "no crawlers today" >&2\nexit 4\n',
                 encoding="utf-8")
    check("it exits non-zero -> it covered nothing",
          True, ["sh robots.sh failed while the gate ran it", "no crawlers today"])

# 6. A WRITE THAT HIDES ITS mtime. Nothing can set a ctime back.
with Edit("gen/robots.sh"):
    planted("gen/robots.sh", WRITE,
            '> ../robots.new\n'
            'touch -r ../site/robots.txt ../robots.ref\n'        # the mtime it had
            'cp ../robots.new ../site/robots.txt\n'              # the write
            'touch -r ../robots.ref ../site/robots.txt\n'        # the mtime put back
            'rm -f ../robots.new ../robots.ref\n')
    check("it writes and puts the old mtime back -> seen anyway, and the gate passes",
          False, ["UNKNOWN        0", "generated      5"])

# 7. A WRITE BY ITS OWN CHILD: the picture sees every process, in any language.
with Edit("gen/robots.sh"):
    planted("gen/robots.sh", WRITE, '| sh -c \'cat > ../site/robots.txt\'\n')
    check("the write made by a child process of the command -> seen, and the gate passes",
          False, ["UNKNOWN        0", "generated      5"])

# 8. AND IT PASSES WHEN NOTHING IS BROKEN.
check("clean tree, a Python and a shell generator -> the gate passes",
      False, ["UNKNOWN        0", "generated      5"])

left = git(ROOT, "status", "--porcelain").stdout
if left.strip():
    print(f"::error::the proof did not put the fixture back:\n{left}")
    results.append(False)
sys.exit(report(results))
