import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from lib import SRC, DST
s = (SRC / "checks/coverage_gate.py").read_text(encoding="utf-8")
orig = s

def once(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)

def cut(start, end, new):
    global s
    assert s.count(start) == 1, start[:60]
    i = s.index(start); j = s.index(end, i)
    s = s[:i] + new + s[j:]

once('"""Every tracked file is accounted for, and every generated one was really written.\n',
 '"""Every tracked file is accounted for, and every generated one was really written.\n'
 '\n'
 'IN WHEREFORE. Moved from chaotic-pendulums-co\'s checks/coverage_gate.py, its\n'
 'docstring and comments kept: the bugs it names are that repository\'s, and they\n'
 'are why each line is here. What changed is whose corpus it is. ROOT, the\n'
 'inventory, the source a capture\'s `spec_values` are read from, and how a\n'
 'message names the inventory and this command are set by configure(). "Is this\n'
 'file what was committed?" is compare.py\'s, which holds the exceptions to\n'
 'byte-identity a client declares in wherefore.json `compare`, each with its\n'
 'reason - the thresholds, and the measurements that set them, stay with the\n'
 'client whose renderers they were measured on. A file the client compares by\n'
 'its cells is the one the second pass ignores, as .xlsx was here.\n')
once('sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))\nimport generators as G\n',
     'from . import compare as _C\nfrom . import generators as G\nfrom . import sources as _S\n')
once('ROOT = G.ROOT\nDECL = ROOT / "checks/inventory.json"\nSPEC = "spec/mk3.params.json"\n',
 '# The client\'s, set by configure(). See the module docstring.\n'
 'ROOT = None\n'
 'DECL = None             # () -> the inventory, read fresh\n'
 'WRITE_DECL = None       # (inventory) -> the path it was written to\n'
 'DECL_NAME = "wherefore.json"\n'
 'SPEC = None             # repo-relative path of the source spec_values read\n'
 'ADAPTER = "leaves"\n'
 'COMPARE = _C.Comparators()\n'
 'COMMAND = "wherefore gate"\n'
 'RESETTLE_HINT = ("A generator reads a file that a later one writes, so it\\n"\n'
 '                 "           lands one pass late.")\n'
 '\n'
 '\n'
 'def configure(root, decl, write_decl, decl_name, spec, adapter, comparators,\n'
 '              command=None, resettle_hint=None):\n'
 '    """Say whose corpus this is. configure generators.py first: this runs them."""\n'
 '    global ROOT, DECL, WRITE_DECL, DECL_NAME, SPEC, ADAPTER, COMPARE, COMMAND, RESETTLE_HINT\n'
 '    ROOT = pathlib.Path(root).resolve()\n'
 '    DECL, WRITE_DECL, DECL_NAME = decl, write_decl, decl_name\n'
 '    SPEC, ADAPTER, COMPARE = spec, adapter, comparators\n'
 '    if command is not None:\n'
 '        COMMAND = command\n'
 '    if resettle_hint is not None:\n'
 '        RESETTLE_HINT = resettle_hint\n'
 '\n'
 '\n'
 'def configure_from(cfg):\n'
 '    """configure() this module and the runner from a loaded wherefore.json."""\n'
 '    import json as _json\n'
 '    G.configure_from(cfg)\n'
 '    _name, src = cfg.source()\n'
 '    msg = cfg.doc.get("messages", {})\n'
 '    if "inventory" in cfg.included:\n'
 '        path = cfg.root / cfg.included["inventory"]\n'
 '        decl = lambda: _json.loads(path.read_text(encoding="utf-8"))\n'
 '    else:\n'
 '        decl = lambda: _json.loads((cfg.root / "wherefore.json").read_text(\n'
 '            encoding="utf-8")).get("inventory", {})\n'
 '    configure(cfg.root, decl, lambda d: cfg.write_section("inventory", d),\n'
 '              cfg.where("inventory"), src["path"], src.get("adapter", "leaves"),\n'
 '              _C.Comparators(cfg.doc.get("compare", [])),\n'
 '              msg.get("gate_command"), msg.get("resettle_hint"))\n')
# The thresholds, their measurements, the picture functions and same(): the
# functions move to compare.py, the numbers stay with the client.
cut("# The thirteen stills come out of a WebGL canvas", "def first_difference(",
 'MEASURED = _C.MEASURED\n'
 '\n'
 '\n'
 'def same(was, now):\n'
 '    """Is this file what was committed? compare.py says, by the client\'s rules."""\n'
 '    rel = str(now.resolve()).replace(str(ROOT) + "/", "")\n'
 '    return COMPARE.same(was, now, rel)\n'
 '\n'
 '\n')
once('''    """One parameter out of the spec, by its family.group.name path."""
    family, group, name = dotted.split(".")
    p = spec[family][group]["params"][name]
    return p.get("nominal", p.get("value"))''',
 '''    """One parameter out of the spec, by its family.group.name path - or, for a
    source read by the `leaves` adapter, by its dotted path. See sources.py."""
    return _S.value(spec, dotted, ADAPTER)''')
once('''    return (pathlib.PurePosixPath(rel).suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
            and any(rel.startswith(d) for d in RASTERISED))''',
 '''    return COMPARE.is_raster(rel)''')
once('''    DECL.write_text(json.dumps(decl, indent=1, ensure_ascii=False) + "\\n",
                    encoding="utf-8")
    print(f"\\nwrote {DECL.relative_to(ROOT)}. Commit it with the re-shot files, "''',
 '''    written = WRITE_DECL(decl)
    print(f"\\nwrote {pathlib.Path(written).relative_to(ROOT)}. Commit it with the re-shot files, "''')
once('def main():\n    keep = "--keep" in sys.argv\n    doing_restamp = "--restamp" in sys.argv\n',
     'def main(argv=None):\n    argv = sys.argv if argv is None else argv\n'
     '    keep = "--keep" in argv\n    doing_restamp = "--restamp" in argv\n')
once('    decl = json.loads(DECL.read_text(encoding="utf-8"))\n', '    decl = DECL()\n')
once('            i = sys.argv.index("--restamp")\n            only = sys.argv[i + 1] if len(sys.argv) > i + 1 else None\n',
     '            i = argv.index("--restamp")\n            only = argv[i + 1] if len(argv) > i + 1 else None\n')
once('tempfile.mkdtemp(prefix="cp-gate-")', 'tempfile.mkdtemp(prefix=f"{G.TEMP_PREFIX}gate-")')
once('declared a source in checks/inventory.json")', 'declared a source in {DECL_NAME}")')
once('f"and checks/inventory.json needs\\n           the rule that "', 'f"and {DECL_NAME} needs\\n           the rule that "')
once('and pathlib.Path(rel).suffix != ".xlsx")', 'and COMPARE.rule_for(rel)[0] != "xlsx-cells")')
once('extra = "".join(f"\\n           {w}" for w in picture_faults(d))',
     'extra = "".join(f"\\n           {w}" for w in _C.picture_faults(\n'
     '                    d, **COMPARE.picture_tolerances(rel)))')
once('''            worst = max(d[0] for d in seen.values())
            toned = max(d[2] for d in seen.values())
            print(f"       {len(seen)} rasterised file(s) compared as pictures, "
                  f"not bytes — worst edge {worst:.4f} of {EDGE_TOL:g} allowed, "
                  f"worst tone {toned:.1f} of {TONE_TOL:g}")''',
 '''            # Each against its own rule's tolerances; a client with one rule
            # for every picture reads exactly what it read before.
            tol = {r: COMPARE.picture_tolerances(r) for r in seen}
            we = max(seen, key=lambda r: seen[r][0])
            wt = max(seen, key=lambda r: seen[r][2])
            worst, toned = seen[we][0], seen[wt][2]
            print(f"       {len(seen)} rasterised file(s) compared as pictures, "
                  f"not bytes — worst edge {worst:.4f} of {tol[we]['edge_tol']:g} allowed, "
                  f"worst tone {toned:.1f} of {tol[wt]['tone_tol']:g}")''')
once('kv[1][0] / EDGE_TOL, kv[1][2] / TONE_TOL))[:6]:',
     'kv[1][0] / tol[kv[0]]["edge_tol"], kv[1][2] / tol[kv[0]]["tone_tol"]))[:6]:')
once('''                f"pass does not settle them. This is the manifest cycle -\\n"
                f"           spec/build_manifest.py writes spec/manifest.json "
                f"and the drawn views read it,\\n           and it runs after "
                f"them. Regenerate a second time and commit that. First "''',
 '''                f"pass does not settle them. {RESETTLE_HINT}"
                f" Regenerate a second time and commit that. First "''')
once('''                + f"           Then: python3 checks/coverage_gate.py "
                  f"--restamp {name!r}")''',
 '''                + f"           Then: {COMMAND} "
                  f"--restamp {name!r}")''')
(DST / "gate.py").write_text(s, encoding="utf-8")
print("gate.py: built from checks/coverage_gate.py")
