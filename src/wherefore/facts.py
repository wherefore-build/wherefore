"""`wherefore facts`: a source backed by a store, and the file it is materialized into.

THE GENERATORS ARE THE CLIENT'S, AND THEY OPEN THE FILE. A client's generator
is its own script, and it reads its facts the plainest way there is:
`json.load(open("facts.json"))`. Nothing can stand between that call and a
store without changing every generator, so nothing does. A source backed by a
store keeps its `path`, and the engine MATERIALIZES the store into that file -
the same path, the same JSON shape a file source would have - and the build
and every check read the file as they always have. Design: docs/scale.md,
Stage 3.

THE FILE IS GENERATED, SO THE GATE HOLDS IT. The materializing is a generator
the corpus declares, `python -m wherefore.facts`, first in its list:

    {"script": "-m wherefore.facts", "cwd": ".", "probe": false,
     "makes": "facts.json, from the store",
     "why": "it writes the source the reach probe moves, so the probe must not run it"}

The gate runs it like any generator, so the file is generated - derived by
running it, never declared - and compared byte for byte with what is
committed. It writes the store's facts at the version wherefore.json pins
(`"store": {..., "version": N}`), so a file edited by hand differs from what
the store says there and the gate names it. It fails when the store has
moved past the pin: the store says something the corpus does not, until
someone pulls it and commits what moved. And the gate checks every source
that declares a `schema` on the bytes committed, so a value of the wrong type
is named by its identity whichever way it got there.

The probe must not run it - reach moves a fact in the file and requires the
generators to carry it, and this one would put the store's value straight
back - and config.py refuses a store-backed source without it, or with it
probed.

THE COMMANDS. The store is written only by these, each a new version with
who decided it; pull is how a corpus takes a version.

  wherefore facts import [FILE] [--source NAME] --decided-by WHO [--note WORDS]
      FILE (the source's own file by default) becomes the store's next
      version, whole: a fact it does not hold is removed.
  wherefore facts set KEY VALUE [--as TYPE] [--source NAME] --decided-by WHO [--note WORDS]
      one fact, a new version. VALUE is read as JSON - 95, true, null,
      "a string" - and as a string when it is not JSON; --as says which type
      is meant. A fact keeps its type unless --as says otherwise, and the
      store refuses a type the schema does not allow, naming the fact.
  wherefore facts pull [--source NAME]
      the store's newest version, written to the file, and pinned in
      wherefore.json: commit them together.
  wherefore facts log [KEY] [--source NAME]
      the versions, newest first, and who decided each; with KEY, that fact:
      what it is, who decided it, and every value it has had. A file source
      answers too: its versions are the commits that touched it.

OUT OF SCOPE, AND SAID: a store anywhere but this machine, any
authentication, a store standing in for git for anything but facts.
"""
import json
import pathlib
import sys

from . import model, sources

GENERATOR = "-m wherefore.facts"
PROTOCOLS = ("wherefore-store/1",)
STORE_FIELDS = ("protocol", "at", "run", "version", "indent")
USAGE = """usage: wherefore facts import [FILE] [--source NAME] --decided-by WHO [--note WORDS]
       wherefore facts set KEY VALUE [--as TYPE] [--source NAME] --decided-by WHO [--note WORDS]
       wherefore facts pull [--source NAME]
       wherefore facts log [KEY] [--source NAME]"""
SUBCOMMANDS = ("import", "set", "pull", "log")
SHOWN = 20


# ── wherefore.json ──────────────────────────────────────────────────────────

def validate(doc):
    """Refuse a `schema` or a `store` on a source that cannot be meant."""
    from .config import ConfigError
    backed = []
    for name, src in (doc.get("sources") or {}).items():
        where = f"source {name!r}"
        if "schema" in src:
            bad = model.schema_problem(src["schema"])
            if bad:
                raise ConfigError(f"{where}: `schema` {bad}")
        st = src.get("store")
        if st is None:
            continue
        if "schema" in src and src.get("adapter", "leaves") == "params":
            raise ConfigError(f"{where}: a store holds a source's facts as leaves, and the `params` adapter "
                              f"names them by parameter, so one `schema` cannot type both: type a store-backed "
                              f"source read as leaves, or keep a params source a file")
        if not isinstance(st, dict):
            raise ConfigError(f"{where}: `store` is an object - {{\"protocol\": \"wherefore-store/1\", "
                              f"\"at\": \"facts.db\"}} - saying which store the file is materialized from")
        unknown = set(st) - set(STORE_FIELDS)
        if unknown:
            raise ConfigError(f"{where}: `store` has {', '.join(sorted(unknown))}, which it does not take: "
                              f"{', '.join(STORE_FIELDS)}")
        if st.get("protocol") not in PROTOCOLS:
            raise ConfigError(f"{where}: `store.protocol` is {st.get('protocol')!r}; this engine speaks "
                              f"{', '.join(PROTOCOLS)}")
        if ("at" in st) == ("run" in st):
            raise ConfigError(f"{where}: `store` says `at` - the reference store's SQLite file - or `run`, "
                              f"the command of any store that speaks the protocol, and exactly one of them")
        if "at" in st:
            at = st["at"]
            if not (isinstance(at, str) and at.strip()) or pathlib.PurePath(at).is_absolute() \
                    or ".." in pathlib.PurePath(at).parts:
                raise ConfigError(f"{where}: `store.at` is a path inside the repository, and not {at!r}")
            if pathlib.PurePath(at) == pathlib.PurePath(src["path"]):
                raise ConfigError(f"{where}: `store.at` and `path` are the same file")
        if "run" in st:
            run = st["run"]
            if not (isinstance(run, list) and run and all(isinstance(w, str) and w for w in run)):
                raise ConfigError(f"{where}: `store.run` is a command as a list of its words, run with no "
                                  f"shell between, and not {run!r}")
        v = st.get("version")
        if v is not None and not (isinstance(v, int) and not isinstance(v, bool) and v >= 1):
            raise ConfigError(f"{where}: `store.version` is the version the file was pulled at - written by "
                              f"`wherefore facts pull` - and not {v!r}")
        ind = st.get("indent", 1)
        if not (isinstance(ind, int) and not isinstance(ind, bool) and 0 <= ind <= 8):
            raise ConfigError(f"{where}: `store.indent` is how the file is indented, 0 to 8, and not {ind!r}")
        backed.append(name)
    if not backed:
        return
    if any(c in (doc.get("entry") or {}) for c in ("gate", "build", "list")):
        return                  # the client's own scripts list its generators; the docs say what to add
    gens = [g for g in doc.get("generators", []) if isinstance(g, dict) and g.get("script") == GENERATOR]
    if not gens:
        raise ConfigError(
            f"source {backed[0]!r} is backed by a store, so its file is generated: declare the generator "
            f"that materializes it, first among the generators - {{\"script\": \"{GENERATOR}\", \"cwd\": \".\", "
            f"\"probe\": false, \"makes\": \"...\", \"why\": \"...\"}}")
    if gens[0].get("probe", True) is not False:
        raise ConfigError(f"the generator {GENERATOR} writes the source the reach probe moves, and would put "
                          f"the store's value straight back: it says \"probe\": false, with why")


def stored(cfg):
    """[(name, declaration)] of every source backed by a store."""
    return [(n, s) for n, s in (cfg.doc.get("sources") or {}).items() if s.get("store")]


def where(decl):
    st = decl["store"]
    return st.get("at") or " ".join(st["run"])


# ── the generator: python -m wherefore.facts ────────────────────────────────

def materialize(src, version):
    """(text, facts): the file `src` holds at `version`."""
    facts = src.facts(version)
    return model.render(model.compose(facts), src.store.get("indent", 1)), facts


def generate():
    """Write every store-backed source's file at its pinned version; exit 1 if
    any is not pinned, or its store has moved past the pin."""
    from . import config, store
    cfg = config.load()
    fails = []
    for name, decl in stored(cfg):
        with sources.Stored(cfg.root, name, decl) as src:
            pin = src.pinned
            try:
                head = src.head()
                if pin is None:
                    fails.append(f"{name}: {decl['path']} has never been pulled from its store "
                                 f"{where(decl)}: run `wherefore facts pull`, and commit what it writes")
                    continue
                if pin > head:
                    fails.append(f"{name}: wherefore.json pins version {pin}, and the store {where(decl)} holds "
                                 f"versions up to {head}: it is not the store the file was pulled from")
                    continue
                text, facts = materialize(src, pin)
            except (store.StoreError, model.ModelError) as e:
                fails.append(f"{name}: the store {where(decl)} could not be read: {e}")
                continue
        out = cfg.root / decl["path"]
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"{decl['path']}: {len(facts)} facts, version {pin} of {where(decl)}")
        if head != pin:
            fails.append(f"{name}: the store {where(decl)} is at version {head}, and {decl['path']} is pulled at "
                         f"version {pin}. The store says what the corpus does not: run `wherefore facts pull`, "
                         f"and commit what moved")
    for f in fails:
        print(f"::error::{f}", file=sys.stderr)
    return 1 if fails else 0


# ── the commands ────────────────────────────────────────────────────────────

def _parse(args, flags, positional):
    """({flag: value}, [positional]) or a message."""
    got, pos = {}, []
    i = 0
    while i < len(args):
        a = args[i]
        if a in flags:
            if i + 1 >= len(args):
                return f"{a} takes a value"
            if a in got:
                return f"{a} is given twice"
            got[a] = args[i + 1]
            i += 2
            continue
        if a.startswith("--"):
            return f"there is no {a} here"
        pos.append(a)
        i += 1
    if len(pos) > positional[1] or len(pos) < positional[0]:
        return "the wrong number of arguments"
    return got, pos


def _pick(cfg, name, store_only=True):
    """(name, declaration) of the source a command acts on, or an error string."""
    srcs = cfg.doc.get("sources") or {}
    if name is not None:
        if name not in srcs:
            return f"no source called {name!r}; there is {', '.join(map(repr, srcs)) or 'none'}"
        if store_only and not srcs[name].get("store"):
            return f"source {name!r} is a file, not backed by a store: its facts change where they are written"
        return name, srcs[name]
    backed = stored(cfg)
    if len(backed) == 1:
        return backed[0]
    if len(backed) > 1:
        return f"several sources are backed by a store ({', '.join(n for n, _ in backed)}): say which, --source NAME"
    if store_only:
        return ("no source is backed by a store. A source says so beside its path - "
                "\"store\": {\"protocol\": \"wherefore-store/1\", \"at\": \"facts.db\"} - see the configuration page")
    if not srcs:
        return "declares no `sources`"
    first = next(iter(srcs))
    return first, srcs[first]


def _show(value):
    return json.dumps(value, ensure_ascii=False)


def _decider(got):
    who = got.get("--decided-by")
    if not (who and who.strip()):
        return None
    return who.strip()


def _import(cfg, args):
    from . import store
    p = _parse(args, ("--source", "--decided-by", "--note"), (0, 1))
    if isinstance(p, str):
        return _usage(p)
    got, pos = p
    who = _decider(got)
    if who is None:
        return _usage("say who decided these facts: --decided-by WHO. A store records who decided every version")
    pick = _pick(cfg, got.get("--source"))
    if isinstance(pick, str):
        print(f"::error::{pick}")
        return 1
    name, decl = pick
    rel = pos[0] if pos else decl["path"]
    path = cfg.root / rel if not pathlib.Path(rel).is_absolute() else pathlib.Path(rel)
    try:
        raw = path.read_text(encoding="utf-8")
        facts = model.decompose(json.loads(raw), name)
    except FileNotFoundError:
        print(f"::error::{rel} does not exist")
        return 1
    except (ValueError, model.ModelError) as e:
        print(f"::error::{rel} cannot be imported: {e}")
        return 1
    wrong = [w for w in (model.wrong_type(f, decl.get("schema")) for f in facts) if w]
    if wrong:
        for w in wrong:
            print(f"::error::refused: {w}")
        return 1
    try:
        with sources.Stored(cfg.root, name, decl) as src:
            head = src.head()
            try:
                v = src.write(facts, who, got.get("--note", ""), replace=True, schema=decl.get("schema"),
                              base=head)["version"]
            except store.StoreError as e:
                if str(e).startswith("nothing to write"):
                    print(f"{name}: nothing to import - version {head} of {where(decl)} already holds every "
                          f"fact in {rel}")
                    return 0
                raise
            moved = src.changes(head, v)
    except store.StoreError as e:
        print(f"::error::{name}: {e}")
        return 1
    added = sum(1 for _k, a, b in moved if a is None)
    gone = sum(1 for _k, a, b in moved if b is None)
    print(f"{name}: {len(facts)} facts from {rel} are version {v} of {where(decl)}, decided by {who}")
    print(f"  {added} added, {len(moved) - added - gone} changed, {gone} removed since version {head}")
    if model.render(model.compose(facts), decl["store"].get("indent", 1)) != raw:
        print(f"  {rel} is not written the way a pull writes it (JSON, indent {decl['store'].get('indent', 1)}): "
              f"the first pull rewrites its spacing, and every fact stays as it is")
    print(f"next: `wherefore facts pull` writes {decl['path']} at version {v} and pins it in wherefore.json")
    return 0


def _value(raw, want):
    """The value VALUE means, as type `want` or as JSON-else-string; or an error string."""
    if want is not None:
        if want not in ("string", "number", "boolean", "null"):
            return f"--as is string, number, boolean or null, and not {want!r}"
        if want == "string":
            return (raw,)
        try:
            v = json.loads(raw)
        except ValueError:
            v = raw
        if isinstance(v, (dict, list)) or model.typename(v) != want:
            return f"{raw!r} is not {model._a(want)}"
        return (v,)
    try:
        v = json.loads(raw)
    except ValueError:
        return (raw,)
    if isinstance(v, (dict, list)) and v:
        return "one fact at a time: a value that holds others is where facts are, not a fact"
    return (v,)


def _path_for(doc, key):
    """The path a new or existing `key` sits at in `doc`, or an error string."""
    path, node = [], doc
    segs = key.split(".")
    for i, seg in enumerate(segs):
        if isinstance(node, list):
            if not seg.isdigit():
                return f"{'.'.join(segs[:i])} is an array, and {seg!r} is not an index"
            path.append(int(seg))
            node = node[int(seg)] if int(seg) < len(node) else None
        elif isinstance(node, dict):
            path.append(seg)
            node = node.get(seg)
        elif node is None:
            path.extend(segs[i:])
            return path
        else:
            return f"{'.'.join(segs[:i])} is a fact, not an object: nothing sits inside it"
    if isinstance(node, (dict, list)) and node:
        return f"{key} holds other facts: it is where facts are, not one"
    return path


def _set(cfg, args):
    from . import store
    p = _parse(args, ("--source", "--decided-by", "--note", "--as"), (2, 2))
    if isinstance(p, str):
        return _usage(p)
    got, (key, raw) = p
    who = _decider(got)
    if who is None:
        return _usage("say who decided it: --decided-by WHO. A store records who decided every version")
    pick = _pick(cfg, got.get("--source"))
    if isinstance(pick, str):
        print(f"::error::{pick}")
        return 1
    name, decl = pick
    val = _value(raw, got.get("--as"))
    if isinstance(val, str):
        print(f"::error::{val}")
        return 2
    value = val[0]
    try:
        with sources.Stored(cfg.root, name, decl) as src:
            head = src.head()
            now = src.facts(head)
            was = {f.key: f for f in now}.get(key)
            if was is not None and was.type != model.typename(value) and got.get("--as") is None:
                print(f"::error::{name}:{key} is {model._a(was.type)} ({_show(was.value)}), and {raw!r} is read as "
                      f"{model._a(model.typename(value))}: give {model._a(was.type)}, or say --as "
                      f"{model.typename(value)} to change its type")
                return 1
            path = was.path if was is not None else _path_for(model.compose(now), key)
            if isinstance(path, str):
                print(f"::error::{name}:{key}: {path}")
                return 1
            fact = model.Fact(name, key, path, model.typename(value), value)
            wrong = model.wrong_type(fact, decl.get("schema"))
            if wrong:
                print(f"::error::refused: {wrong}")
                return 1
            try:
                v = src.write([fact], who, got.get("--note", ""), schema=decl.get("schema"), base=head)["version"]
            except store.StoreError as e:
                if str(e).startswith("nothing to write"):
                    print(f"{name}:{key} is already {_show(value)}: nothing written")
                    return 0
                raise
    except store.StoreError as e:
        print(f"::error::{name}: {e}")
        return 1
    print(f"{name}:{key} {_show(was.value) if was else '(new)'} -> {_show(value)}: version {v} of {where(decl)}, "
          f"decided by {who}")
    pin = decl["store"].get("version")
    print(f"{decl['path']} is pulled at version {pin if pin else 'none yet'}: `wherefore facts pull` brings it to {v}")
    return 0


def _pull(cfg, args):
    from . import store
    p = _parse(args, ("--source",), (0, 0))
    if isinstance(p, str):
        return _usage(p)
    got, _ = p
    if got.get("--source"):
        pick = _pick(cfg, got["--source"])
        if isinstance(pick, str):
            print(f"::error::{pick}")
            return 1
        todo = [pick]
    else:
        todo = stored(cfg)
        if not todo:
            print(f"::error::{_pick(cfg, None)}")
            return 1
    srcs = cfg.doc["sources"]
    moved, fails = False, 0
    for name, decl in todo:
        try:
            with sources.Stored(cfg.root, name, decl) as src:
                head = src.head()
                if head == 0:
                    print(f"::error::{name}: the store {where(decl)} holds nothing yet: `wherefore facts import` first")
                    fails += 1
                    continue
                text, facts = materialize(src, head)
                pin = src.pinned
                changed = src.changes(pin, head) if pin and pin <= head else None
        except (store.StoreError, model.ModelError) as e:
            print(f"::error::{name}: {e}")
            fails += 1
            continue
        wrong = [w for w in (model.wrong_type(f, decl.get("schema")) for f in facts) if w]
        if wrong:
            for w in wrong:
                print(f"::error::not pulled: {w}")
            fails += 1
            continue
        out = cfg.root / decl["path"]
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        said = (f"(was {pin}): {len(changed)} fact{'s' if len(changed) != 1 else ''} moved" if changed is not None
                and pin != head else "(already pinned)" if pin == head else "(first pull)")
        print(f"{decl['path']}: {len(facts)} facts at version {head} of {where(decl)} {said}")
        if pin != head:
            srcs[name]["store"]["version"] = head
            moved = True
    if moved:
        cfg.write_section("sources", srcs)
        print("wherefore.json pins the version pulled: commit it with the file, in one commit, so the corpus "
              "and the version it was built from move together")
    return 1 if fails else 0


def _log(cfg, args):
    from . import store
    p = _parse(args, ("--source",), (0, 1))
    if isinstance(p, str):
        return _usage(p)
    got, pos = p
    pick = _pick(cfg, got.get("--source"), store_only=False)
    if isinstance(pick, str):
        print(f"::error::{pick}")
        return 1
    name, decl = pick
    src = sources.of(cfg, name)
    try:
        if pos:
            return _log_fact(src, name, decl, pos[0])
        return _log_versions(src, name, decl)
    except (store.StoreError, sources.Unread) as e:
        print(f"::error::{name}: {e}")
        return 1
    finally:
        if isinstance(src, sources.Stored):
            src.close()


def _label(src, v):
    return f"v{v}" if src.kind == "store" else str(v)[:7]


def _history(src):
    """[(version entry, [(key, was, now)])], oldest first."""
    versions = list(reversed(src.versions()))
    out, prev = [], None
    for h in versions:
        if src.kind == "store":
            out.append((h, src.changes(h["version"] - 1, h["version"])))
        else:
            now = src.facts(h["version"])
            out.append((h, sources._changes(prev or [], now)))
            prev = now
    return out


def _log_versions(src, name, decl):
    print(f"{name}  {src.describe()}")
    hist = _history(src)
    if not hist:
        print("  no versions yet")
    for h, moved in list(reversed(hist))[:SHOWN]:
        n = len(moved)
        note = f" - {h['note']}" if h.get("note") else ""
        print(f"  {_label(src, h['version']):>7}  {h['at'][:10]}  {h['decided_by']}  "
              f"{n} fact{'s' if n != 1 else ''} changed{note}")
    if len(hist) > SHOWN:
        print(f"  ... and {len(hist) - SHOWN} earlier")
    if src.kind == "store":
        head, pin = src.head(), src.pinned
        state = ("the store's newest" if pin == head else
                 f"and the store is at {head}: `wherefore facts pull`" if pin else "never: `wherefore facts pull`")
        print(f"{decl['path']} is pulled at version {pin}, {state}" if pin else f"{decl['path']} is pulled {state}")
    return 0


def _log_fact(src, name, decl, key):
    head = src.head()
    now = {f.key: f for f in src.facts(head)}.get(key)
    if now is None:
        print(f"::error::{name}:{key} is no fact at {_label(src, head) if head else 'any version'}")
        return 1
    print(f"{name}:{key} is {_show(now.value)}, {model._a(now.type)}")
    prov = src.provenance(key, head)
    if prov:
        whose = " - the commit's author, as git records it" if src.kind == "files" else ""
        print(f"  decided by {prov['decided_by']} at {_label(src, prov['version'])}, {prov['at']}{whose}")
    rules = model.allowed(decl.get("schema"), key)
    if rules:
        typed = ", ".join(f"{g} is {' or '.join(t)}" for g, t in rules)
        print(f"  typed by the schema: {typed}")
    print("history, newest first:")
    for h, moved in reversed(_history(src)):
        for k, was, to in moved:
            if k == key:
                print(f"  {_label(src, h['version']):>7}  {h['at'][:10]}  {h['decided_by']}  "
                      f"{_show(to.value) if to else 'removed'}")
    return 0


def _usage(msg=None):
    if msg:
        print(f"::error::{msg}\n{USAGE}")
        return 2
    print(USAGE)
    return 0


def main(cfg, args):
    if not args or args[0] in ("-h", "--help"):
        return _usage(None if args else f"wherefore facts takes one of {', '.join(SUBCOMMANDS)}")
    sub, rest = args[0], args[1:]
    if any(a in ("-h", "--help") for a in rest):
        return _usage()
    if sub == "import":
        return _import(cfg, rest)
    if sub == "set":
        return _set(cfg, rest)
    if sub == "pull":
        return _pull(cfg, rest)
    if sub == "log":
        return _log(cfg, rest)
    return _usage(f"no `wherefore facts {sub}`: {', '.join(SUBCOMMANDS)}")


if __name__ == "__main__":
    sys.exit(generate())
