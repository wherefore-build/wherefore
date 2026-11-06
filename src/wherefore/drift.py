"""Drift: a value said by hand in several places that no source holds - found, counted, and drawn on the map.

THE SCAN, TURNED ON A CORPUS. `wherefore scan` finds, in any repository, the
values stated more than one way. Inside a corpus the question is sharper:
of the files a person writes by hand - authored, or captured - which state a
value in two or more of them that no source holds? A generated file restates
its sources by construction, and reach holds that. A hand-written file that
states a value also stated in another hand-written file, with no source
behind either, is a copy nobody is keeping current: the price in the README
and in the pitch, the limit in two docs. That is drift, and this names each
value, the files that say it, and how many there are.

SEEN, AND SEEN SHRINKING. The map (`wherefore graph`) draws every drifting
value beside the files that state it, with the count in its legend. A
`drift` section in wherefore.json declares how many the corpus allows:

    "drift": {"allow": 4, "why": "the two docs' limits, tracked next",
              "ignore": {"brand/fonts/**": "third-party licences, unchanged"}}

`wherefore check drift` fails when more drift than that; when fewer do, it
says so and asks for the number to come down, so the allowance only ever
falls. Without a section, the check reports and passes: the first run says
what there is to declare.

WHAT HOLDS A VALUE. A source holds a value when the value is a leaf of the
source, or a number, version or money inside a leaf's text. Comparison is
the scan's own: `$89`, `89` and `89.0` are one value.

WHAT IS READ: what a person reads - prose and markup, by hand. A string in
a script is the script's business, and a generator that restates a source
is reach's. NOT READ: code, files the scan does not read (images, data,
lockfiles), changelogs and histories, generated files, the sources
themselves, wherefore.json, and what `ignore` names with a reason -
third-party text nobody here writes.
"""
import fnmatch
import collections
import json
import pathlib
import re
import subprocess

from . import scan, sources

FIELDS = ("allow", "why", "ignore")
NEVER = {"wherefore.json", "requirements-engine.txt", "requirements-browser.txt"}


def validate(doc):
    d = doc.get("drift")
    if d is None:
        return
    from .config import ConfigError
    if not isinstance(d, dict):
        raise ConfigError("`drift` is an object: allow, the number of drifting values this corpus "
                          "still allows, and why")
    unknown = set(d) - set(FIELDS)
    if unknown:
        raise ConfigError(f"`drift` has {', '.join(sorted(unknown))}, which it does not take: allow, why")
    if not isinstance(d.get("allow"), int) or isinstance(d.get("allow"), bool) or d["allow"] < 0:
        raise ConfigError("`drift.allow` is a whole number: how many drifting values this corpus still allows")
    if not (isinstance(d.get("why"), str) and d["why"].strip()):
        raise ConfigError("`drift.why` says what the allowed drift is, and what will track it")
    ign = d.get("ignore", {})
    if not isinstance(ign, dict) or not all(isinstance(k, str) and k and isinstance(v, str) and v.strip()
                                            for k, v in ign.items()):
        raise ConfigError("`drift.ignore` maps a glob of files not read for drift to the reason - "
                          "third-party text, unchanged, is the usual one")


def _tracked(root):
    out = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, text=True, check=True).stdout
    return [p for p in out.split("\0") if p]


def by_hand(cfg):
    """[(rel, kind)] for every tracked file written by hand: authored, under a
    rule, or captured, in a group. Generated and unclassified files are left
    out; so are the sources, wherefore.json and the pins."""
    from . import gate, graph
    graph.configure(cfg)                   # as the gate is: an `entry` corpus configures itself in Python
    decl = gate.DECL()
    decl.setdefault("authored", {}).setdefault("rules", [])
    decl.setdefault("captured", {}).setdefault("groups", {})
    rules = decl["authored"]["rules"]
    captured = gate.captured_files(decl)
    srcs = {s["path"] for s in (cfg.doc.get("sources") or {}).values()}
    ignored = [g.replace("**", "*") for g in ((cfg.doc.get("drift") or {}).get("ignore") or {})]
    out = []
    for rel in _tracked(cfg.root):
        if rel in NEVER or rel in srcs or any(fnmatch.fnmatch(rel, g) for g in ignored):
            continue
        if rel in captured:
            out.append((rel, "captured"))
        elif gate.authored_rule(rel, rules):
            out.append((rel, "authored"))
    return out


def held_values(cfg):
    """Every value a source holds, normalised the scan's way: each leaf as a
    whole, and every number, version or money inside a leaf's text."""
    from . import gate
    held = set()
    paths = [cfg.root / src["path"] for src in (cfg.doc.get("sources") or {}).values()]
    if not paths and gate.SPEC:                 # an `entry` corpus names its source in Python
        paths = [cfg.root / gate.SPEC]
    for path in paths:
        if not path.is_file() or path.suffix.lower() != ".json":
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        for _dotted, v in sources.leaves(doc):
            if isinstance(v, bool) or v is None:
                continue
            text = str(v)
            if isinstance(v, (int, float)):
                held.add(_bare(scan._norm("num", text)))
            for m in scan.TOKEN.finditer(text):
                if m.lastgroup in ("num", "money", "pct", "version"):
                    held.add(_bare(scan._norm(m.lastgroup, m.group())))
    return held


def _anchor(key):
    """The word a value is said with - its unit, or the thing it counts: the
    first real word after it, else the last before. Two files that say
    "boils in 3 minutes" and "3 minutes flat" say one thing."""
    _kind, left, right = key
    for side in (right, reversed(left)):
        for w in side:
            if w != "#" and w not in scan.STOP and len(w) > 1:
                return w
    return ""


def _bare(v):
    """A value with its currency sign and percent stripped, for holding: the
    source says 89, the page says $89."""
    return re.sub(r"^[$€£¥]|%$", "", v)


def _lines(path):
    src = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() in (".html", ".htm", ".svg"):
        return scan.read_markup(src, svg=path.suffix.lower() == ".svg")[0]
    return scan.read_text(src)


def find(cfg):
    """{"values": [{says, kind, value, files, count}], "read": n, "held": n}"""
    hand = by_hand(cfg)                          # configures the corpus, which names its source
    held = held_values(cfg)
    seen = collections.defaultdict(list)
    read = 0
    for rel, _kind in hand:
        path = cfg.root / rel
        suffix = path.suffix.lower()
        # WHAT A PERSON READS: prose and markup. A string in a script is the
        # script's business - a generator that restates a source is reach's.
        if suffix not in scan.TEXT or scan.HISTORY_FILE.search(path.name):
            continue
        read += 1
        for key, value, n, raw in scan.statements(_lines(path)):
            seen[(key[0], value, _anchor(key))].append((key, rel, n, raw))
    values, kept = [], 0
    for (kind, value, _anchor_word), occ in seen.items():
        files = sorted({rel for _key, rel, _n, _raw in occ})
        if len(files) < 2:
            continue
        if _bare(value) in held:
            kept += 1
            continue
        _kind, left, right = occ[0][0]
        values.append({"says": " ".join(list(left) + ["{}"] + list(right)), "kind": kind, "value": value,
                       "files": files, "count": len(occ)})
    values.sort(key=lambda v: (-len(v["files"]), -v["count"], v["says"], v["value"]))
    return {"values": values, "read": read, "held": kept}


def report(found, allow=None):
    """The drift as a person reads it, and the exit code."""
    vals = found["values"]
    lines = []
    for v in vals:
        shown = ", ".join(v["files"][:4]) + (f", and {len(v['files']) - 4} more" if len(v["files"]) > 4 else "")
        lines.append(f"  {v['value']:<12} \"{v['says']}\"  in {len(v['files'])} files, {v['count']}x: {shown}")
    n = len(vals)
    what = (f"{n} value{'s drift' if n != 1 else ' drifts'}: said by hand in two or more of {found['read']} files, "
            f"held by no source; {found['held']} held")
    if allow is None:
        if n:
            lines.append(f"\n{what}. Declare how many this corpus allows in wherefore.json - "
                         f"\"drift\": {{\"allow\": {n}, \"why\": ...}} - and lower it as each is tracked")
            return "\n".join(lines), 0
        return f"ok   nothing drifts: every value said by hand in two or more of {found['read']} files is held by a source", 0
    if n > allow:
        lines.append(f"\n::error::{what}, and wherefore.json allows {allow}. Track one in a source, "
                     f"or raise the allowance with why")
        return "\n".join(lines), 1
    if n < allow:
        lines.append(f"\nok   {what}, under the {allow} allowed: lower drift.allow to {n}, so it cannot come back")
    else:
        lines.append(f"\nok   {what}, the {allow} allowed")
    return "\n".join(lines), 0


def main(cfg, args):
    if args:
        print("usage: wherefore check drift")
        return 0 if args[0] in ("-h", "--help") else 2
    validate(cfg.doc)
    found = find(cfg)
    text, code = report(found, (cfg.doc.get("drift") or {}).get("allow"))
    print(text)
    return code
