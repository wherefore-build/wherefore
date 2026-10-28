#!/usr/bin/env python3
"""Do the recorded edits still turn the pendulum's originals into the engine's modules?

    PENDULUM=/path/to/chaotic-pendulums-co python3 tools/moved/verify.py

MOVE, DON'T IMPROVE, and this is how anyone can check it. Each gen_*.py here
starts from a file in chaotic-pendulums-co (at 460ae20, the commit the move was
made from) and applies a short list of exact edits, each required to match
exactly once. This runs all of them into a scratch directory and requires the
result to be byte-identical to what src/wherefore holds. A difference means a
moved module was changed by hand after its move - which is allowed, once parity
is proven, and should then be recorded here as an edit rather than left as a
silent divergence from the record.
"""
import os
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ENGINE = HERE.parents[1] / "src" / "wherefore"
MOVES = {"gen_observe.py": ["_observe/sitecustomize.py"],
         "gen_generators.py": ["generators.py"], "gen_prove.py": ["prove.py"],
         "gen_gate.py": ["gate.py"], "gen_compare.py": ["compare.py"],
         "gen_retired.py": ["retired.py"], "gen_reach.py": ["reach.py"]}

if "PENDULUM" not in os.environ:
    sys.exit("set PENDULUM to a checkout of chaotic-pendulums-co at 460ae20")
out = pathlib.Path(tempfile.mkdtemp(prefix="wherefore-moved-"))
env = dict(os.environ, MOVED_OUT=str(out))
bad = 0
for script, made in MOVES.items():
    r = subprocess.run([sys.executable, str(HERE / script)], env=env, capture_output=True, text=True)
    if r.returncode:
        print(f"::error::{script} no longer applies: {(r.stderr or r.stdout).strip()[-300:]}")
        bad += 1
        continue
    for m in made:
        same = (out / m).read_bytes() == (ENGINE / m).read_bytes()
        print(f"  {'ok  ' if same else 'DIFF'} {m:26} {r.stdout.strip()}")
        bad += not same
sys.exit(1 if bad else 0)
