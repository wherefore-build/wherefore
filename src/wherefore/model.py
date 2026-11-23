"""A fact, as a model: an identity, a value, a type, and where it came from.

THE SAME FACTS THE `leaves` ADAPTER READS, given a shape a store can hold.
A source is a JSON document; each of its scalars is a fact, named by its
dotted path - `product.price_usd` - exactly as `sources.leaves` names it and
as every check names it. Design: docs/scale.md, Stage 3.

  identity    the source's name and the dotted key: `facts:product.price_usd`.
              Stable for as long as the fact is said in the same place.
  path        where it sits, as a list: an object's key is a string and an
              array's index a number, so `{"a": ["x"]}` and `{"a": {"0": "x"}}`
              are told apart. The dotted key is what people and rules say; the
              path is what puts the document back together.
  type        string, number, boolean or null - and, so an empty object or
              array survives the trip, object or array, which only ever hold
              nothing: a container that holds anything is not a fact, it is
              where facts are.
  value       the JSON value.
  provenance  who decided it, as the store records it - a free string, which
              is a record and not a verification: verification is Stage 2's
              `wherefore check decisions` - and at which version, and when.
              None where the source keeps no such record.

A DOCUMENT AND ITS FACTS ARE ONE THING SAID TWO WAYS. decompose() takes a
document apart into facts, in document order; compose() puts it back, and the
two are exact inverses for any document whose top is an object and in which
no two facts would share a dotted key. render() writes it as text, the one
way a store-backed source's file is written.

A SCHEMA types facts by glob: {"product.price_usd": "number", "company.*":
"string", "origin.note": ["string", "null"]}. `*` matches dots too, as every
glob over dotted keys in the engine does. Every glob that names a fact must
allow its type, and a glob that names no fact is a fault of its own: a
mistyped glob types nothing.
"""
import collections
import fnmatch
import json

TYPES = ("string", "number", "boolean", "null", "object", "array")

Fact = collections.namedtuple("Fact", "source key path type value provenance")
Fact.__new__.__defaults__ = (None,)


def identity(fact):
    """`source:key`, the name a message gives a fact."""
    return f"{fact.source}:{fact.key}" if fact.source else fact.key


class ModelError(ValueError):
    """A document or a set of facts that cannot be what it says."""


def typename(value):
    """The type of a fact's value, or ModelError for one that is not a fact."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, dict) and not value:
        return "object"
    if isinstance(value, list) and not value:
        return "array"
    raise ModelError(f"{value!r} is not one fact: an object or array that holds anything is where facts are")


def decompose(doc, source=""):
    """[Fact] for every fact in `doc`, in document order."""
    if not isinstance(doc, dict):
        raise ModelError(f"{source or 'a source'}: the top of a source is an object, and this is "
                         f"{type(doc).__name__}")
    out, seen = [], {}

    def walk(node, path):
        if isinstance(node, dict) and node:
            for k, v in node.items():
                walk(v, path + [str(k)])
        elif isinstance(node, list) and node:
            for i, v in enumerate(node):
                walk(v, path + [i])
        else:
            key = ".".join(str(p) for p in path)
            if key in seen:
                raise ModelError(f"{source or 'a source'}: two facts would both be called {key!r} "
                                 f"({seen[key]} and {path}): a key with a dot in it names a fact "
                                 f"the dotted key cannot tell from another")
            seen[key] = path
            out.append(Fact(source, key, path, typename(node), node))

    walk(doc, [])
    return out


def compose(facts):
    """The document `facts` say, or ModelError naming the first fact that
    cannot sit where it says. Objects keep the order the facts come in;
    arrays are put in index order, and must run 0, 1, 2 ... with no gap."""
    root = {}                       # segment -> child; a leaf is ("leaf", value)
    LEAF = object()

    def where(f):
        return identity(f)

    for f in facts:
        path = list(f.path or [])
        if not path:
            raise ModelError(f"{where(f)} has no path: a fact sits somewhere in the document")
        if f.type not in TYPES:
            raise ModelError(f"{where(f)} is of type {f.type!r}, which is not one of {', '.join(TYPES)}")
        if typename(f.value) != f.type:
            raise ModelError(f"{where(f)} says it is {f.type} and holds {f.value!r}, a {typename(f.value)}")
        node = root
        for i, seg in enumerate(path):
            if not isinstance(seg, (str, int)) or isinstance(seg, bool):
                raise ModelError(f"{where(f)}: {seg!r} in its path is neither a key nor an index")
            kinds = {type(k) for k in node}
            if kinds and type(seg) not in kinds:
                raise ModelError(f"{where(f)}: {'.'.join(map(str, path[:i])) or 'the top'} holds both keys "
                                 f"and indexes, so it is neither an object nor an array")
            if i == 0 and isinstance(seg, int):
                raise ModelError(f"{where(f)}: the top of a source is an object, not an array")
            last = i == len(path) - 1
            child = node.get(seg)
            if last:
                if child is not None:
                    raise ModelError(f"{where(f)} is said twice, or sits where other facts are")
                node[seg] = (LEAF, f.value)
            else:
                if isinstance(child, tuple):
                    raise ModelError(f"{where(f)} sits inside {'.'.join(map(str, path[:i + 1]))}, "
                                     f"which is a fact, not an object or an array")
                if child is None:
                    child = node[seg] = {}
                node = child

    def build(node, at):
        if isinstance(node, tuple):
            return node[1]
        if node and isinstance(next(iter(node)), int):
            idx = sorted(node)
            if idx != list(range(len(idx))):
                raise ModelError(f"{at or 'the top'} is an array whose indexes are {idx}, not 0 to "
                                 f"{len(idx) - 1}: an array has no gaps")
            return [build(node[i], f"{at}.{i}") for i in idx]
        return {k: build(v, f"{at}.{k}" if at else k) for k, v in node.items()}

    return build(root, "")


def render(doc, indent=1):
    """The text a store-backed source's file holds: JSON, UTF-8 as written,
    the indent its declaration says (1 by default, as the engine writes its
    own files), and a newline at the end."""
    return json.dumps(doc, indent=indent, ensure_ascii=False) + "\n"


# ── the schema ──────────────────────────────────────────────────────────────

def schema_problem(schema):
    """Why `schema` is not one, or None."""
    if not isinstance(schema, dict) or not schema:
        return ("is an object of globs over the source's dotted keys, each with the type its facts "
                "must be - {\"product.price_usd\": \"number\"}")
    for glob, want in schema.items():
        if not (isinstance(glob, str) and glob.strip()):
            return f"has a glob {glob!r}, which names nothing"
        wants = want if isinstance(want, list) else [want]
        if not wants or not all(isinstance(w, str) and w in TYPES for w in wants):
            return (f"says {glob!r} is {want!r}: a type is one of {', '.join(TYPES)}, or a list of "
                    f"them")
    return None


def allowed(schema, key):
    """[(glob, [types])] for every glob of `schema` that names `key`."""
    out = []
    for glob, want in (schema or {}).items():
        if fnmatch.fnmatchcase(key, glob):
            out.append((glob, want if isinstance(want, list) else [want]))
    return out


def wrong_type(fact, schema):
    """Why `fact` is of a type `schema` does not allow, or None."""
    for glob, wants in allowed(schema, fact.key):
        if fact.type not in wants:
            return (f"{identity(fact)} is {_a(fact.type)} ({json.dumps(fact.value, ensure_ascii=False)}), "
                    f"and the schema says {glob} is {' or '.join(wants)}")
    return None


def check(facts, schema, source=""):
    """Every way `facts` break `schema`: a fact of a type its globs do not
    allow, named by its identity, and a glob that names no fact at all."""
    problems = [w for w in (wrong_type(f, schema) for f in facts) if w]
    for glob in (schema or {}):
        if not any(fnmatch.fnmatchcase(f.key, glob) for f in facts):
            problems.append(f"{source}: the schema's {glob!r} names no fact - a mistyped glob types nothing")
    return problems


def _a(word):
    return f"an {word}" if word[0] in "aeiou" else f"a {word}"
