"""wherefore - the command line.

  wherefore init [DIR]            write a wherefore.json that declares nothing yet
  wherefore list                  run every generator once; say what each wrote
  wherefore build                 the roll: every generator, twice, compared with
                                  what is committed, and the results LEFT in place
  wherefore gate [--keep]         the coverage gate; puts the tree back unless --keep
  wherefore gate --restamp GROUP  record a re-made capture against its sources
  wherefore prove [SCRIPT ...]    run the proofs, one at a time, in place
  wherefore check NAME            retired | reach | claims
  wherefore hook install          a pre-push hook: no push leaves the corpus stale

Every command finds its client by looking for wherefore.json in the working
directory and above it, or in WHEREFORE_ROOT.

A client that configures the engine in Python names the script that runs each
command in `entry`, and the command runs that script, with what was typed after
it, exactly as the client's own CI runs it.
"""
import os
import pathlib
import subprocess
import sys

from . import __version__
from . import config as cfgmod


def _init(args):
    target = pathlib.Path(args[0] if args else ".").resolve()
    path = target / cfgmod.NAME
    if path.exists():
        print(f"::error::{path} already exists. init writes a corpus that declares "
              f"nothing; it does not overwrite one that declares something.")
        return 1
    target.mkdir(parents=True, exist_ok=True)
    import json
    path.write_text(json.dumps(cfgmod.starter(target.name), indent=1,
                               ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {path}\n\nNext: declare your sources and generators, then run "
          f"`wherefore gate`.\nEvery tracked file it cannot classify it will name, "
          f"and each one is a decision:\ngenerated, authored or captured - with the "
          f"reason written down.")
    return 0


def _handed_over(cfg, command, args):
    """Run the client's own script for `command`, if `entry` names one; else None."""
    argv = cfg.entry(command)
    if argv is None:
        return None
    env = dict(os.environ, WHEREFORE_ROOT=str(cfg.root))
    return subprocess.run([sys.executable, *argv, *args], cwd=cfg.root, env=env).returncode


def _configured():
    cfg = cfgmod.load()
    from . import gate, generators
    gate.configure_from(cfg)
    return cfg, generators, gate


def _list(args):
    r = _handed_over(cfgmod.load(), "list", args)
    if r is not None:
        return r
    _cfg, G, _gate = _configured()
    saved = sys.argv
    try:
        sys.argv = ["wherefore"]
        return G.main()
    finally:
        sys.argv = saved


def _build(args):
    r = _handed_over(cfgmod.load(), "build", args)
    if r is not None:
        return r
    _cfg, G, _gate = _configured()
    return G.roll()


def _gate(args):
    r = _handed_over(cfgmod.load(), "gate", args)
    if r is not None:
        return r
    _cfg, _G, gate = _configured()
    return gate.main(["wherefore", *args])


def _prove(args):
    cfg = cfgmod.load()
    if args:
        scripts = [pathlib.Path(a) for a in args]
    else:
        pattern = cfg.doc.get("proofs", {}).get("glob")
        if not pattern:
            print("::error::wherefore.json declares no `proofs` glob, and none were named")
            return 1
        scripts = sorted(p.relative_to(cfg.root) for p in cfg.root.glob(pattern))
    env = dict(os.environ, WHEREFORE_ROOT=str(cfg.root))
    # ONE AT A TIME, IN PLACE. A proof plants its fault in the working tree and
    # puts it back; two at once in one checkout plant into each other's tree.
    # Parallelism is one checkout per proof, which is a CI's job, not this one's.
    failed = []
    for s in scripts:
        print(f"\n== {s}")
        r = subprocess.run([sys.executable, str(s)], cwd=cfg.root, env=env)
        if r.returncode:
            failed.append(str(s))
    print(f"\n{len(scripts) - len(failed)}/{len(scripts)} proofs held")
    for f in failed:
        print(f"::error::{f} did not hold")
    return 1 if failed else 0


def _check(args):
    if not args:
        print("::error::wherefore check NAME, where NAME is retired, reach or claims")
        return 1
    name, rest = args[0], args[1:]
    cfg = cfgmod.load()
    r = _handed_over(cfg, f"check {name}", rest)
    if r is not None:
        return r
    if name == "retired":
        from . import retired
        return retired.main(cfg, rest)
    if name == "reach":
        from . import reach
        reach.configure_from(cfg)
        return reach.main(["wherefore", *rest]) or 0
    if name == "claims":
        from . import claims
        return claims.main(cfg, rest)
    print(f"::error::no check called {name!r}: retired, reach or claims")
    return 1


def _hook(args):
    from . import hook
    return hook.main(cfgmod.load(), args)


COMMANDS = {"init": _init, "list": _list, "build": _build, "gate": _gate,
            "prove": _prove, "check": _check, "hook": _hook}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    if argv[0] == "--version":
        print(f"wherefore {__version__}")
        return 0
    cmd = COMMANDS.get(argv[0])
    if cmd is None:
        print(f"::error::no command {argv[0]!r}. `wherefore --help` lists them.")
        return 2
    try:
        return cmd(argv[1:])
    except cfgmod.ConfigError as e:
        print(e.code)
        return 1
