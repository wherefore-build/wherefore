"""The store protocol, wherefore-store/1, and the reference store that speaks it.

A SOURCE MAY BE BACKED BY A STORE instead of being a file a person edits: the
facts live in the store, with a type each and who decided them, version after
version, and the engine writes the source's file from it (`wherefore facts
pull`; the generator `python -m wherefore.facts`). Design: docs/scale.md,
Stage 3. This module is the protocol any store speaks, the client the engine
speaks it with, and one store that speaks it, on SQLite, so the protocol is
shown working and not only written down.

THE PROTOCOL. A store is a command. The engine starts it in the corpus's root,
writes one request per line to its standard input - a JSON object - and reads
one JSON object per line back from its standard output for each. When the
engine is done it closes standard input, and the store exits. Nothing else is
assumed: no network, no library, no language. Every answer carries "ok"; one
that is false carries "error", words a person reads, and may carry "fact",
the dotted key it is about.

  hello     {"op": "hello", "protocol": "wherefore-store/1"}
            -> {"ok": true, "protocol": "wherefore-store/1", "store": WORDS,
                "head": N}
            N is the newest version, 0 for a store that holds nothing yet.
  facts     {"op": "facts", "version": N}
            -> {"ok": true, "version": N, "facts": [FACT, ...]}
            Every fact at version N, in document order.
  changes   {"op": "changes", "from": A, "to": B}
            -> {"ok": true, "changes": [{"key": K, "was": FACT|null,
                                         "now": FACT|null}, ...]}
            Every fact whose type or value differs between A and B, or that is
            in one and not the other. A may be 0: the empty store.
  log       {"op": "log"}
            -> {"ok": true, "versions": [{"version": N, "decided_by": WHO,
                "at": TIME, "note": WORDS, "changed": COUNT}, ...]}
            Oldest first.
  write     {"op": "write", "base": N, "facts": [FACT, ...], "replace": BOOL,
             "decided_by": WHO, "note": WORDS, "schema": {GLOB: TYPE}}
            -> {"ok": true, "version": N + 1, "changed": COUNT}
            One new version. With "replace" the facts given are the whole of
            it, and any fact not given is removed; without, they are set and
            every other fact is kept. "base" is the version the writer read:
            a store whose head is not "base" refuses, because another writer
            moved it in between. A store refuses a fact whose type is not
            one the schema allows, naming it, and a write that changes
            nothing. A version, once written, is never changed.

  FACT      {"key": "product.price_usd", "path": ["product", "price_usd"],
             "type": "number", "value": 89,
             "provenance": {"version": 3, "decided_by": "fern-founder",
                            "at": "2026-11-22T09:14:03Z"}}
            `provenance` is in what a store answers, and is the version the
            fact's value was last set at, by whom and when. A writer leaves
            it out: the store sets it.

The engine reads a store through `facts`, `changes` and `log` - the source
interface in sources.py - and writes to one only through the `wherefore facts`
commands. A store is told nothing about which corpus asks, nor anything to
authenticate with: a store that needs either is out of scope here.

THE REFERENCE STORE is `python -m wherefore.store PATH`: one SQLite file
(Python's own sqlite3; no dependency), declared as `"store": {"protocol":
"wherefore-store/1", "at": PATH}`. Its versions are append-only, and the
database says so itself: a trigger refuses any UPDATE or DELETE, so an old
version can be read back for as long as the file exists. Each version records
only the facts it changed. Reading never creates the file; the first write
does.
"""
import datetime
import json
import os
import pathlib
import sqlite3
import subprocess
import sys

PROTOCOL = "wherefore-store/1"


class StoreError(Exception):
    """A store refused, or did not answer as the protocol says."""

    def __init__(self, msg, fact=None):
        super().__init__(msg)
        self.fact = fact


# ── the engine's side ───────────────────────────────────────────────────────

class Client:
    """One conversation with a store: start it, ask, close."""

    def __init__(self, argv, cwd):
        self.argv = list(argv)
        try:
            self.proc = subprocess.Popen(self.argv, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE, text=True, encoding="utf-8")
        except OSError as e:
            raise StoreError(f"the store could not be started ({' '.join(self.argv)}): {e}")
        self.hello = self.ask({"op": "hello", "protocol": PROTOCOL})
        if self.hello.get("protocol") != PROTOCOL:
            self.close()
            raise StoreError(f"the store ({' '.join(self.argv)}) speaks {self.hello.get('protocol')!r}, "
                             f"and this engine speaks {PROTOCOL}")

    def ask(self, request):
        try:
            self.proc.stdin.write(json.dumps(request, ensure_ascii=False) + "\n")
            self.proc.stdin.flush()
            line = self.proc.stdout.readline()
        except (BrokenPipeError, OSError):
            line = ""
        if not line:
            err = ""
            try:
                self.proc.wait(timeout=5)
                err = self.proc.stderr.read().strip()
            except Exception:
                pass
            raise StoreError(f"the store ({' '.join(self.argv)}) closed without answering "
                             f"{request.get('op')!r}" + (f": {err[-600:]}" if err else ""))
        try:
            answer = json.loads(line)
        except ValueError:
            raise StoreError(f"the store ({' '.join(self.argv)}) answered {request.get('op')!r} with "
                             f"something that is not JSON: {line[:200]!r}")
        if not isinstance(answer, dict) or "ok" not in answer:
            raise StoreError(f"the store ({' '.join(self.argv)}) answered {request.get('op')!r} without "
                             f"\"ok\": {line[:200]!r}")
        if not answer["ok"]:
            raise StoreError(str(answer.get("error") or "refused, and said nothing"), answer.get("fact"))
        return answer

    def close(self):
        try:
            self.proc.stdin.close()
        except OSError:
            pass
        try:
            self.proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        for f in (self.proc.stdout, self.proc.stderr):
            try:
                f.close()
            except OSError:
                pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def argv(decl):
    """The command a store declaration names: its `run`, or the reference store at `at`."""
    if decl.get("run"):
        return list(decl["run"])
    return [sys.executable, "-m", "wherefore.store", decl["at"]]


# ── the reference store ─────────────────────────────────────────────────────

SCHEMA_SQL = """
CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT NOT NULL);
CREATE TABLE versions (
  version    INTEGER PRIMARY KEY,
  decided_by TEXT NOT NULL,
  at         TEXT NOT NULL,
  note       TEXT NOT NULL
);
CREATE TABLE facts (
  version INTEGER NOT NULL REFERENCES versions(version),
  key     TEXT NOT NULL,
  path    TEXT NOT NULL,
  ord     INTEGER NOT NULL,
  type    TEXT NOT NULL,
  value   TEXT NOT NULL,
  gone    INTEGER NOT NULL,
  since   INTEGER NOT NULL,
  PRIMARY KEY (version, key)
);
CREATE TRIGGER versions_are_kept_u BEFORE UPDATE ON versions
  BEGIN SELECT RAISE(ABORT, 'a version, once written, is never changed'); END;
CREATE TRIGGER versions_are_kept_d BEFORE DELETE ON versions
  BEGIN SELECT RAISE(ABORT, 'a version, once written, is never changed'); END;
CREATE TRIGGER facts_are_kept_u BEFORE UPDATE ON facts
  BEGIN SELECT RAISE(ABORT, 'a version, once written, is never changed'); END;
CREATE TRIGGER facts_are_kept_d BEFORE DELETE ON facts
  BEGIN SELECT RAISE(ABORT, 'a version, once written, is never changed'); END;
"""


def _now():
    clock = os.environ.get("WHEREFORE_STORE_CLOCK")      # for a test that needs a fixed time
    if clock:
        return clock
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Reference:
    """The SQLite store, answering the protocol one request at a time."""

    def __init__(self, path):
        self.path = pathlib.Path(path)

    def _read(self):
        if not self.path.is_file():
            return None
        return sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True)

    def _head(self, db):
        if db is None:
            return 0
        return db.execute("SELECT COALESCE(MAX(version), 0) FROM versions").fetchone()[0]

    def handle(self, req):
        op = req.get("op") if isinstance(req, dict) else None
        try:
            if op == "hello":
                return self.hello(req)
            if op == "facts":
                return self.facts_op(req)
            if op == "changes":
                return self.changes_op(req)
            if op == "log":
                return self.log_op(req)
            if op == "write":
                return self.write_op(req)
            return {"ok": False, "error": f"no op {op!r}: hello, facts, changes, log, write"}
        except StoreError as e:
            return {"ok": False, "error": str(e), **({"fact": e.fact} if e.fact else {})}
        except sqlite3.DatabaseError as e:
            return {"ok": False, "error": f"{self.path}: {e}"}

    def hello(self, req):
        db = self._read()
        try:
            head = self._head(db)
        finally:
            if db is not None:
                db.close()
        return {"ok": True, "protocol": PROTOCOL, "head": head,
                "store": f"the reference store, SQLite, at {self.path}" + ("" if db else " (no file yet)")}

    # reading

    def _at(self, db, version):
        """{key: row} at `version`, removed facts left out, in document order."""
        if db is None or version == 0:
            return {}
        rows = db.execute(
            "SELECT f.key, f.path, f.ord, f.type, f.value, f.gone, f.since, v.decided_by, v.at "
            "FROM facts f JOIN versions v ON v.version = f.since "
            "WHERE f.version = (SELECT MAX(g.version) FROM facts g WHERE g.key = f.key AND g.version <= ?) "
            "ORDER BY f.ord", (version,)).fetchall()
        out = {}
        for key, path, ord_, typ, value, gone, since, by, at in rows:
            if gone:
                continue
            out[key] = {"key": key, "path": json.loads(path), "type": typ, "value": json.loads(value),
                        "provenance": {"version": since, "decided_by": by, "at": at}, "_ord": ord_}
        return out

    def _version(self, db, req, field="version"):
        v = req.get(field)
        head = self._head(db)
        if not (isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= head):
            raise StoreError(f"there is no version {v!r} here: the store is at {head}")
        return v

    @staticmethod
    def _public(row):
        return {k: v for k, v in row.items() if not k.startswith("_")} if row else None

    def facts_op(self, req):
        db = self._read()
        try:
            v = self._version(db, req)
            return {"ok": True, "version": v, "facts": [self._public(r) for r in self._at(db, v).values()]}
        finally:
            if db is not None:
                db.close()

    def changes_op(self, req):
        db = self._read()
        try:
            a, b = self._version(db, req, "from"), self._version(db, req, "to")
            was, now = self._at(db, a), self._at(db, b)
            out = []
            for key in list(was) + [k for k in now if k not in was]:
                x, y = was.get(key), now.get(key)
                if x and y and x["type"] == y["type"] and _text(x["value"]) == _text(y["value"]):
                    continue
                out.append({"key": key, "was": self._public(x), "now": self._public(y)})
            return {"ok": True, "changes": out}
        finally:
            if db is not None:
                db.close()

    def log_op(self, req):
        db = self._read()
        try:
            if db is None:
                return {"ok": True, "versions": []}
            rows = db.execute(
                "SELECT v.version, v.decided_by, v.at, v.note, "
                "(SELECT COUNT(*) FROM facts f WHERE f.version = v.version AND (f.since = v.version OR f.gone)) "
                "FROM versions v ORDER BY v.version").fetchall()
            return {"ok": True, "versions": [{"version": n, "decided_by": by, "at": at, "note": note,
                                              "changed": c} for n, by, at, note, c in rows]}
        finally:
            if db is not None:
                db.close()

    # writing

    def write_op(self, req):
        from . import model
        who = req.get("decided_by")
        if not (isinstance(who, str) and who.strip()):
            raise StoreError("a write says who decided it, in `decided_by`: a store records who, "
                             "and a version nobody decided is not one")
        given = req.get("facts")
        if not isinstance(given, list):
            raise StoreError("a write carries `facts`, a list")
        schema = req.get("schema") or {}
        bad = model.schema_problem(schema) if schema else None
        if bad:
            raise StoreError(f"the schema {bad}")
        facts = []
        for f in given:
            if not (isinstance(f, dict) and isinstance(f.get("key"), str) and isinstance(f.get("path"), list)):
                raise StoreError(f"a fact is {{key, path, type, value}}, and this is {f!r}")
            fact = model.Fact("", f["key"], f["path"], f.get("type"), f.get("value"))
            if ".".join(str(p) for p in fact.path) != fact.key:
                raise StoreError(f"{fact.key}: its path {fact.path} says {'.'.join(map(str, fact.path))}",
                                 fact.key)
            try:
                if model.typename(fact.value) != fact.type:
                    raise StoreError(f"{fact.key} says it is {fact.type} and holds {fact.value!r}", fact.key)
            except model.ModelError as e:
                raise StoreError(f"{fact.key}: {e}", fact.key)
            wrong = model.wrong_type(fact, schema)
            if wrong:
                raise StoreError(f"refused: {wrong}", fact.key)
            facts.append(fact)
        keys = [f.key for f in facts]
        if len(set(keys)) != len(keys):
            twice = sorted({k for k in keys if keys.count(k) > 1})
            raise StoreError(f"a write says {twice[0]} twice", twice[0])

        self.path.parent.mkdir(parents=True, exist_ok=True)
        fresh = not self.path.is_file()
        db = sqlite3.connect(str(self.path), isolation_level=None)
        try:
            return self._write(db, fresh, facts, who, req)
        except StoreError:
            if fresh:
                db.close()
                self.path.unlink(missing_ok=True)
            raise
        finally:
            db.close()

    def _write(self, db, fresh, facts, who, req):
        from . import model
        if fresh:
            db.executescript(SCHEMA_SQL)
            db.execute("INSERT INTO meta VALUES ('protocol', ?)", (PROTOCOL,))
        db.execute("BEGIN IMMEDIATE")
        head = self._head(db)
        if req.get("base") != head:
            db.execute("ROLLBACK")
            raise StoreError(f"the store moved: it is at version {head}, and this write was made "
                             f"against {req.get('base')!r}. Read it again and decide again")
        was = self._at(db, head)
        if req.get("replace"):
            order = {f.key: i for i, f in enumerate(facts)}
            after = {f.key: f for f in facts}
        else:
            order = {k: r["_ord"] for k, r in was.items()}
            after = {k: model.Fact("", k, r["path"], r["type"], r["value"]) for k, r in was.items()}
            nxt = max(order.values(), default=-1) + 1
            for f in facts:
                if f.key not in order:
                    order[f.key] = nxt
                    nxt += 1
                after[f.key] = f
        # The whole version must still be a document.
        try:
            model.compose(sorted(after.values(), key=lambda f: order[f.key]))
        except model.ModelError as e:
            db.execute("ROLLBACK")
            raise StoreError(f"refused: {e}")
        v = head + 1
        rows = []
        for key, f in after.items():
            old = was.get(key)
            same_value = old is not None and old["type"] == f.type and _text(old["value"]) == _text(f.value)
            if same_value and old["path"] == list(f.path) and old["_ord"] == order[key]:
                continue
            since = old["provenance"]["version"] if same_value else v
            rows.append((v, key, json.dumps(list(f.path), ensure_ascii=False), order[key], f.type,
                         _text(f.value), 0, since))
        for key, old in was.items():
            if key not in after:
                rows.append((v, key, json.dumps(old["path"], ensure_ascii=False), old["_ord"], old["type"],
                             _text(old["value"]), 1, v))
        changed = sum(1 for r in rows if r[7] == v)
        if not rows:
            db.execute("ROLLBACK")
            raise StoreError(f"nothing to write: version {head} already says every fact given")
        db.execute("INSERT INTO versions VALUES (?, ?, ?, ?)", (v, who.strip(), _now(), str(req.get("note") or "")))
        db.executemany("INSERT INTO facts VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
        db.execute("COMMIT")
        return {"ok": True, "version": v, "changed": changed}


def _text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def serve(path, stdin=None, stdout=None):
    """Answer the protocol on stdin/stdout until stdin closes."""
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    store = Reference(path)
    for line in stdin:
        if not line.strip():
            continue
        try:
            req = json.loads(line)
        except ValueError:
            answer = {"ok": False, "error": f"not JSON: {line[:200]!r}"}
        else:
            answer = store.handle(req)
        stdout.write(json.dumps(answer, ensure_ascii=False) + "\n")
        stdout.flush()
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1 or argv[0].startswith("-"):
        print("usage: python -m wherefore.store PATH\n\nThe reference store: speaks "
              f"{PROTOCOL} on standard input and output, over the SQLite file at PATH.",
              file=sys.stderr)
        return 2
    return serve(argv[0])


if __name__ == "__main__":
    sys.exit(main())
