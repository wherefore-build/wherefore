import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from lib import SRC, DST
_gate = (SRC / "checks/coverage_gate.py").read_text(encoding="utf-8")
pf = _gate[_gate.index("def picture_diff(was, now):"):_gate.index("MEASURED = {}")]
def once(s, old, new):
    assert s.count(old) == 1, (s.count(old), old[:80]); return s.replace(old, new)
pf = once(pf, "def picture_faults(d):\n", "def picture_faults(d, edge_tol, tone_tol):\n")
pf = once(pf, "    if d[0] >= EDGE_TOL:\n", "    if d[0] >= edge_tol:\n")
pf = once(pf, '                   f"{EDGE_TOL:g} a rasteriser is allowed")\n    if d[2] >= TONE_TOL:\n',
              '                   f"{edge_tol:g} a rasteriser is allowed")\n    if d[2] >= tone_tol:\n')
pf = once(pf, '                   f"{TONE_TOL:g} a rasteriser is allowed")\n', '                   f"{tone_tol:g} a rasteriser is allowed")\n')
ss = (SRC / "checks/shipped_solids.py").read_text()
a = ss.index("def same_solid(was, now):"); b = ss.index("\n\ndef pairs(")
solid = ss[a:b]
solid = once(solid, "def same_solid(was, now):\n", "def same_numbers(was, now, tol):\n")
solid = once(solid, "    within TOL and nothing", "    within tol and nothing")
solid = once(solid, "            if abs(float(x) - float(y)) > TOL:\n", "            if abs(float(x) - float(y)) > tol:\n")

head = '''"""Is this file what was committed? Bytes, unless a reason says otherwise.

The gate compares every generated file with the snapshot it took before
regenerating, and the honest default is byte-identity. Every exception is a
file whose generator CANNOT be bit-reproducible across machines, held instead
to the thing its reader depends on - and every one is declared in wherefore.json
`compare`, by glob (fnmatch, where `*` crosses `/`), first match wins, with its
reason:

  bytes                   the default; nothing to declare
  xlsx-cells              a workbook, by its cells
  numbers      tol        every number within tol, nothing else moving at all
  picture      edge_tol tone_tol
                          a raster, as a picture: has the drawing moved, has
                          the color moved
  html-inlined-pictures   edge_tol tone_tol
                          a page's text exactly, each data: image as a picture

THE THRESHOLDS ARE NOT DEFAULTS, because they are not general. In the
repository this was extracted from they were measured - on its corpus, on three
rasterisers - and got wrong twice before they were right, and those
measurements live there, beside the numbers. A client measures its own: the
gate prints the worst figures on success for exactly that reason, because a new
machine is the only place the real cross-rasteriser number can be learned.

The functions below were moved verbatim from chaotic-pendulums-co's
checks/coverage_gate.py and checks/shipped_solids.py; only the tolerances
became arguments.
"""
import base64
import fnmatch
import io
import pathlib
import re

KINDS = {"bytes": (), "xlsx-cells": (), "numbers": ("tol",),
         "picture": ("edge_tol", "tone_tol"),
         "html-inlined-pictures": ("edge_tol", "tone_tol")}
RASTER = (".png", ".jpg", ".jpeg", ".webp")
NUM = re.compile(r"-?\\d+\\.?\\d*(?:[eE][-+]?\\d+)?")

# rel -> (edge, flat, tone) for every picture compared in this process, so the
# gate can show the judgement even when it passes.
MEASURED = {}


'''
glue = '''

def same_cells(was, now):
    """A workbook by its cells.

    A .xlsx is not a loosening: a workbook is a ZIP, a zip records the time
    each member was added, and so two builds of the same BOM from the same spec
    differ in their bytes every time while every cell in them is identical.
    Byte-identity there would fail on every run and teach whoever reads this
    check to ignore it, which costs more than it buys. What a supplier reads is
    the cells.
    """
    import openpyxl

    def cells(f):
        wb = openpyxl.load_workbook(f, read_only=True)
        return [(ws.title, [str(c.value) for r in ws.iter_rows() for c in r])
                for ws in wb]
    try:
        return cells(was) == cells(now)
    except Exception:
        return was.read_bytes() == now.read_bytes()


def same_inlined(was, now, rel, edge_tol, tone_tol):
    """A page with pictures inside it."""
    # A page can have a picture INSIDE it. The hand-over inlines the hero
    # still as a data: URI so the page travels as one file, and that put a
    # WebGL render - the one thing on this object that cannot agree across
    # rasterisers - inside a file being compared byte for byte. One level of
    # indirection from a tolerance that already existed for it.
    #
    # So the page is split: the text around the images must match exactly,
    # and each image is compared as a picture.
    #
    # WHAT THIS CANNOT SEE: two images that are the same picture. The
    # hand-over inlines a three-quarter and a front-mark view of the same
    # pose, and they measure 0.0079 apart - well inside the tolerance,
    # correctly, because at 128 px they ARE the same picture. Swap them and
    # this passes. A perceptual comparison cannot be asked to tell apart
    # what a person cannot either; if those two ever need distinguishing,
    # the answer is a page that does not inline near-identical views.
    from PIL import Image
    blob = re.compile(r"data:image/[a-z+]+;base64,([A-Za-z0-9+/=]+)")
    ta, tb = (f.read_text(encoding="utf-8", errors="replace") for f in (was, now))
    if blob.sub("#", ta) != blob.sub("#", tb):
        return False
    ia, ib = blob.findall(ta), blob.findall(tb)
    if len(ia) != len(ib):
        return False
    worst = None
    for x, y in zip(ia, ib):
        if x == y:
            continue
        try:
            d = picture_metrics(Image.open(io.BytesIO(base64.b64decode(x))),
                                Image.open(io.BytesIO(base64.b64decode(y))))
        except Exception:
            return False
        if picture_faults(d, edge_tol, tone_tol):
            MEASURED[rel] = d
            return False
        # The worst of each term, which need not be the same image's.
        worst = d if worst is None else tuple(map(max, worst, d))
    if worst:
        MEASURED[rel] = worst
    return True


class Comparators:
    """The declared exceptions to byte-identity, in the order they were declared."""

    def __init__(self, rules=()):
        self.rules = []
        for r in rules:
            kind = r["as"]
            if kind not in KINDS:
                raise SystemExit(f"::error::compare: {kind!r} is not a comparator this "
                                 f"engine has ({', '.join(KINDS)})")
            missing = [p for p in KINDS[kind] if p not in r]
            if missing:
                raise SystemExit(f"::error::compare: {kind} for {r['glob']} needs "
                                 f"{', '.join(missing)} - a threshold is measured, never "
                                 f"assumed, so the engine does not supply one")
            globs = r["glob"] if isinstance(r["glob"], list) else [r["glob"]]
            self.rules.append((globs, kind, {p: r[p] for p in KINDS[kind]}))

    def rule_for(self, rel):
        """(kind, params) for a repo-relative path. First match wins."""
        for globs, kind, params in self.rules:
            if any(fnmatch.fnmatch(rel, g) for g in globs):
                return kind, params
        return "bytes", {}

    def is_raster(self, rel):
        """A picture a browser rasterised, whose bytes are the machine's business."""
        # A RASTER, not merely a file in one of those folders. brand/web/ holds
        # favicon.svg beside the PNGs it is rasterised into, and PIL cannot open an
        # SVG - it raised UnidentifiedImageError from inside the comparison, which
        # surfaced as a proof failing for a reason that had nothing to do with it.
        return (self.rule_for(rel)[0] == "picture"
                and pathlib.PurePosixPath(rel).suffix.lower() in RASTER)

    def picture_tolerances(self, rel):
        kind, p = self.rule_for(rel)
        return p if kind in ("picture", "html-inlined-pictures") else {}

    def same(self, was, now, rel):
        """Is this file what was committed? Bytes, for everything the answer is
        honest about; the declared exception for the rest."""
        kind, p = self.rule_for(rel)
        if kind == "xlsx-cells":
            return same_cells(was, now)
        if was.read_bytes() == now.read_bytes():
            return True
        if kind == "html-inlined-pictures":
            return same_inlined(was, now, rel, p["edge_tol"], p["tone_tol"])
        if kind == "numbers":
            return same_numbers(was, now, p["tol"])
        if self.is_raster(rel):
            d = picture_diff(was, now)
            MEASURED[rel] = d
            return not picture_faults(d, p["edge_tol"], p["tone_tol"])
        return False
'''
(DST / "compare.py").write_text(head + pf.rstrip() + "\n\n\n" + solid.rstrip() + "\n" + glue, encoding="utf-8")
print("compare.py: built from checks/coverage_gate.py and checks/shipped_solids.py")
