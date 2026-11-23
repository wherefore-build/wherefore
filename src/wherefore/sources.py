"""A fact out of a source, by name.

Two adapters, because two shapes of source exist:

  params   the shape the repository this was extracted from keeps its spec in:
           `family.group.name` names spec[family][group]["params"][name], whose
           value is its `nominal`, or its `value` where it has no band
  leaves   any JSON: a dotted path through objects and arrays (an array index
           is a number), and the value is whatever is there

A source's adapter is declared beside it in wherefore.json `sources`; `leaves`
is the default, because it assumes nothing about the source's shape.

THE INTERFACE, read-only to the engine (docs/scale.md, Stage 3). A source
answers three questions, whatever stands behind it:

  facts(version)        every fact at a version, in document order (model.Fact),
                        named as the source's adapter names them
  changes(a, b)         every fact whose type or value differs between two
                        versions: [(key, was, now)], a missing side None
  provenance(key, v)    who decided a fact, at which version, and when

Two kinds of source answer them:

  Files    a JSON file in the repository: today's source, read exactly as it
           always was. A version is a git commit, and None the working tree.
           Provenance is the commit that last changed the fact's value and its
           author as git records it - which anyone can type; Stage 2's
           `wherefore check decisions` is what verifies a decision.
  Stored   a store speaking wherefore-store/1 (store.py). A version is the
           store's own number. Provenance is what the store recorded.

Everything that reads a source's FILE - the gate, reach, retired, claims,
drift, decisions, the client's own generators - goes on reading the file. A
store-backed source's file is materialized from the store at the version
wherefore.json pins (facts.py), so the file and the store are held to agree
by the gate, and nothing above the interface had to change for it.
"""
import json
import pathlib
import subprocess


def value(doc, dotted, adapter="leaves"):
    if adapter == "params":
        family, group, name = dotted.split(".")
        p = doc[family][group]["params"][name]
        return p.get("nominal", p.get("value"))
    node = doc
    for part in dotted.split("."):
        node = node[int(part)] if isinstance(node, list) else node[part]
    return node


def leaves(doc, prefix=()):
    """(dotted path, value) for every scalar in a JSON document, in order."""
    if isinstance(doc, dict):
        for k, v in doc.items():
            yield from leaves(v, prefix + (str(k),))
    elif isinstance(doc, list):
        for i, v in enumerate(doc):
            yield from leaves(v, prefix + (str(i),))
    else:
        yield ".".join(prefix), doc


# ── the interface ───────────────────────────────────────────────────────────

class Unread(Exception):
    """A source that could not be read at a version: words a person reads."""


class Files:
    """A source that is a JSON file in the repository; a version is a git commit."""

    kind = "files"

    def __init__(self, root, name, decl):
        self.root = pathlib.Path(root)
        self.name, self.decl = name, decl
        self.path = decl["path"]

    def describe(self):
        return f"{self.path}, a file: each version is a git commit"

    def _git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, capture_output=True, text=True)

    def head(self):
        """The commit HEAD names, or None in a repository with none."""
        r = self._git("rev-parse", "--verify", "--quiet", "HEAD^{commit}")
        return r.stdout.strip() or None

    def document(self, version=None):
        """The parsed file at `version`, or None where that commit has none."""
        if version is None:
            p = self.root / self.path
            if not p.is_file():
                return None
            raw = p.read_bytes()
        else:
            r = subprocess.run(["git", "show", f"{version}:./{self.path}"], cwd=self.root, capture_output=True)
            if r.returncode:
                return None
            raw = r.stdout
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as e:
            at = "in the working tree" if version is None else f"at {str(version)[:12]}"
            raise Unread(f"{self.path} {at} is not JSON ({e})")

    def facts(self, version=None):
        from . import model
        doc = self.document(version)
        if doc is None:
            return []
        try:
            return model.read(doc, self.name, self.decl.get("adapter", "leaves"))
        except model.ModelError as e:
            raise Unread(str(e))

    def changes(self, a, b):
        return _changes(self.facts(a), self.facts(b))

    def versions(self):
        """[{version, decided_by, at, note}], newest first: the commits that touched the file."""
        r = self._git("log", "--format=%H%x1f%an%x1f%aI%x1f%s", "--", self.path)
        out = []
        for line in r.stdout.splitlines():
            parts = line.split("\x1f")
            if len(parts) == 4:
                out.append({"version": parts[0], "decided_by": parts[1], "at": parts[2], "note": parts[3]})
        return out

    def provenance(self, key, version=None):
        """{version, decided_by, at} of the commit that last set `key` to the
        value it has at `version` (HEAD by default), or None where no commit
        holds it."""
        history = self.versions()
        if version is not None:
            ids = [h["version"] for h in history]
            full = self._git("rev-parse", "--verify", "--quiet", f"{version}^{{commit}}").stdout.strip()
            history = history[ids.index(full):] if full in ids else []
        found = None
        current = None
        for h in history:                            # newest first
            here = {f.key: f for f in self.facts(h["version"])}.get(key)
            if current is None:
                if here is None:
                    return None
                current, found = here, h
                continue
            if here is None or here.type != current.type or _text(here.value) != _text(current.value):
                break
            found = h
        return {k: found[k] for k in ("version", "decided_by", "at")} if found else None


class Stored:
    """A source backed by a store speaking wherefore-store/1; a version is the store's number."""

    kind = "store"

    def __init__(self, root, name, decl):
        self.root = pathlib.Path(root)
        self.name, self.decl = name, decl
        self.store = decl["store"]
        self.path = decl["path"]
        self._client = None

    def describe(self):
        where = self.store.get("at") or " ".join(self.store.get("run", []))
        return f"{self.path}, materialized from the store {where}"

    @property
    def client(self):
        if self._client is None:
            from . import store
            self._client = store.Client(store.argv(self.store), self.root)
        return self._client

    def close(self):
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def head(self):
        """The store's newest version, asked now: another writer may have moved it."""
        from . import store
        return self.client.ask({"op": "hello", "protocol": store.PROTOCOL})["head"]

    @property
    def pinned(self):
        return self.store.get("version")

    def _fact(self, f):
        from . import model
        return model.Fact(self.name, f["key"], f["path"], f["type"], f["value"], f.get("provenance"))

    def facts(self, version=None):
        v = self.head() if version is None else version
        return [self._fact(f) for f in self.client.ask({"op": "facts", "version": v})["facts"]]

    def changes(self, a, b):
        got = self.client.ask({"op": "changes", "from": a, "to": b})["changes"]
        return [(c["key"], self._fact(c["was"]) if c.get("was") else None,
                 self._fact(c["now"]) if c.get("now") else None) for c in got]

    def versions(self):
        return list(reversed(self.client.ask({"op": "log"})["versions"]))

    def provenance(self, key, version=None):
        got = {f.key: f for f in self.facts(version)}.get(key)
        return got.provenance if got else None

    def write(self, facts, decided_by, note="", replace=False, schema=None, base=None):
        req = {"op": "write", "base": self.head() if base is None else base, "replace": replace,
               "decided_by": decided_by, "note": note, "schema": schema or {},
               "facts": [{"key": f.key, "path": list(f.path), "type": f.type, "value": f.value} for f in facts]}
        return self.client.ask(req)


def of(cfg, name):
    """The source `name` declares, behind the interface."""
    _name, decl = cfg.source(name)
    return (Stored if decl.get("store") else Files)(cfg.root, name, decl)


def _text(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True)


def _changes(was, now):
    a = {f.key: f for f in was}
    b = {f.key: f for f in now}
    out = []
    for key in list(a) + [k for k in b if k not in a]:
        x, y = a.get(key), b.get(key)
        if x and y and x.type == y.type and _text(x.value) == _text(y.value):
            continue
        out.append((key, x, y))
    return out
