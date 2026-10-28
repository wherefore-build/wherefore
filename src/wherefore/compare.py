"""Is this file what was committed? Bytes, unless a reason says otherwise.

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
NUM = re.compile(r"-?\d+\.?\d*(?:[eE][-+]?\d+)?")

# rel -> (edge, flat, tone) for every picture compared in this process, so the
# gate can show the judgement even when it passes.
MEASURED = {}


def picture_diff(was, now):
    """How much the picture differs, as a drawing and as color.

    Returns (edge, flat, tone) or None if the two cannot be compared as pictures
    at all - a different canvas size is a real change, not a rasteriser one.

    `edge` is judged against EDGE_TOL: mean absolute difference of the
    variance-normalised edge magnitude, on a 128-wide thumbnail. Thumbnailing
    averages ~360 source pixels into each compared pixel, so antialiasing washes
    out while composition does not. Normalising by the edge map's own standard
    deviation makes it scale-free, so a contrast or gamma difference cancels.

    `tone` is judged against TONE_TOL: the largest box-blurred signed
    per-channel difference of the same thumbnails, in levels. See TONE_TOL.

    `flat` is the older mean-centred intensity difference, kept and reported
    because it is what the first CI run measured and what showed the statistic
    had to change. Nothing is judged on it: centring cancels a uniform tint.
    """
    from PIL import Image
    return picture_metrics(Image.open(was), Image.open(now))


def picture_faults(d, edge_tol, tone_tol):
    """What is wrong with a comparison, in words. Empty is the same picture.

    The words are what checks/picture_tolerance_proof.py requires of each break,
    so a fault caught by the OTHER term does not count as caught.
    """
    if d is None:
        return ["the canvas is a different SIZE, which is not a rasteriser difference"]
    out = []
    if d[0] >= edge_tol:
        out.append(f"the DRAWING moved: edge difference {d[0]:.4f}, past the "
                   f"{edge_tol:g} a rasteriser is allowed")
    if d[2] >= tone_tol:
        out.append(f"the COLOR moved: tone difference {d[2]:.1f} levels, past the "
                   f"{tone_tol:g} a rasteriser is allowed")
    return out


def picture_metrics(a, b):
    """The same judgement, on two images already in hand."""
    import math
    import numpy as np
    from PIL import Image
    if a.size != b.size:
        return None

    def thumb(im, w=128):
        im = im.convert("RGB")
        return im.resize((w, max(1, round(w * im.height / im.width))),
                         Image.LANCZOS)

    ta, tb = thumb(a), thumb(b)

    def edges(t):
        g = np.asarray(t.convert("L"), dtype=np.float64)
        gy, gx = np.gradient(g)
        m = np.hypot(gx, gy)
        sd = m.std()
        return m / sd if sd else m

    def box(x, r):
        # A separable box mean over (2r+1)^2, the border repeated outward.
        k = 2 * r + 1
        x = np.pad(x, ((r, r), (r, r), (0, 0)), mode="edge")
        for axis in (0, 1):
            c = np.cumsum(x, axis=axis)
            c = np.concatenate([np.zeros_like(np.take(c, [0], axis=axis)), c], axis=axis)
            x = (np.take(c, range(k, c.shape[axis]), axis=axis)
                 - np.take(c, range(0, c.shape[axis] - k), axis=axis)) / k
        return x

    fa = np.asarray(ta, dtype=np.float64)
    fb = np.asarray(tb, dtype=np.float64)
    r = max(2, math.ceil(1.5 * ta.width / a.width))
    tone = float(np.abs(box(fb - fa, r)).max())
    for t in (fa, fb):
        t -= t.reshape(-1, t.shape[-1]).mean(axis=0)
    return (float(np.abs(edges(ta) - edges(tb)).mean()),
            float(np.abs(fa - fb).mean()), tone)


def same_numbers(was, now, tol):
    """Is this STEP or DXF the same drawing as that one?

    NOT BY BYTES, and the argument is this file's whole reason for existing: a
    circle is drawn through sin and cos, libm implementations differ by an ulp,
    and the writer rounds to five decimals - which is exactly where an ulp
    becomes a whole digit. Byte-identity across two machines is a requirement
    no two machines can meet. What a supplier actually has is every number
    within tol and nothing that is not a number moving at all.

    IT LIVES HERE SO THERE IS ONE OF IT. checks/coverage_gate.py had this
    inline and checks/spec_reaches_the_shop.py had nothing - it compared bytes,
    and refused to start on four STEP files whose own report said "the largest
    move is 0.00e+00 mm". The sweep could have imported the gate; it would have
    put a file the shipping-files fingerprint leaves out into the middle of
    what that job runs, which checks/leaves_are_leaves.py refuses, correctly.
    This file is already kept by both jobs, because both already call it.
    """
    old_lines = was.read_text(errors="replace").splitlines()
    new_lines = now.read_text(errors="replace").splitlines()
    if len(old_lines) != len(new_lines):
        return False
    for a, b in zip(old_lines, new_lines):
        if a == b:
            continue
        if NUM.sub("#", a) != NUM.sub("#", b):
            return False
        for x, y in zip(NUM.findall(a), NUM.findall(b)):
            if abs(float(x) - float(y)) > tol:
                return False
    return True


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
