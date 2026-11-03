"""wherefore.json: the one file a client writes to say what its corpus is.

THE ROOT IS WHERE THIS FILE IS. Nothing in the engine works out a repository's
root from where the engine's own code happens to be installed - the repository
this was extracted from did that ninety-seven times, `Path(__file__).parents[1]`,
and it was right only because every script lived one directory below the root.
`WHEREFORE_ROOT` overrides the search, for a runner that already knows.

A REASON IS DATA, NOT A COMMENT. Every list entry that excuses something - a
script that writes but is not a generator, a generator the probe skips, a file
compared by something looser than its bytes - carries a `why`, and this module
refuses the file when one is missing. An exemption is a justification, not a
silence, and the difference has to be something a machine can check, which is
why this is JSON and not a format whose reasons would be comments.

ANY SECTION MAY LIVE IN ITS OWN FILE. A string where an object is expected is a
path, relative to the root, and the section is read from there - and written
back there, with that file's own formatting, by the one command that writes
configuration (`wherefore gate --restamp`). So a client that already keeps its
inventory in checks/inventory.json points at it, and nothing moves.

OR THE CLIENT CONFIGURES THE ENGINE IN PYTHON, AND SAYS WHERE. A corpus that
was a corpus before it was a client - the one this was extracted from - keeps
its generator list, its comparators and its exemptions in the scripts its
proofs plant faults into, by path, and each script hands them to the engine
itself. Copying those lists in here would be the same fact in two places, which
is the first thing this engine exists to refuse. So `entry` names, for each
command, the client's own script that runs it, and the command runs that script
exactly as the client's CI does: the same verdict, in the same words. A command
handed over may not ALSO be configured here; that is the same thing said twice.
"""
import json
import os
import pathlib

NAME = "wherefore.json"
SCHEMA = 1

# The sections that may be includes. Others are always inline.
INCLUDABLE = ("inventory", "surfaces", "retired", "reach", "claims", "compare")

GEN_FIELDS = ("script", "cwd", "makes", "stdout_to", "probe", "resettle", "why")

# The commands `entry` may hand to a client's script, and the sections each one
# would otherwise be configured from. A command handed over and configured here
# as well is refused: it would say one thing twice, and the two would drift.
ENTRY = {
    "list": ("generators", "not_a_generator"),
    "build": ("generators", "not_a_generator"),
    "gate": ("generators", "not_a_generator", "inventory", "compare"),
    "check retired": ("retired",),
    "check reach": ("reach",),
    "check claims": ("claims",),
}


class ConfigError(SystemExit):
    """wherefore.json says something the engine will not guess about."""

    def __init__(self, msg):
        super().__init__(f"::error::{NAME}: {msg}")


def find_root(start=None):
    """The directory holding wherefore.json, searching upward from `start`."""
    env = os.environ.get("WHEREFORE_ROOT")
    if env:
        root = pathlib.Path(env).resolve()
        if not (root / NAME).is_file():
            raise ConfigError(f"WHEREFORE_ROOT is {root}, and there is no {NAME} there")
        return root
    here = pathlib.Path(start or os.getcwd()).resolve()
    for d in (here, *here.parents):
        if (d / NAME).is_file():
            return d
    raise ConfigError(f"no {NAME} in {here} or above it. `wherefore init` writes one")


class Config:
    """The parsed file, with includes resolved and every reason present."""

    def __init__(self, root, doc):
        self.root = pathlib.Path(root).resolve()
        self.doc = doc
        self.included = {}           # section -> the file it came from
        for key in INCLUDABLE:
            v = doc.get(key)
            if isinstance(v, str):
                path = self.root / v
                if not path.is_file():
                    raise ConfigError(f"`{key}` names {v}, which does not exist")
                self.included[key] = v
                doc[key] = json.loads(path.read_text(encoding="utf-8"))
        validate(self)

    # ── the parts every module needs ────────────────────────────────────────
    @property
    def name(self):
        return self.doc.get("name", self.root.name)

    @property
    def env_prefix(self):
        return self.doc.get("observer", {}).get("env_prefix", "WHEREFORE_")

    @property
    def observer_dir(self):
        """The directory put on PYTHONPATH: the client's own, or the engine's."""
        d = self.doc.get("observer", {}).get("dir")
        if d:
            return self.root / d
        return pathlib.Path(__file__).resolve().parent / "_observe"

    @property
    def temp_prefix(self):
        return self.doc.get("temp_prefix", "wherefore-")

    @property
    def generators(self):
        from .generators import Gen
        return [Gen(*(g.get(f, d) for f, d in zip(GEN_FIELDS[:6], (None, None, None, None, True, True))))
                for g in self.doc.get("generators", [])]

    @property
    def not_a_generator(self):
        return dict(self.doc.get("not_a_generator", {}))

    def where(self, section):
        """The file a section lives in, as a reader would name it."""
        return self.included.get(section, NAME)

    def entry(self, command):
        """[script, args...] the client runs `command` with, or None for the engine's own."""
        target = self.doc.get("entry", {}).get(command)
        if target is None:
            return None
        return [target] if isinstance(target, str) else list(target)

    def source(self, name=None):
        """(name, declaration) of a source; the first declared is the primary."""
        sources = self.doc.get("sources", {})
        if not sources:
            raise ConfigError("declares no `sources`. A corpus is generated FROM something")
        if name is None:
            name = next(iter(sources))
        if name not in sources:
            raise ConfigError(f"no source called {name!r}; there is {', '.join(map(repr, sources))}")
        return name, sources[name]

    # ── writing back: the one place configuration is written ────────────────
    def write_section(self, section, value):
        if section in self.included:
            path = self.root / self.included[section]
        else:
            path = self.root / NAME
            raw = json.loads(path.read_text(encoding="utf-8"))
            raw[section] = value
            value = raw
        # indent=1, which is how the files this was extracted from are written;
        # 2 re-indented all of them.
        path.write_text(json.dumps(value, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        return path


def load(root=None):
    root = pathlib.Path(root).resolve() if root else find_root()
    path = root / NAME
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigError(f"no {NAME} in {root}")
    except json.JSONDecodeError as e:
        raise ConfigError(f"is not JSON: {e}")
    return Config(root, doc)


def _why(value, where):
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{where} carries no reason. An exemption is a justification, "
                          f"not a silence: say why, in `why`")


def validate(cfg):
    """Refuse what cannot be meant, before anything runs."""
    d = cfg.doc
    if d.get("wherefore") != SCHEMA:
        raise ConfigError(f"`wherefore` must be {SCHEMA}, the schema this engine reads; "
                          f"it is {d.get('wherefore')!r}")
    for name, src in d.get("sources", {}).items():
        if not isinstance(src, dict) or "path" not in src:
            raise ConfigError(f"source {name!r} has no `path`")
        if src.get("adapter", "leaves") not in ("leaves", "params"):
            raise ConfigError(f"source {name!r}: adapter {src.get('adapter')!r} is not "
                              f"one this engine has (leaves, params)")
    seen = set()
    for i, g in enumerate(d.get("generators", [])):
        where = f"generators[{i}]"
        if "command" in g:
            raise ConfigError(f"{where} says `command`, which is reserved: v1 runs Python "
                              f"generators only, by `script`, because what it observes is "
                              f"Python's open(). A generator it cannot see would be a "
                              f"generator whose files nobody covers")
        unknown = set(g) - set(GEN_FIELDS)
        if unknown:
            raise ConfigError(f"{where} has {', '.join(sorted(unknown))}, which no generator has")
        for f in ("script", "cwd", "makes"):
            if not isinstance(g.get(f), str) or not g[f]:
                raise ConfigError(f"{where} needs `{f}`")
        key = (g["cwd"], g["script"])
        if key in seen:
            raise ConfigError(f"{where}: {g['cwd']}/{g['script']} is listed twice")
        seen.add(key)
        if g.get("probe") is False or g.get("resettle") is False:
            _why(g.get("why"), f"{where} ({g['script']}) is left out of the probe or the "
                               f"second pass, and")
    for path, why in d.get("not_a_generator", {}).items():
        _why(why, f"not_a_generator {path!r}")
    for i, c in enumerate(d.get("compare", [])):
        if not isinstance(c, dict) or "glob" not in c or "as" not in c:
            raise ConfigError(f"compare[{i}] needs `glob` and `as`")
        _why(c.get("why"), f"compare[{i}] ({c['as']} for {c['glob']}) is looser than bytes, and")
    inv = d.get("inventory")
    if inv is not None:
        rules = inv.get("authored", {}).get("rules", [])
        for i, rule in enumerate(rules):
            if not isinstance(rule, list) or len(rule) < 2:
                raise ConfigError(f"authored rule {i} in {cfg.where('inventory')} is not "
                                  f"[pattern, why] or [pattern, why, [exceptions]]")
            _why(rule[1], f"authored rule {rule[0]!r} in {cfg.where('inventory')}")
        for name, grp in inv.get("captured", {}).get("groups", {}).items():
            where = f"captured group {name!r} in {cfg.where('inventory')}"
            _why(grp.get("why"), where)
            files = grp.get("files")
            if not (isinstance(files, list) and files and all(isinstance(f, str) and f for f in files)):
                raise ConfigError(f"{where} needs `files`: the globs of what it captured")
            # WHAT IT WAS MADE FROM, OR WHY NOTHING. A group with neither stamped
            # to the hash of nothing and passed for ever - a third answer beside
            # the two the gate means to accept.
            made_from = grp.get("shot_from") or grp.get("spec_values")
            if grp.get("no_stamp"):
                if made_from:
                    raise ConfigError(f"{where} says what it was made from and `no_stamp` "
                                      f"too: it is one or the other")
                _why(grp["no_stamp"], f"{where} says `no_stamp`, and")
            elif not made_from:
                raise ConfigError(f"{where} says neither what it was made from "
                                  f"(`shot_from`, `spec_values`) nor why there is nothing "
                                  f"(`no_stamp`, with the reason). A stamp over nothing "
                                  f"would pass for ever")
            if grp.get("spec_values") and not d.get("sources"):
                raise ConfigError(f"{where} reads `spec_values`, and no source is declared "
                                  f"to read them from")
    entry = d.get("entry")
    if entry is not None:
        if not isinstance(entry, dict):
            raise ConfigError("`entry` must be an object: each command, and the script "
                              "that runs it")
        _why(entry.get("why"), "`entry`, which hands commands to the client's own scripts,")
        for cmd, target in entry.items():
            if cmd == "why":
                continue
            if cmd not in ENTRY:
                raise ConfigError(f"`entry` names {cmd!r}, which is not a command it can "
                                  f"hand over: {', '.join(ENTRY)}")
            argv = [target] if isinstance(target, str) else target
            if not (isinstance(argv, list) and argv
                    and all(isinstance(a, str) and a for a in argv)):
                raise ConfigError(f"entry {cmd!r} must be a script, or a list of a script "
                                  f"and the arguments it always takes")
            if not (cfg.root / argv[0]).is_file():
                raise ConfigError(f"entry {cmd!r} names {argv[0]}, which does not exist")
            for section in ENTRY[cmd]:
                if d.get(section):
                    raise ConfigError(
                        f"entry {cmd!r} hands the command to {argv[0]}, and `{section}` "
                        f"is declared here too. That is the same thing said in two "
                        f"places, and they will drift: say it in one")


SKILL_GENERATOR = {
    "script": "-m wherefore.skill",
    "cwd": ".",
    "makes": ".claude/skills/wherefore/ and .agents/skills/wherefore/, the skill the pinned "
             "release ships, where Claude Code and Codex read it",
}


def starter(name):
    """What `wherefore init` writes: a corpus that declares nothing yet but the
    skill its agents read.

    Run the gate on it and every tracked file but this one fails as
    unclassified, which is the right first instruction: decide what each file
    is, and write the reason down. The one generator writes the skill from the
    installed engine (wherefore.skill), so the skill an agent reads here is
    always the release's, and the gate says when it is not.
    """
    return {
        "wherefore": SCHEMA,
        "name": name,
        "sources": {},
        "generators": [dict(SKILL_GENERATOR)],
        "not_a_generator": {},
        "inventory": {
            "note": "Every tracked file is generated, authored or captured. GENERATED is "
                    "derived by running the generators; this declares the rest.",
            "authored": {"rules": [
                [NAME, "this file: what the corpus is, and why each exemption exists"],
            ]},
            "captured": {"groups": {}},
        },
    }
