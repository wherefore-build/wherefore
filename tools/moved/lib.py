"""Build an engine module from the pendulum original by exact, asserted edits.

PENDULUM is a checkout of chaotic-pendulums-co at the commit the move was made
from (460ae20). MOVED_OUT is where the modules are written: the engine's own
src/wherefore by default, and a scratch directory when verify.py asks whether
these edits still reproduce what is committed.
"""
import os, pathlib, sys
SRC = pathlib.Path(os.environ["PENDULUM"])
DST = pathlib.Path(os.environ.get("MOVED_OUT") or
                   pathlib.Path(__file__).resolve().parents[2] / "src" / "wherefore")

def move(src_rel, dst_name, edits):
    s = (SRC / src_rel).read_text(encoding="utf-8")
    for i, (old, new) in enumerate(edits):
        n = s.count(old)
        if n != 1:
            sys.exit(f"{dst_name}: edit {i} matched {n} times: {old[:80]!r}")
        s = s.replace(old, new)
    (DST / dst_name).write_text(s, encoding="utf-8")
    print(f"{dst_name}: {len(edits)} edits from {src_rel}")
