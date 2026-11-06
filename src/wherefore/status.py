"""Where a repository stands, in one read: `wherefore status`.

ONE FILE, FOR WHATEVER READS IT. Every other command answers one question:
the gate, what each file is; drift, what is said by hand twice; launch, where
each thing's stage stands. A person, an agent or the app wants all of it at
once, and wants it as data. This puts the answers the engine already gives
into one document - nothing here judges anything the other commands do not -
and prints it as a few lines, or as JSON:

    wherefore status                  the lines
    wherefore status --json           the document, on stdout
    wherefore status --out PATH       the document, to PATH, and the lines
    wherefore status --gate ...       and run the gate first, for its verdict

WHAT EACH FILE IS. Without `--gate` nothing runs: the files are sorted by
what wherefore.json declares - written by hand, or captured - and the rest are
left for the gate, which alone runs the generators and so alone can say each
was built and is current. With `--gate` the gate runs, in its own process, as
`wherefore gate` would, and the document carries its verdict and its counts.
A corpus that hands its gate to its own script (`entry`) gets that script's
verdict, and its counts only if it prints them the way the gate does.

A REPOSITORY NOT SET UP YET - no wherefore.json - is scanned instead, the way
`wherefore scan .` would: how many values it states, in how many files, and
how many disagree. That is the first thing the app shows for it, beside the
step that sets it up.

The document's shape is versioned by `status`, and changes only with the
engine's minor version. CI writes it with `--gate --out` and keeps it as the
run's artifact; nothing commits it, since it describes the commit it is in.
"""
import json
import os
import pathlib
import re
import subprocess
import sys

from . import __version__

SHAPE = 1
PIN = re.compile(r"^\s*wherefore-build\s*(?:==\s*(?P<version>[^\s#;]+)|@\s*\S+@(?P<commit>[0-9a-f]{7,40}))", re.M)
COUNT = re.compile(r"^\s+(generated|authored|captured|UNKNOWN)\s+(\d+)\b", re.M)


def _git(root, *args):
    r = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def _pinned(root):
    """The engine release this repository pins, from requirements-engine.txt: a version, or a commit."""
    path = root / "requirements-engine.txt"
    if not path.is_file():
        return None
    m = PIN.search(path.read_text(encoding="utf-8"))
    if not m:
        return None
    return {"version": m["version"]} if m["version"] else {"commit": m["commit"]}


def _declared(cfg):
    """{tracked, written, captured, left}: what wherefore.json says each file is, running nothing."""
    from . import gate
    gate.configure_from(cfg)
    decl = gate.DECL()
    rules = (decl.get("authored") or {}).get("rules") or []
    captured = gate.captured_files({"captured": decl.get("captured") or {"groups": {}}})
    tracked = [p for p in (_git(cfg.root, "ls-files", "-z") or "").split("\0") if p]
    n_cap = sum(1 for f in tracked if f in captured)
    n_auth = sum(1 for f in tracked if f not in captured and gate.authored_rule(f, rules))
    return {"tracked": len(tracked), "written": n_auth, "captured": n_cap, "left": len(tracked) - n_auth - n_cap}


def _judged(root):
    """The gate's verdict and counts, from running it as `wherefore gate` would."""
    env = dict(os.environ)
    env.pop("WHEREFORE_ROOT", None)
    r = subprocess.run([sys.executable, "-m", "wherefore", "gate"], cwd=root, env=env,
                       capture_output=True, text=True)
    counts = {k: int(v) for k, v in COUNT.findall(r.stdout + r.stderr)}
    out = {"passed": r.returncode == 0}
    if counts:
        out.update(built=counts.get("generated"), written=counts.get("authored"),
                   captured=counts.get("captured"), unaccounted=counts.get("UNKNOWN"))
    return out


def find(root, gate=False):
    """The status document for the repository at `root`."""
    from . import config as cfgmod
    root = pathlib.Path(root)
    doc = {"status": SHAPE, "engine": __version__, "commit": _git(root, "rev-parse", "HEAD"),
           "pins": _pinned(root)}
    if not (root / cfgmod.NAME).is_file():
        from . import scan
        got = scan.scan([str(root)])
        doc.update(name=root.name, set_up=False,
                   scan={"stated": got["stated"], "files": got["sources"], "disagree": len(got["disagree"])})
        return doc
    try:
        cfg = cfgmod.load(root)
    except cfgmod.ConfigError as e:
        # Set up, and refused: said, never read as not set up.
        doc.update(name=root.name, set_up=True, invalid=str(e).removeprefix("::error::"))
        return doc
    doc.update(name=cfg.name, set_up=True)
    files = {}
    if not cfg.entry("gate"):
        try:
            files.update(_declared(cfg))
        except Exception as e:             # a corpus the engine cannot read this way says so, and the rest stands
            files["unread"] = f"{type(e).__name__}: {e}"
    if gate:
        files["gate"] = _judged(cfg.root)
    doc["files"] = files
    from . import drift, launch
    drifting = drift.find(cfg)
    doc["drift"] = {"values": len(drifting["values"]), "allowed": (cfg.doc.get("drift") or {}).get("allow"),
                    "read": drifting["read"],
                    "list": [{"value": v["value"], "says": v["says"], "files": v["files"]} for v in drifting["values"]]}
    doc["launch"] = launch.find(cfg) if cfg.doc.get("launch") is not None else {"ladders": []}
    return doc


def lines(doc):
    """The document as a few lines a person reads."""
    pins = doc.get("pins") or {}
    pinned = (f" (pins {pins['version']})" if "version" in pins else
              f" (pins {pins['commit'][:7]})" if "commit" in pins else "")
    out = [doc["name"], f"  engine   wherefore {doc['engine']}{pinned}"]
    if doc.get("invalid"):
        out.append(f"  refused  {doc['invalid']}")
        return out
    if not doc["set_up"]:
        s = doc["scan"]
        out.append(f"  scan     {s['stated']} values stated in {s['files']} files; {s['disagree']} disagree")
        out.append("  not set up: nothing holds those values yet. `wherefore init` starts")
        return out
    f = doc["files"]
    judged = f.get("gate")
    if judged and judged.get("built") is not None:
        files = (f"{f.get('tracked', '?')} tracked: {judged['built']} built, {judged['written']} written, "
                 f"{judged['captured']} captured, {judged['unaccounted']} unaccounted")
    elif "tracked" in f:
        files = (f"{f['tracked']} tracked: {f['written']} written, {f['captured']} captured, "
                 f"{f['left']} for the gate to judge")
    else:
        files = f.get("unread", "sorted by the corpus's own gate")
    if judged:
        files += " - the gate passed" if judged["passed"] else " - the gate FAILED"
    out.append(f"  files    {files}")
    d = doc["drift"]
    allowed = f", {d['allowed']} allowed" if d["allowed"] is not None else ", none declared"
    out.append(f"  drift    {d['values']} value{'s' if d['values'] != 1 else ''} said by hand twice with no source{allowed}")
    ladders = doc["launch"]["ladders"]
    if not ladders:
        out.append("  launch   no ladders")
    for lad in ladders:
        short = sum(1 for t in lad["things"] if not t["known"] or not all(r["held"] for r in t["now"]))
        state = (f"{short} lack{'s' if short == 1 else ''} what {'its stage needs' if short == 1 else 'their stages need'}"
                 if short else "each at a stage it has everything for")
        out.append(f"  launch   {lad['name']}: {len(lad['things'])} thing{'s' if len(lad['things']) != 1 else ''}, {state}")
    return out


def main(args):
    usage = "usage: wherefore status [--gate] [--json] [--out PATH]"
    gate, as_json, out = False, False, None
    rest = list(args)
    while rest:
        a = rest.pop(0)
        if a in ("-h", "--help"):
            print(usage)
            return 0
        if a == "--gate":
            gate = True
        elif a == "--json":
            as_json = True
        elif a == "--out" and rest:
            out = pathlib.Path(rest.pop(0))
        else:
            print(usage)
            return 2
    from . import config as cfgmod
    try:
        root = cfgmod.find_root()
    except cfgmod.ConfigError:
        root = pathlib.Path.cwd()
    doc = find(root, gate=gate)
    text = json.dumps(doc, indent=1, ensure_ascii=False) + "\n"
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    if as_json:
        sys.stdout.write(text)
    else:
        print("\n".join(lines(doc)))
        if out:
            print(f"\nwrote {out}")
    judged = doc.get("files", {}).get("gate")
    return 1 if doc.get("invalid") or (judged and not judged["passed"]) else 0
