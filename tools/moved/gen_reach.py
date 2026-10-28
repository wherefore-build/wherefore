import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import lib
SRC = lib.SRC / "checks/spec_reaches_the_shop.py"
DST = lib.DST / "reach.py"
s = SRC.read_text(encoding="utf-8")

def once(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)

def cut(start, end, new):
    global s
    assert s.count(start) == 1, start[:60]
    i = s.index(start); j = s.index(end, i)
    s = s[:i] + new + s[j:]

once('"""Change the spec, and the files a supplier receives must change.\n',
 '"""Change the spec, and the files a supplier receives must change.\n'
 '\n'
 'IN WHEREFORE. Moved from chaotic-pendulums-co\'s checks/spec_reaches_the_shop.py,\n'
 'its words kept. What it watches, which facts it moves and by how much, what is\n'
 'exempt and which facts must move which files are the client\'s now, in\n'
 'wherefore.json `reach`. A source read by the `params` adapter is swept as\n'
 'the pendulum\'s spec always was - every nominal, value and band in the named\n'
 'families, sized in the object\'s unit - and one read by `leaves` has every\n'
 'scalar moved: a number by a nudge big enough to show, a string by a marker\n'
 'appended, because a company whose facts are a name and a price has facts too.\n'
 'A comparison is the gate\'s, by the client\'s declared rules, so a workbook is\n'
 'its cells and a solid its numbers here exactly as there.\n')
once("Usage:  python3 checks/spec_reaches_the_shop.py\n        python3 checks/spec_reaches_the_shop.py --only PATTERN [PATTERN ...]\n",
     "Usage:  wherefore check reach\n        wherefore check reach --only PATTERN [PATTERN ...]\n")
cut("sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))\nimport generators as G\n",
    "# EVERY numeric parameter is probed",
 'from . import compare as _C\n'
 'from . import generators as G\n'
 'from . import sources as _Src\n'
 '\n'
 '# The client\'s, set by configure(). See the module docstring.\n'
 'ROOT = None\n'
 'SPEC = None             # the source the probe moves, as a path\n'
 'WATCHED = []            # [(path, the name a message gives it)]\n'
 'EXCLUDE = []            # substrings of a path that is never watched\n'
 'COMPARE = _C.Comparators()\n'
 'AUDIENCE = "a reader"\n'
 'SUCCESS = "every fact probed reaches something {audience} receives"\n'
 '\n'
 '\n')
cut("EXEMPT = {\n", "\n\n# Parameters PROVEN to reach nothing", "EXEMPT = {}\n")
cut("UNCONSUMED = {\n", "\n\n# (what it is, where it lives", "UNCONSUMED = {}\n")
cut("def _solids(*parts):\n", "\n\ndef watched():",
 "PROBES = []             # [(name, path, what it must reach, [files])]\n")
once('''    out = {}
    for d in SHIPPED:
        for f in sorted(d.rglob("*")):
            if f.is_file() and "-stills" not in str(f) and "/renders/" not in str(f):
                out[str(f.relative_to(ROOT))] = f
    return out''',
'''    out = {}
    for d, alias in WATCHED:
        if d.is_file():
            out[alias or str(d.relative_to(ROOT))] = d
            continue
        for f in sorted(d.rglob("*")):
            if f.is_file() and not any(x in str(f) for x in EXCLUDE):
                out[str(f.relative_to(ROOT))] = f
    return out''')
once('''        shutil.copy2(f, dst)
    (into / "bom.json").write_text(json.dumps(bom_cells()))''', '''        shutil.copy2(f, dst)''')
once('''    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import shipped_solids as SS
    out = []
    for rel, f in watched().items():
        was = against / rel
        if not was.exists():
            out.append(rel)
        elif f.suffix in (".step", ".dxf"):
            if not SS.same_solid(was, f):
                out.append(rel)
        elif was.read_bytes() != f.read_bytes():
            out.append(rel)
    was_cells = json.loads((against / "bom.json").read_text())
    if [tuple(x) for x in was_cells] != [tuple(x) for x in bom_cells()]:
        out.append("BOM.xlsx")
    return out''',
'''    out = []
    for rel, f in watched().items():
        was = against / rel
        if not was.exists():
            out.append(rel)
        elif not COMPARE.same(was, f, str(f.relative_to(ROOT))):
            out.append(rel)
    return out''')
once('tempfile.mkdtemp(prefix="cp-probe-")', 'tempfile.mkdtemp(prefix=f"{G.TEMP_PREFIX}probe-")')
once('''        env["CP_WRITE_LOG"] = str(log)\n''',
     '''        env[f"{G.ENV_PREFIX}WRITE_LOG"] = str(log)\n        env["WHEREFORE_ROOT"] = str(ROOT)\n''')
once("def nudge(doc, path, delta):\n", "def nudge_params(doc, path, delta):\n")
once('''def sweep():
    """Every numeric parameter in the spec, with a nudge big enough to show."""
    doc = json.loads(SPEC.read_text(encoding="utf-8"))''',
'''def sweep_params(doc, families, not_length):
    """Every numeric parameter in the spec, with a nudge big enough to show."""''')
once('    for family in ("hardware", "machined", "geometry", "mark", "tolerances"):\n',
     '    for family in families:\n')
once('                k = 1.0 if name in _S.NOT_LENGTH else u\n', '                k = 1.0 if name in not_length else u\n')
once("                                0.04 * (1.0 if name in _S.NOT_LENGTH else u)))\n",
     "                                0.04 * (1.0 if name in not_length else u)))\n")
once('''    return out


def main():''', '''    return out


MARKER = " (probe)"


def sweep_leaves(doc, include, exclude):
    """Every scalar a `leaves` source holds, by dotted path, that `include`
    names and `exclude` does not (fnmatch): a number, nudged, or a string,
    marked. A boolean has no nudge that means anything, and is not moved."""
    out = []
    for dotted, v in _Src.leaves(doc):
        if not any(fnmatch.fnmatchcase(dotted, p) for p in include):
            continue
        if any(fnmatch.fnmatchcase(dotted, p) for p in exclude):
            continue
        if isinstance(v, bool) or v is None:
            continue
        if isinstance(v, (int, float)):
            out.append((dotted, tuple(dotted.split(".")),
                        1 if isinstance(v, int) else max(abs(v) * 0.1, 0.1)))
        elif isinstance(v, str):
            out.append((dotted, tuple(dotted.split(".")), MARKER))
    return out


def nudge_leaves(doc, path, delta):
    """Move one scalar: a number by delta, a string by the marker."""
    node = doc
    for p in path[:-1]:
        node = node[int(p)] if isinstance(node, list) else node[p]
    key = int(path[-1]) if isinstance(node, list) else path[-1]
    was = node[key]
    if isinstance(was, str):
        node[key] = was + delta
        return repr(was), repr(node[key])
    node[key] = round(was + delta, 6) if isinstance(was, float) else was + delta
    return f"{was:g}", f"{node[key]:g}"


SWEEP = lambda: []                  # noqa: E731  () -> [(name, path, delta)]
NUDGE = nudge_leaves


def sweep():
    return SWEEP()


def nudge(doc, path, delta):
    return NUDGE(doc, path, delta)


def configure(root, spec, watched, exclude, comparators, sweep_fn, nudge_fn,
              exempt=None, unconsumed=None, probes=None, audience=None, success=None):
    """Say whose corpus this is. configure generators.py first: this runs them."""
    global ROOT, SPEC, WATCHED, EXCLUDE, COMPARE, SWEEP, NUDGE, AUDIENCE, SUCCESS
    ROOT = pathlib.Path(root).resolve()
    SPEC = ROOT / spec
    WATCHED = [(ROOT / p, alias) for p, alias in watched]
    EXCLUDE = list(exclude)
    COMPARE = comparators
    SWEEP, NUDGE = sweep_fn, nudge_fn
    EXEMPT.clear(); EXEMPT.update(exempt or {})
    UNCONSUMED.clear(); UNCONSUMED.update(unconsumed or {})
    PROBES[:] = list(probes or [])
    if audience:
        AUDIENCE = audience
    if success:
        SUCCESS = success


def configure_from(cfg):
    """configure() this module and the runner from wherefore.json `reach`."""
    G.configure_from(cfg)
    r = cfg.doc.get("reach") or {}
    facts = r.get("facts", {})
    name, src = cfg.source(facts.get("source"))
    adapter = src.get("adapter", "leaves")
    path = cfg.root / src["path"]
    if adapter == "params":
        nl = facts.get("not_length", [])
        if isinstance(nl, str):
            nl = _attr(cfg.root, nl)
        fams = facts.get("families", [])
        sweep_fn = lambda: sweep_params(json.loads(path.read_text(encoding="utf-8")), fams, nl)  # noqa: E731
        nudge_fn = nudge_params
    else:
        inc, exc = facts.get("include", ["*"]), facts.get("exclude", [])
        sweep_fn = lambda: sweep_leaves(json.loads(path.read_text(encoding="utf-8")), inc, exc)  # noqa: E731
        nudge_fn = nudge_leaves
    watched = [(w, None) if isinstance(w, str) else (w["path"], w.get("as")) for w in r.get("watched", [])]
    probes = [(p["name"], tuple(p["fact"].split(".")), p["reaches"], p["files"])
              for p in r.get("probes", [])]
    for k, why in {**r.get("exempt", {}), **r.get("unconsumed", {})}.items():
        if not str(why).strip():
            raise SystemExit(f"::error::reach: {k} is exempt with no reason. An exemption is "
                             f"a justification, not a silence")
    configure(cfg.root, src["path"], watched, r.get("exclude", []),
              _C.Comparators(cfg.doc.get("compare", [])), sweep_fn, nudge_fn,
              r.get("exempt"), r.get("unconsumed"), probes, r.get("audience"),
              cfg.doc.get("messages", {}).get("reach_ok"))


def _attr(root, ref):
    """`path/to/module.py:NAME` - a value the client keeps in code, by reference."""
    import importlib.util
    file, name = ref.rsplit(":", 1)
    spec = importlib.util.spec_from_file_location("_wherefore_ref", root / file)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str((root / file).parent))
    spec.loader.exec_module(mod)
    return getattr(mod, name)


def main(argv=None):''')
once('    only = sys.argv[sys.argv.index("--only") + 1:] if "--only" in sys.argv else None\n',
     '    argv = sys.argv if argv is None else argv\n'
     '    only = argv[argv.index("--only") + 1:] if "--only" in argv else None\n')
once("                if not refused or abs(attempt) <= abs(delta) / 8:\n",
     "                if not refused or not isinstance(delta, (int, float)) \\\n"
     "                        or abs(attempt) <= abs(delta) / 8:\n")
once('f"NOTHING a supplier receives changed. Either a "', 'f"NOTHING {AUDIENCE} receives changed. Either a "')
once('if __name__ == "__main__":\n    main()\n', 'if __name__ == "__main__":\n    sys.exit(main())\n')
once('    print("\\nevery number probed reaches the supplier files or the drawn brand")\n',
     '    print("\\n" + SUCCESS.format(audience=AUDIENCE))\n')
DST.write_text(s, encoding="utf-8")
print("reach.py: built from checks/spec_reaches_the_shop.py")
