"""Facts as a typed model, behind a pluggable source (docs/scale.md, Stage 3).

The model (model.py), the store protocol and the reference store (store.py),
the source interface (sources.py), the `wherefore facts` commands and the
generator that materializes a store into a file (facts.py) - and the design's
acceptance: the same corpus built once from files and once from the
reference store makes byte-identical documents, and the gate and the checks
pass on both.
"""
import json
import os
import pathlib
import shutil
import sqlite3
import sys
import tempfile
import textwrap
import unittest

from _util import ENGINE, SRC, git, repo, wherefore
from wherefore import model, since, sources, store
from wherefore.config import Config, ConfigError

FIXTURE = ENGINE / "tests/fixture"
# What the fixture's generators write: every document a customer or a buyer reads.
DOCUMENTS = ("site/index.html", "deck/one-pager.svg", "deck/speaker-notes.txt", "ledger.json")
SCHEMA = {"product.price_usd": "number", "product.capacity_l": "number", "company.*": "string",
          "origin.activities.*": "string"}
MATERIALIZE = {"script": "-m wherefore.facts", "cwd": ".", "probe": False,
               "makes": "facts.json, from the store",
               "why": "it writes the source the reach probe moves, and would put the store's value back"}


def commit(root, msg="x"):
    git(root, "add", "-A")
    git(root, "-c", "user.email=t@w", "-c", "user.name=t", "commit", "-qm", msg)


def copy_fixture(name):
    root = pathlib.Path(tempfile.mkdtemp(prefix=f"wherefore-facts-{name}-")) / "fernhollow"
    shutil.copytree(FIXTURE, root, ignore=shutil.ignore_patterns("__pycache__"))
    return root


def store_backed(root, decl_extra=None):
    """Declare the fixture's facts as backed by the reference store at facts.db."""
    cfg = json.loads((root / "wherefore.json").read_text(encoding="utf-8"))
    src = cfg["sources"]["facts"]
    src["store"] = {"protocol": "wherefore-store/1", "at": "facts.db", **(decl_extra or {})}
    src["schema"] = dict(SCHEMA)
    cfg["generators"].insert(0, dict(MATERIALIZE))
    for rule in cfg["inventory"]["authored"]["rules"]:
        if rule[0] == "facts.json":
            rule[0], rule[1] = "facts.db", "THE SOURCE: the store the facts live in; facts.json is made from it"
    (root / "wherefore.json").write_text(json.dumps(cfg, indent=1) + "\n", encoding="utf-8")


def doc(path):
    """A JSON file as nested pairs, so key order counts in a comparison."""
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"), object_pairs_hook=list)


# ── the model ───────────────────────────────────────────────────────────────

class TheModel(unittest.TestCase):
    def test_a_document_and_its_facts_are_one_thing_said_two_ways(self):
        d = json.loads((FIXTURE / "facts.json").read_text(encoding="utf-8"))
        facts = model.decompose(d, "facts")
        self.assertEqual([f.key for f in facts], [k for k, _ in sources.leaves(d)],
                         "the facts are the leaves, named as `leaves` names them, in document order")
        self.assertEqual(model.compose(facts), d)
        self.assertEqual(list(model.compose(facts)), list(d))
        price = {f.key: f for f in facts}["product.price_usd"]
        self.assertEqual((model.identity(price), price.path, price.type, price.value),
                         ("facts:product.price_usd", ["product", "price_usd"], "number", 89))
        self.assertEqual({f.key: f for f in facts}["origin.activities.1"].path, ["origin", "activities", 1])

    def test_types_and_the_empty_containers_survive(self):
        d = {"a": None, "b": True, "c": 1.5, "d": "x", "e": [], "f": {}, "g": [{"h": 0}], "i": {"0": "key, not index"}}
        facts = model.decompose(d)
        self.assertEqual([f.type for f in facts], ["null", "boolean", "number", "string", "array", "object", "number",
                                                   "string"])
        self.assertEqual(model.compose(facts), d)
        self.assertIsInstance(model.compose(facts)["i"], dict)

    def test_what_cannot_be_a_document_is_refused(self):
        with self.assertRaisesRegex(model.ModelError, "two facts would both be called 'a.b'"):
            model.decompose({"a.b": 1, "a": {"b": 2}}, "facts")
        with self.assertRaisesRegex(model.ModelError, "the top of a source is an object"):
            model.decompose([1, 2])
        F = model.Fact
        with self.assertRaisesRegex(model.ModelError, "an array has no gaps"):
            model.compose([F("s", "a.0", ["a", 0], "number", 1), F("s", "a.2", ["a", 2], "number", 3)])
        with self.assertRaisesRegex(model.ModelError, "is a fact, not an object"):
            model.compose([F("s", "a", ["a"], "number", 1), F("s", "a.b", ["a", "b"], "number", 2)])
        with self.assertRaisesRegex(model.ModelError, "says it is number and holds '1'"):
            model.compose([F("s", "a", ["a"], "number", "1")])

    def test_a_schema_types_by_glob_and_names_the_fact(self):
        facts = model.decompose({"product": {"price_usd": "89", "name": "One"}}, "facts")
        got = model.check(facts, {"product.price_usd": "number", "product.name": ["string", "null"],
                                  "product.prcie": "number"}, "facts")
        self.assertEqual(got, [
            'facts:product.price_usd is a string ("89"), and the schema says product.price_usd is number',
            "facts: the schema's 'product.prcie' names no fact - a mistyped glob types nothing"])
        self.assertIsNone(model.schema_problem({"a.*": ["string", "null"]}))
        self.assertIn("a type is one of", model.schema_problem({"a": "integer"}))

    def test_a_params_source_is_typed_by_the_names_its_adapter_gives(self):
        d = {"units": "mm", "_meta": {"note": "not a family"},
             "hardware": {"bearing": {"params": {"bore": {"nominal": 8.0, "tol": [0, 0.01], "value": 9},
                                                 "count": {"value": 2, "provenance": "drawing 4"}}},
                          "notes": "a group with no params"},
             "geometry": {"arm": {"params": {"points": {"value": [[0, 0], [1, 2]]},
                                             "reach": {"derived": "from points"}}}}}
        facts = model.read(d, "spec", "params")
        self.assertEqual([(f.key, f.type, f.value) for f in facts], [
            ("hardware.bearing.bore", "number", 8.0), ("hardware.bearing.count", "number", 2),
            ("geometry.arm.points", "array", [[0, 0], [1, 2]]), ("geometry.arm.reach", "null", None)])
        self.assertEqual([sources.value(d, f.key, "params") for f in facts], [f.value for f in facts],
                         "a params fact is what sources.value reads by its name")
        self.assertEqual(facts[0].path, ["hardware", "bearing", "params", "bore", "nominal"])
        self.assertEqual(model.check(facts, {"hardware.*": "number", "geometry.arm.points": "array",
                                             "geometry.arm.reach": "number"}, "spec"),
                         ["spec:geometry.arm.reach is a null (null), and the schema says geometry.arm.reach is number"])
        self.assertEqual([f.key for f in model.read(d, "spec")], [k for k, _ in sources.leaves(d)],
                         "leaves is still the default")
        with self.assertRaisesRegex(model.ModelError, "two parameters would both be called 'a.b.c.d'"):
            model.params({"a": {"b": {"params": {"c.d": {"value": 1}}}, "b.c": {"params": {"d": {"value": 2}}}}})

    def test_a_file_source_names_its_facts_by_its_adapter(self):
        root = repo({"spec.json": {"hardware": {"bearing": {"params": {"bore": {"nominal": 8.0}}}}}})
        src = sources.Files(root, "spec", {"path": "spec.json", "adapter": "params"})
        self.assertEqual([f.key for f in src.facts()], ["hardware.bearing.bore"])
        self.assertEqual(src.provenance("hardware.bearing.bore")["decided_by"], "t")


# ── the reference store, through the protocol ───────────────────────────────

class TheProtocol(unittest.TestCase):
    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="wherefore-store-"))
        self.db = self.dir / "facts.db"
        self.env = dict(os.environ, PYTHONPATH=str(SRC))

    def client(self):
        was = os.environ.get("PYTHONPATH")
        os.environ["PYTHONPATH"] = str(SRC)
        try:
            return store.Client([sys.executable, "-m", "wherefore.store", str(self.db)], self.dir)
        finally:
            if was is None:
                os.environ.pop("PYTHONPATH")
            else:
                os.environ["PYTHONPATH"] = was

    def write(self, c, facts, base, **more):
        return c.ask({"op": "write", "base": base, "decided_by": more.pop("by", "dana"), "note": "",
                      "facts": [{"key": k, "path": k.split("."), "type": model.typename(v), "value": v}
                                for k, v in facts], **more})

    def test_hello_creates_nothing_and_a_write_makes_a_version(self):
        with self.client() as c:
            self.assertEqual((c.hello["protocol"], c.hello["head"]), ("wherefore-store/1", 0))
            self.assertFalse(self.db.exists(), "reading never creates the store")
            got = self.write(c, [("plan.price", 89), ("plan.name", "Pro")], 0, replace=True)
            self.assertEqual((got["version"], got["changed"]), (1, 2))
            self.write(c, [("plan.price", 95)], 1, by="lee")
            facts = c.ask({"op": "facts", "version": 2})["facts"]
            self.assertEqual([(f["key"], f["value"]) for f in facts], [("plan.price", 95), ("plan.name", "Pro")])
            prov = {f["key"]: f["provenance"] for f in facts}
            self.assertEqual((prov["plan.price"]["version"], prov["plan.price"]["decided_by"]), (2, "lee"))
            self.assertEqual((prov["plan.name"]["version"], prov["plan.name"]["decided_by"]), (1, "dana"))
            self.assertEqual([f["value"] for f in c.ask({"op": "facts", "version": 1})["facts"]], [89, "Pro"],
                             "an old version reads back as it was")
            ch = c.ask({"op": "changes", "from": 1, "to": 2})["changes"]
            self.assertEqual([(x["key"], x["was"]["value"], x["now"]["value"]) for x in ch], [("plan.price", 89, 95)])
            self.assertEqual([v["decided_by"] for v in c.ask({"op": "log"})["versions"]], ["dana", "lee"])

    def test_it_refuses_a_stale_base_a_wrong_type_and_a_write_of_nothing(self):
        with self.client() as c:
            self.write(c, [("plan.price", 89)], 0, replace=True)
            with self.assertRaisesRegex(store.StoreError, "the store moved: it is at version 1"):
                self.write(c, [("plan.price", 95)], 0)
            with self.assertRaises(store.StoreError) as e:
                self.write(c, [("plan.price", "95")], 1, schema={"plan.*": "number"})
            self.assertIn('plan.price is a string ("95"), and the schema says plan.* is number', str(e.exception))
            self.assertEqual(e.exception.fact, "plan.price")
            with self.assertRaisesRegex(store.StoreError, "nothing to write"):
                self.write(c, [("plan.price", 89)], 1)
            with self.assertRaisesRegex(store.StoreError, "says who decided it"):
                self.write(c, [("plan.price", 90)], 1, by=" ")
            self.assertEqual(c.ask({"op": "hello"})["head"], 1)

    def test_a_version_once_written_is_never_changed(self):
        with self.client() as c:
            self.write(c, [("plan.price", 89)], 0, replace=True)
        db = sqlite3.connect(str(self.db))
        for sql in ("UPDATE facts SET value = '95'", "DELETE FROM facts", "UPDATE versions SET decided_by = 'x'"):
            with self.assertRaisesRegex(sqlite3.DatabaseError, "never changed"):
                db.execute(sql)
        db.close()

    def test_any_command_that_speaks_it_is_a_store(self):
        """A store of one's own, in a few lines that are not the engine's: the protocol is the contract."""
        toy = textwrap.dedent('''\
            import json, sys
            FACTS = [{"key": "plan.price", "path": ["plan", "price"], "type": "number", "value": 89,
                      "provenance": {"version": 1, "decided_by": "dana", "at": "2026-11-22T00:00:00Z"}}]
            for line in sys.stdin:
                req = json.loads(line)
                if req["op"] == "hello":
                    out = {"ok": True, "protocol": "wherefore-store/1", "store": "a toy", "head": 1}
                elif req["op"] == "facts":
                    out = {"ok": True, "version": 1, "facts": FACTS}
                else:
                    out = {"ok": False, "error": "a toy store reads only"}
                print(json.dumps(out), flush=True)
            ''')
        root = repo({"toy_store.py": toy, ".gitignore": "__pycache__/\n", "wherefore.json": {
            "wherefore": 1, "name": "toy",
            "sources": {"facts": {"path": "facts.json", "why": "the source",
                                  "store": {"protocol": "wherefore-store/1", "run": [sys.executable, "toy_store.py"]}}},
            "generators": [dict(MATERIALIZE)],
            "inventory": {"authored": {"rules": [["wherefore.json", "what the corpus is"],
                                                 ["toy_store.py", "the store"], [".gitignore", "what is not tracked"]]},
                          "captured": {"groups": {}}}}})
        code, out = wherefore(root, "facts", "pull")
        self.assertEqual(code, 0, out)
        self.assertEqual((root / "facts.json").read_text(encoding="utf-8"), '{\n "plan": {\n  "price": 89\n }\n}\n')
        code, out = wherefore(root, "facts", "set", "plan.price", "95", "--decided-by", "dana")
        self.assertEqual(code, 1, out)
        self.assertIn("a toy store reads only", out)
        commit(root)
        code, out = wherefore(root, "gate")
        self.assertEqual(code, 0, out)


# ── wherefore.json ──────────────────────────────────────────────────────────

class TheDeclaration(unittest.TestCase):
    def cfg(self, store=None, gens=None, schema=None):
        src = {"path": "facts.json", "why": "x"}
        if store is not None:
            src["store"] = store
        if schema is not None:
            src["schema"] = schema
        return Config(tempfile.mkdtemp(), {"wherefore": 1, "sources": {"facts": src},
                                           "generators": [dict(MATERIALIZE)] if gens is None else gens})

    def refused(self, words, **kw):
        with self.assertRaises(ConfigError) as e:
            self.cfg(**kw)
        self.assertIn(words, str(e.exception.code))

    def test_a_store_and_a_schema_are_held_to_their_shape(self):
        ok = {"protocol": "wherefore-store/1", "at": "facts.db"}
        self.cfg(store=ok, schema={"product.*": "number"})
        self.cfg(store={"protocol": "wherefore-store/1", "run": ["my-store", "--json"], "version": 3, "indent": 2})
        self.refused("this engine speaks wherefore-store/1", store={"protocol": "graph/9", "at": "f.db"})
        self.refused("and exactly one of them", store={"protocol": "wherefore-store/1", "at": "f.db", "run": ["x"]})
        self.refused("and exactly one of them", store={"protocol": "wherefore-store/1"})
        self.refused("a path inside the repository", store={"protocol": "wherefore-store/1", "at": "../f.db"})
        self.refused("which it does not take", store={**ok, "url": "https://x"})
        self.refused("`store.version` is the version", store={**ok, "version": 0})
        self.refused("a type is one of", schema={"product.*": "integer"})

    def test_a_store_backed_params_source_takes_no_schema(self):
        ok = {"protocol": "wherefore-store/1", "at": "facts.db"}
        with self.assertRaises(ConfigError) as e:
            Config(tempfile.mkdtemp(), {"wherefore": 1, "generators": [dict(MATERIALIZE)], "sources": {"spec": {
                "path": "spec.json", "adapter": "params", "store": ok, "schema": {"a.*": "number"}, "why": "x"}}})
        self.assertIn("one `schema` cannot type both", str(e.exception.code))

    def test_a_store_backed_source_needs_its_generator_and_keeps_it_out_of_the_probe(self):
        ok = {"protocol": "wherefore-store/1", "at": "facts.db"}
        self.refused("declare the generator that materializes it", store=ok, gens=[])
        self.refused('it says "probe": false', store=ok,
                     gens=[{"script": "-m wherefore.facts", "cwd": ".", "makes": "facts.json"}])


# ── the source interface, for a file ────────────────────────────────────────

class AFileSource(unittest.TestCase):
    def test_versions_are_commits_and_provenance_is_the_commit_that_set_it(self):
        root = repo({"facts.json": {"plan": {"price": 89, "name": "Pro"}}})
        first = git(root, "rev-parse", "HEAD").stdout.strip()
        (root / "facts.json").write_text(json.dumps({"plan": {"price": 95, "name": "Pro"}}, indent=1) + "\n")
        git(root, "-c", "user.email=l@w", "-c", "user.name=lee", "commit", "-qam", "the price")
        second = git(root, "rev-parse", "HEAD").stdout.strip()
        src = sources.Files(root, "facts", {"path": "facts.json"})
        self.assertEqual([f.value for f in src.facts(first)], [89, "Pro"])
        self.assertEqual([(k, a.value, b.value) for k, a, b in src.changes(first, second)], [("plan.price", 89, 95)])
        self.assertEqual(src.provenance("plan.price")["version"], second)
        self.assertEqual(src.provenance("plan.price")["decided_by"], "lee")
        self.assertEqual(src.provenance("plan.name")["version"], first)
        self.assertEqual(src.provenance("plan.price", first)["version"], first)

    def test_facts_log_answers_for_a_file_source(self):
        root = repo({"wherefore.json": {"wherefore": 1, "sources": {"facts": {"path": "facts.json", "why": "x"}}},
                     "facts.json": {"plan": {"price": 89}}})
        code, out = wherefore(root, "facts", "log", "plan.price")
        self.assertEqual(code, 0, out)
        self.assertIn("facts:plan.price is 89, a number", out)
        self.assertIn("the commit's author, as git records it", out)
        code, out = wherefore(root, "facts", "pull")
        self.assertEqual(code, 1, out)
        self.assertIn("no source is backed by a store", out)


# ── a corpus whose own script configures the gate ───────────────────────────

SPEC = {"units": "mm",
        "hardware": {"bearing": {"params": {"bore": {"nominal": 8.0, "tol": [0, 0.01], "provenance": "drawing 4"},
                                            "count": {"value": 2, "provenance": "drawing 4"}}}},
        "geometry": {"arm": {"params": {"points": {"value": [[0, 0], [1, 2]], "provenance": "the sketch"}}}}}
SITE = {"company": {"name": "Pendulum Works", "since": 2019}}
ENTRY_INVENTORY = {"authored": {"rules": [["*.py", "code"], ["wherefore.json", "the corpus"],
                                          ["checks/inventory.json", "the inventory"], ["spec/*.json", "THE SOURCES"],
                                          [".gitignore", "bytecode"]]},
                   "captured": {"groups": {}}}


def entry_corpus(sources_decl, spec=None, gate_args=""):
    """The pendulum's shape: `entry` hands the gate to checks/coverage_gate.py,
    which calls gate.configure() itself - and names no schema - while
    wherefore.json declares the sources, a `params` one among them."""
    from _util import scripted
    tree = {"spec/mk3.params.json": spec or SPEC, "spec/site.json": SITE}
    root = scripted(ENTRY_INVENTORY, tree)
    cfg = json.loads((root / "wherefore.json").read_text(encoding="utf-8"))
    if sources_decl is not None:
        cfg["sources"] = sources_decl
    (root / "wherefore.json").write_text(json.dumps(cfg, indent=1) + "\n", encoding="utf-8")
    if gate_args:
        script = root / "checks/coverage_gate.py"
        script.write_text(script.read_text(encoding="utf-8").replace("None, None, gate.COMPARE)",
                                                                     f"None, None, gate.COMPARE, {gate_args})"),
                          encoding="utf-8")
    if git(root, "status", "--porcelain").stdout.strip():
        commit(root)
    return root


def typed_sources():
    return {"spec": {"path": "spec/mk3.params.json", "adapter": "params", "why": "the object",
                     "schema": {"hardware.*": "number", "geometry.arm.points": "array"}},
            "site": {"path": "spec/site.json", "why": "the company",
                     "schema": {"company.name": "string", "company.since": "number"}}}


class AnEntryCorpusIsHeldToItsSchema(unittest.TestCase):
    """0.27.0 typed a source's facts only where configure_from() read
    wherefore.json; a corpus whose own script calls gate.configure() declared
    its schemas and was never checked against them."""

    def test_a_value_of_the_wrong_type_fails_the_gate_naming_the_fact(self):
        bad = json.loads(json.dumps(SPEC))
        bad["hardware"]["bearing"]["params"]["bore"]["nominal"] = "8.0"
        root = entry_corpus(typed_sources(), spec=bad)
        code, out = wherefore(root, "gate")
        self.assertEqual(code, 1, out)
        self.assertIn('spec:hardware.bearing.bore is a string ("8.0"), and the schema says hardware.* is number', out)
        self.assertIn("FAIL 5 facts in 2 sources typed by a schema, 1 fault", out)
        self.assertIn("fix it in spec/mk3.params.json", out)
        r = __import__("subprocess").run([sys.executable, "checks/coverage_gate.py"], cwd=root, capture_output=True,
                                         text=True, env=dict(os.environ, PYTHONPATH=str(SRC)))
        self.assertEqual(r.returncode, 1, "the script run as CI runs it, with no `wherefore` in front")
        self.assertIn('spec:hardware.bearing.bore is a string ("8.0")', r.stdout)

    def test_a_leaves_source_beside_it_is_checked_too(self):
        root = entry_corpus(typed_sources())
        (root / "spec/site.json").write_text(json.dumps({"company": {"name": "Pendulum Works", "since": "2019"}}))
        code, out = wherefore(root, "gate")
        self.assertEqual(code, 1, out)
        self.assertIn('site:company.since is a string ("2019"), and the schema says company.since is number', out)

    def test_the_right_types_pass(self):
        root = entry_corpus(typed_sources())
        code, out = wherefore(root, "gate")
        self.assertEqual(code, 0, out)
        self.assertIn("ok   5 facts in 2 sources typed by a schema, 0 faults", out)

    def test_a_corpus_with_no_schema_sees_no_change(self):
        untyped = typed_sources()
        for s in untyped.values():
            del s["schema"]
        said = []
        for decl in (None, untyped):
            code, out = wherefore(entry_corpus(decl), "gate")
            self.assertEqual(code, 0, out)
            said.append(out)
        self.assertNotIn("typed by a schema", said[0])
        self.assertEqual(said[1], said[0], "declaring sources with no schema changes nothing the gate says")

    def test_a_script_may_name_its_schemas_itself(self):
        root = entry_corpus(None, gate_args="schemas={'site': {'path': 'spec/site.json', "
                                            "'schema': {'company.since': 'string'}}}")
        code, out = wherefore(root, "gate")
        self.assertEqual(code, 1, out)
        self.assertIn('site:company.since is a number (2019), and the schema says company.since is string', out)
        self.assertIn("FAIL 1 facts in 1 source typed by a schema, 1 fault", out)


# ── the commands, on the fixture company ────────────────────────────────────

class TheCommands(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = copy_fixture("cmd")
        store_backed(cls.root)
        git(cls.root, "init", "-q")
        code, out = wherefore(cls.root, "facts", "import", "--decided-by", "fern-founder")
        assert code == 0, out
        cls.imported = out
        code, out = wherefore(cls.root, "facts", "pull")
        assert code == 0, out
        cls.pulled = out

    def test_import_and_pull_say_what_they_did(self):
        self.assertIn("facts: 19 facts from facts.json are version 1 of facts.db, decided by fern-founder",
                      self.imported)
        self.assertIn("19 added, 0 changed, 0 removed since version 0", self.imported)
        self.assertIn("the first pull rewrites its spacing", self.imported)
        self.assertIn("facts.json: 19 facts at version 1 of facts.db (first pull)", self.pulled)
        cfg = json.loads((self.root / "wherefore.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg["sources"]["facts"]["store"]["version"], 1)
        self.assertEqual(json.loads((self.root / "facts.json").read_text(encoding="utf-8")),
                         json.loads((FIXTURE / "facts.json").read_text(encoding="utf-8")))

    def test_set_keeps_a_type_and_the_schema_refuses_one_naming_the_fact(self):
        code, out = wherefore(self.root, "facts", "set", "product.price_usd", "ninety", "--decided-by", "sam")
        self.assertEqual(code, 1, out)
        self.assertIn("facts:product.price_usd is a number (89), and 'ninety' is read as a string", out)
        code, out = wherefore(self.root, "facts", "set", "product.price_usd", "ninety", "--as", "string",
                              "--decided-by", "sam")
        self.assertEqual(code, 1, out)
        self.assertIn('refused: facts:product.price_usd is a string ("ninety"), and the schema says '
                      'product.price_usd is number', out)
        code, out = wherefore(self.root, "facts", "set", "product.price_usd", "89", "--decided-by", "sam")
        self.assertEqual((code, out.strip()), (0, "facts:product.price_usd is already 89: nothing written"))
        code, out = wherefore(self.root, "facts", "set", "product.price_usd.cents", "1", "--decided-by", "sam")
        self.assertIn("product.price_usd is a fact, not an object", out)
        code, out = wherefore(self.root, "facts", "set", "product.price_usd", "95")
        self.assertEqual(code, 2, out)
        self.assertIn("--decided-by WHO", out)


# ── the materialized file, held by the gate ─────────────────────────────────

class WhatSinceDoesWithAStore(unittest.TestCase):
    def test_the_materializer_always_runs(self):
        p = since.Plan(tempfile.mkdtemp(), "HEAD")
        name = "-m wherefore.facts"
        p.entries = {name: {"reads": ["wherefore.json"], "writes": ["facts.json"], "code": []}}
        from wherefore.generators import Gen
        why = since._why_run(p, Gen(name, ".", "facts.json", None, False, True))
        self.assertEqual(why, "it materializes a store: what a store holds is not a file the map can watch")


class TheSameCorpusFromFilesAndFromTheStore(unittest.TestCase):
    """The design's acceptance (docs/scale.md, Stage 3): built once from files
    and once from the reference store, the corpus makes byte-identical
    documents, and the gate and the checks pass on both.

    The store-built copy starts with no facts.json and none of the documents:
    its facts are imported into facts.db from the fixture, the file is deleted,
    and everything after comes out of the store."""

    @classmethod
    def setUpClass(cls):
        cls.files = copy_fixture("files")
        for rel in DOCUMENTS[:3]:
            (cls.files / rel).unlink()
        git(cls.files, "init", "-q")
        cls.built = {"files": wherefore(cls.files, "build")}
        commit(cls.files, "built from files")

        cls.stored = copy_fixture("store")
        store_backed(cls.stored)
        git(cls.stored, "init", "-q")
        cls.imported = wherefore(cls.stored, "facts", "import", "--decided-by", "fern-founder")
        for rel in ("facts.json",) + DOCUMENTS[:3]:
            (cls.stored / rel).unlink()
        cls.pulled = wherefore(cls.stored, "facts", "pull")
        cls.built["store"] = wherefore(cls.stored, "build")
        commit(cls.stored, "built from the store")

    def roots(self):
        return (("files", self.files), ("store", self.stored))

    def test_the_store_was_the_only_source(self):
        self.assertEqual(self.imported[0], 0, self.imported[1])
        self.assertEqual(self.pulled[0], 0, self.pulled[1])
        self.assertIn("facts.json: 19 facts at version 1 of facts.db", self.pulled[1])

    def test_every_document_is_byte_identical(self):
        for rel in DOCUMENTS:
            a, b = (self.files / rel).read_bytes(), (self.stored / rel).read_bytes()
            self.assertEqual(a, b, f"{rel} differs between the corpus built from files and from the store")
        # The facts file itself: the same document, every key in the same place,
        # written in the store's spacing (the fixture keeps one array on a line).
        self.assertEqual(doc(self.files / "facts.json"), doc(self.stored / "facts.json"))
        self.assertEqual((self.stored / "facts.json").read_text(encoding="utf-8"),
                         model.render(json.loads((FIXTURE / "facts.json").read_text(encoding="utf-8"))))

    def test_the_gate_passes_on_both(self):
        for which, root in self.roots():
            code, out = wherefore(root, "gate")
            self.assertEqual(code, 0, f"{which}:\n{out}")
            self.assertIn("UNKNOWN        0", out)
            code, out = wherefore(root, "gate", "--since", "HEAD")
            self.assertEqual(code, 0, f"{which} --since:\n{out}")
        code, out = wherefore(self.stored, "gate")
        self.assertIn("ok   5 generated files, 0 differ from what is committed", out)
        self.assertIn("ok   7 facts in 1 source typed by a schema, 0 faults", out)

    def test_the_checks_pass_on_both(self):
        # Not the fixture's own proof, proofs/origin_proof.py: it plants its
        # fault in facts.json, which in the store-built copy is generated - the
        # build puts the store's facts straight back. A store-backed corpus
        # plants in the store, as proofs/facts_proof.py does.
        for which, root in self.roots():
            for check in ("retired", "reach", "claims", "drift"):
                code, out = wherefore(root, "check", check)
                self.assertEqual(code, 0, f"{which}, {check}:\n{out}")
            code, out = wherefore(root, "check", "decisions", "--base", "HEAD")
            self.assertEqual(code, 0, f"{which}, decisions:\n{out}")
            self.assertEqual(git(root, "status", "--porcelain").stdout.strip(), "", f"{which}: the tree moved")


if __name__ == "__main__":
    unittest.main()
