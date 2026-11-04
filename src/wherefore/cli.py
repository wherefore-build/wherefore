"""wherefore - the command line.

The commands, and what each does, are said once, in commands.json beside this
file; `wherefore --help` prints them from there, and so does the README.

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
    if len(args) > 1 or (args and args[0].startswith("-")):
        if args[0] in ("-h", "--help"):
            print("usage: wherefore init [DIR]")
            return 0
        print(f"::error::wherefore init takes one directory, at most: {' '.join(args)}")
        return 2
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
    from . import skill
    skill.write(target)
    places = " and ".join(f"{p}/ ({agent})" for agent, p in skill.INTO.items())
    print(f"wrote {path}\nwrote {places}: the skill a coding agent here "
          f"reads\n\nCommit them. Then ask your agent to set up Wherefore: the skill's "
          f"start.md is how.\nFrom the first build on, the skill is regenerated from the "
          f"release this repository pins.\n\n`wherefore gate` names every tracked file "
          f"nobody has accounted for, and each one is a decision:\ngenerated, authored or "
          f"captured - with the reason written down.\n\nThen every place the product is "
          f"described - a site, the docs, another repository - pins\nthe one that decides "
          f"it, and fails its build on a feature it does not say: start.md, \"Every surface\".")
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


def _takes_nothing(name, args):
    """An exit code for arguments a command does not take, or None.

    Refused rather than ignored: a flag nobody reads is a flag somebody thinks
    did something.
    """
    if not args:
        return None
    rows = [c["usage"] for c in commands() if c["usage"].split()[1:2] == [name]]
    if any(a in ("-h", "--help") for a in args):
        print("usage: " + "\n       ".join(rows))
        return 0
    print(f"::error::wherefore {name} takes no arguments: {' '.join(args)}")
    return 2


def _list(args):
    r = _handed_over(cfgmod.load(), "list", args)
    if r is not None:
        return r
    r = _takes_nothing("list", args)
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
    r = _takes_nothing("build", args)
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
        if not scripts:
            # "0/0 proofs held" passed, so a mistyped glob turned a CI step green.
            print(f"::error::the `proofs` glob {pattern!r} matches no file. A proof step "
                  f"that runs nothing proves nothing")
            return 1
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


# The checks `wherefore check` runs, in the order commands.json lists them.
CHECKS = ("retired", "reach", "claims", "upstream")


def _check(args):
    if not args:
        print(f"::error::wherefore check NAME, where NAME is {', '.join(CHECKS)}")
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
    if name == "upstream":
        from . import upstream
        return upstream.main(cfg, rest)
    print(f"::error::no check called {name!r}: {', '.join(CHECKS)}")
    return 1


def _graph(args):
    from . import graph
    return graph.main(cfgmod.load(), args)


def _hook(args):
    from . import hook
    return hook.main(cfgmod.load(), args)


def _scan(args):
    # NO wherefore.json: the scan is the first win, before there is a corpus.
    from . import scan
    return scan.main(args)


COMMANDS = {"init": _init, "list": _list, "build": _build, "gate": _gate,
            "graph": _graph, "prove": _prove, "check": _check, "hook": _hook,
            "scan": _scan}


def commands():
    """The commands as commands.json says them: [{usage, does}]."""
    import json
    path = pathlib.Path(__file__).resolve().parent / "commands.json"
    return json.loads(path.read_text(encoding="utf-8"))["commands"]


def usage():
    rows = commands()
    width = max(len(c["usage"]) for c in rows) + 2
    listing = "\n".join(f"  {c['usage']:<{width}}{c['does']}" for c in rows)
    return __doc__.replace("\n\nThe commands, and what each does,",
                           "\n\n" + listing + "\n\nThe commands, and what each does,", 1)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(usage())
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
