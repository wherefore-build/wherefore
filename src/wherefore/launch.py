"""Launches that wait: a thing moves to its next stage only when what that stage needs is there.

RELEASE IS NOT LAUNCH. Code can ship any day; what waits is the moment a
thing is said to be ready - a feature in beta, a site launched, a roadmap
item shipped. Each such thing has a stage, as a fact in a source the
company owns. The stages are named once, in order, and each stage names what
must be true of a thing from that stage on: a help doc, a line in the
changelog, its name on the feature page. A pull request that moves a thing
to a stage it does not yet have everything for is red, and the check says
what is missing, in the words the corpus gave it.

    "launch": {
      "of": {"source": "facts", "at": "features", "id": "id", "stage": "stage"},
      "stages": ["building", "beta", "live"],
      "needs": {
        "beta": [{"file": "docs/{id}.md", "why": "a help doc"},
                 {"in": "CHANGELOG.md", "says": "{name} (beta)", "why": "the changelog marks it beta"}],
        "live": [{"in": "site/features/index.html", "says": "{name}", "why": "the feature page"}]
      },
      "until": {
        "beta": [{"in": "site/**", "lacks": "{name}", "why": "nothing public says it before beta"}]
      }
    }

`needs` holds from the stage it is under onward - what beta needs, live
needs too, said once. `until` holds before the stage it is under - nothing
public until beta. A requirement is one of:

    has     the thing's own fact has this field, and it is not empty
    file    a tracked file matches this glob
    says    a tracked file matching `in` says this text
    lacks   no tracked file matching `in` says this text

and says `why`, which is what the check prints when it is missing. `{field}`
in a requirement is the thing's own field (`{id}` and `{stage}` always
exist); a field the thing does not have is a requirement it cannot meet.

WHAT A THING IS. `of` names where the stages live: a source by name, or a
JSON file by `path`; `at`, the list or object of things inside it; `id` and
`stage`, the fields of each. Without `at` there is one thing, the corpus
itself, whose stage is the field `stage` names - a site's draft or launched.

WHAT IS READ: tracked files, the way the gate sees them, generated pages
included - the feature page is what a visitor reads. Markup is read as its
text and as its source, so a name split by a tag still counts.

ONE LADDER, OR SEVERAL. The section above is one ladder, and most corpora
need no more. Things that move differently - features through building,
beta and live; the site through draft and launched - each get a ladder of
their own, by name:

    "launch": {"ladders": {"features": {"of": ..., "stages": [...], "needs": {...}},
                           "site": {"of": ..., "stages": ["draft", "launched"], ...}}}

A thing is on one ladder: two ladders that read the same things are
refused. The check and its JSON say which ladder each thing is on.

`wherefore check launch` fails on a thing at a stage it does not have
everything for; for every other thing it says what the next stage still
waits on. `--json` prints the same, for a reader that draws it.
"""
import fnmatch
import html
import json
import re
import subprocess

from . import scan, sources

FIELDS = ("of", "stages", "needs", "until", "why")
DEFAULT = "default"
OF_FIELDS = ("source", "path", "at", "id", "stage")
KINDS = ("has", "file", "says", "lacks")
MARKUP = (".html", ".htm", ".svg")
FIELD = re.compile(r"\{([A-Za-z0-9_.\-]+)\}")
MISSING = object()


# ── what the section may say ─────────────────────────────────────────────────

def ladders(d):
    """[(name, ladder)]: the ladders the section names, or the one it is.

    A section is one ladder - `of`, `stages`, `needs`, `until` - named
    `default`, which is how most corpora start; or `ladders`, several by name,
    for things that move differently: features through building, beta and live,
    the site through draft and launched."""
    if "ladders" in d:
        return list(d["ladders"].items())
    return [(DEFAULT, d)]


def validate(doc):
    d = doc.get("launch")
    if d is None:
        return
    from .config import ConfigError
    if not isinstance(d, dict):
        raise ConfigError("`launch` is one ladder - `of`, where the stages live; `stages`, in order; "
                          "`needs` and `until`, what each stage requires - or `ladders`, several by name")
    if "ladders" not in d:
        _ladder(d, "launch", doc)
        return
    unknown = set(d) - {"ladders", "why"}
    if unknown:
        raise ConfigError(f"`launch` names `ladders`, so beside it there is only `why`: {', '.join(sorted(unknown))} "
                          f"belong{'s' if len(unknown) == 1 else ''} to a ladder")
    named = d["ladders"]
    if not isinstance(named, dict) or not named:
        raise ConfigError("`launch.ladders` names each ladder: {\"features\": {...}, \"site\": {...}}")
    seen = {}
    for name, ladder in named.items():
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", name):
            raise ConfigError(f"`launch.ladders` names {name!r}: a ladder's name is lower case, digits, `-` and `_`")
        _ladder(ladder, f"launch.ladders.{name}", doc)
        of = ladder["of"]
        rel = (doc.get("sources") or {})[of["source"]]["path"] if "source" in of else of["path"]
        key = (rel, of.get("at"))
        if key in seen:
            raise ConfigError(f"`launch.ladders.{name}` reads the same things as `{seen[key]}` ({rel}"
                              + (f", {of['at']}" if of.get("at") else "") + "): a thing is on one ladder")
        seen[key] = name


def _ladder(d, where, doc):
    """One ladder, said where `where` says."""
    from .config import ConfigError
    if not isinstance(d, dict):
        raise ConfigError(f"`{where}` is a ladder: `of`, `stages`, `needs` and `until`")
    unknown = set(d) - set(FIELDS)
    if unknown:
        raise ConfigError(f"`{where}` has {', '.join(sorted(unknown))}, which it does not take: "
                          f"{', '.join(FIELDS)}")
    stages = d.get("stages")
    if (not isinstance(stages, list) or len(stages) < 2 or len(set(stages)) != len(stages)
            or not all(isinstance(s, str) and s.strip() for s in stages)):
        raise ConfigError(f"`{where}.stages` is the stages in order, at least two, each named once: "
                          "[\"building\", \"beta\", \"live\"]")
    of = d.get("of")
    if not isinstance(of, dict):
        raise ConfigError(f"`{where}.of` says where each thing's stage lives: "
                          "{\"source\": \"facts\", \"at\": \"features\", \"id\": \"id\", \"stage\": \"stage\"}")
    unknown = set(of) - set(OF_FIELDS)
    if unknown:
        raise ConfigError(f"`{where}.of` has {', '.join(sorted(unknown))}, which it does not take: "
                          f"{', '.join(OF_FIELDS)}")
    if ("source" in of) == ("path" in of):
        raise ConfigError(f"`{where}.of` names its file one way: `source`, a source in wherefore.json by name, "
                          "or `path`, a JSON file")
    if "source" in of and of["source"] not in (doc.get("sources") or {}):
        raise ConfigError(f"`{where}.of.source` is {of['source']!r}, which is not a source in wherefore.json")
    if not (isinstance(of.get("stage"), str) and of["stage"]):
        raise ConfigError(f"`{where}.of.stage` is the field that holds each thing's stage")
    if "id" in of and "at" not in of:
        raise ConfigError(f"`{where}.of.id` names each thing's field among several (`at`); "
                          "without `at` the one thing is the corpus itself")
    for part in ("needs", "until"):
        block = d.get(part, {})
        if not isinstance(block, dict):
            raise ConfigError(f"`{where}.{part}` maps a stage to what it requires: {{\"beta\": [...]}}")
        for stage, reqs in block.items():
            if stage not in stages:
                raise ConfigError(f"`{where}.{part}` names {stage!r}, which is not one of the stages "
                                  f"({', '.join(stages)})")
            if part == "until" and stage == stages[0]:
                raise ConfigError(f"`{where}.until.{stage}` is before the first stage, where nothing is")
            if not isinstance(reqs, list) or not reqs:
                raise ConfigError(f"`{where}.{part}.{stage}` is a list of requirements")
            for i, r in enumerate(reqs):
                _requirement(r, f"{where}.{part}.{stage}[{i}]")


def _requirement(r, where):
    from .config import ConfigError
    if not isinstance(r, dict):
        raise ConfigError(f"`{where}` is an object: one of {', '.join(KINDS)}, and why")
    kinds = [k for k in KINDS if k in r]
    if len(kinds) != 1:
        raise ConfigError(f"`{where}` says {'none' if not kinds else ' and '.join(kinds)} of "
                          f"{', '.join(KINDS)}; a requirement is exactly one")
    kind = kinds[0]
    allowed = {kind, "why"} | ({"in"} if kind in ("says", "lacks") else set())
    unknown = set(r) - allowed
    if unknown:
        raise ConfigError(f"`{where}` has {', '.join(sorted(unknown))}, which a `{kind}` requirement does not take")
    if kind in ("says", "lacks") and not (isinstance(r.get("in"), str) and r["in"]):
        raise ConfigError(f"`{where}` is `{kind}`, so `in` names the files to read, as a glob")
    if not (isinstance(r[kind], str) and r[kind].strip()):
        raise ConfigError(f"`{where}.{kind}` is text")
    if not (isinstance(r.get("why"), str) and r["why"].strip()):
        raise ConfigError(f"`{where}` has no `why`: what it is for, which is what the check says when it is missing")


# ── the things, and their stages ─────────────────────────────────────────────

def _get(fields, dotted):
    try:
        return sources.value(fields, dotted)
    except (KeyError, IndexError, TypeError, ValueError):
        return MISSING


def things(cfg, d):
    """[{id, stage, fields}] for every thing a ladder names, in the source's order."""
    of = d["of"]
    rel = cfg.doc["sources"][of["source"]]["path"] if "source" in of else of["path"]
    doc = json.loads((cfg.root / rel).read_text(encoding="utf-8"))
    if "at" not in of:
        return [{"id": cfg.name, "stage": _get(doc, of["stage"]), "fields": doc}], rel
    node = _get(doc, of["at"])
    if isinstance(node, dict):
        items = [(str(k), v) for k, v in node.items()]
    elif isinstance(node, list):
        items = [(None, v) for v in node]
    else:
        from .config import ConfigError
        raise ConfigError(f"`launch.of.at` is {of['at']!r}, which is not a list or an object in {rel}")
    out = []
    for key, item in items:
        if not isinstance(item, dict):
            continue
        ident = _get(item, of.get("id", "id"))
        ident = key if ident is MISSING and key is not None else ident
        out.append({"id": str(ident), "stage": _get(item, of["stage"]), "fields": item})
    return out, rel


# ── what is said, where ──────────────────────────────────────────────────────

def _tracked(root):
    out = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, text=True).stdout
    return [p for p in out.split("\0") if p]


def _norm(text):
    return " ".join(text.split())


class Corpus:
    """The tracked files, read once each: as source, and markup as its text too."""

    def __init__(self, root):
        self.root, self.files, self._read = root, _tracked(root), {}

    def matching(self, glob):
        return [f for f in self.files if fnmatch.fnmatch(f, glob)]

    def texts(self, rel):
        if rel not in self._read:
            raw = (self.root / rel).read_bytes()
            if b"\0" in raw[:4096]:
                self._read[rel] = []
            else:
                src = raw.decode("utf-8", "replace")
                got = [_norm(src)]
                if rel.lower().endswith(MARKUP):
                    got.append(_norm(html.unescape(src)))
                    got.append(_norm(" ".join(line for _, line in scan.read_markup(src, svg=rel.lower().endswith(".svg"))[0])))
                self._read[rel] = got
        return self._read[rel]

    def says(self, glob, text):
        """The first tracked file matching `glob` that says `text`, or None."""
        want = _norm(text)
        for f in self.matching(glob):
            if any(want in t for t in self.texts(f)):
                return f
        return None


def _fill(template, thing):
    def one(m):
        name = m.group(1)
        v = thing["id"] if name == "id" else thing["stage"] if name == "stage" else _get(thing["fields"], name)
        if v is MISSING or isinstance(v, (dict, list)) or v is None:
            raise LookupError(name)
        return str(v)
    return FIELD.sub(one, template)


def judge(req, thing, corpus):
    """(held, what was found) for one requirement of one thing."""
    kind = next(k for k in KINDS if k in req)
    try:
        if kind == "has":
            v = _get(thing["fields"], req["has"])
            ok = v is not MISSING and v not in (None, "", [], {})
            return ok, (f"its `{req['has']}` is there" if ok else f"it has no `{req['has']}`")
        if kind == "file":
            glob = _fill(req["file"], thing)
            hit = corpus.matching(glob)
            return bool(hit), (hit[0] if hit else f"no tracked file is {glob}")
        glob, text = _fill(req["in"], thing), _fill(req[kind], thing)
    except LookupError as e:
        return False, f"it has no `{e.args[0]}` to say"
    hit = corpus.says(glob, text)
    if kind == "says":
        return hit is not None, (f"{hit} says “{text}”" if hit else f"nothing in {glob} says “{text}”")
    return hit is None, (f"nothing in {glob} says “{text}”" if hit is None else f"{hit} says “{text}”")


def find(cfg):
    """Every ladder; on each, every thing, its stage, and every requirement that applies now and at the next stage."""
    corpus = Corpus(cfg.root)
    return {"ladders": [dict(name=name, **_climb(cfg, d, corpus)) for name, d in ladders(cfg.doc["launch"])]}


def _climb(cfg, d, corpus):
    stages, needs, until = d["stages"], d.get("needs", {}), d.get("until", {})
    listed, rel = things(cfg, d)
    out = []
    for t in listed:
        row = {"id": t["id"], "stage": t["stage"] if t["stage"] is not MISSING else None,
               "now": [], "next": None, "known": t["stage"] in stages}
        if row["known"]:
            at = stages.index(t["stage"])
            for i, stage in enumerate(stages):
                for req in needs.get(stage, []) if i <= at else ():
                    held, said = judge(req, t, corpus)
                    row["now"].append({"part": "needs", "stage": stage, "why": req["why"], "held": held, "said": said})
                for req in until.get(stage, []) if i > at else ():
                    held, said = judge(req, t, corpus)
                    row["now"].append({"part": "until", "stage": stage, "why": req["why"], "held": held, "said": said})
            if at + 1 < len(stages):
                nxt = stages[at + 1]
                # What moving on would ask: the next stage's needs, and the end of its `until`.
                wants = []
                for req in needs.get(nxt, []):
                    held, said = judge(req, t, corpus)
                    wants.append({"part": "needs", "stage": nxt, "why": req["why"], "held": held, "said": said})
                row["next"] = {"stage": nxt, "wants": wants, "ready": all(w["held"] for w in wants)}
        out.append(row)
    return {"stages": stages, "of": rel, "things": out}


# ── the check ────────────────────────────────────────────────────────────────

def _report(lad, named):
    """(lines, faults, things short, things ready) for one ladder; `named` puts its name on each fault."""
    lines, faults, short, ready = [], 0, 0, 0
    who = f"{lad['name']}: " if named else ""
    width = max([len(t["id"]) for t in lad["things"]] + [8])
    stw = max(len(s) for s in lad["stages"])
    for t in lad["things"]:
        if not t["known"]:
            faults += 1
            short += 1
            lines.append(f"::error::{who}{t['id']} is at {t['stage']!r}, which is not one of the stages "
                         f"({', '.join(lad['stages'])}) - say one in {lad['of']}")
            continue
        missing = [r for r in t["now"] if not r["held"]]
        for r in missing:
            faults += 1
            when = f"from {r['stage']} it needs" if r["part"] == "needs" else f"until {r['stage']},"
            lines.append(f"::error::{who}{t['id']} is {t['stage']}, and {when} {r['why']}: {r['said']}")
        if missing:
            short += 1
            continue
        held = len(t["now"])
        tail = ""
        if t["next"]:
            nxt = t["next"]
            if not nxt["wants"]:
                tail = f"; {nxt['stage']} asks nothing more"
            elif nxt["ready"]:
                ready += 1
                tail = f"; ready for {nxt['stage']}"
            else:
                tail = f"; {nxt['stage']} waits on " + "; ".join(w["why"] for w in nxt["wants"] if not w["held"])
        lines.append(f"  ok   {t['id']:<{width}}  {t['stage']:<{stw}}  {held} held{tail}")
    return lines, faults, short, ready


def report(found):
    named = len(found["ladders"]) > 1
    lines, faults, short, ready, n = [], 0, 0, 0, 0
    for lad in found["ladders"]:
        got = _report(lad, named)
        if named:
            lines.append(f"{lad['name']}  {' · '.join(lad['stages'])}  ({lad['of']})")
        lines += got[0]
        faults, short, ready, n = faults + got[1], short + got[2], ready + got[3], n + len(lad["things"])
    where = f"on {len(found['ladders'])} ladders" if named else f"in {found['ladders'][0]['of']}"
    if faults:
        lines.append(f"\n{short} of {n} thing{'s' if n != 1 else ''} lack{'s' if short == 1 else ''} what "
                     f"{'its stage needs' if short == 1 else 'their stages need'} ({faults} missing): "
                     f"a stage moves only when what it needs is there")
        return "\n".join(lines), 1
    lines.append(f"\nok   {n} thing{'s' if n != 1 else ''} {where}, each at a stage it has everything for"
                 + (f"; {ready} ready for the next" if ready else ""))
    return "\n".join(lines), 0


def main(cfg, args):
    if args and args[0] in ("-h", "--help") or set(args) - {"--json"}:
        print("usage: wherefore check launch [--json]")
        return 0 if args and args[0] in ("-h", "--help") else 2
    if cfg.doc.get("launch") is None:
        if "--json" in args:
            print(json.dumps({"ladders": []}, indent=1))
            return 0
        print("ok   no launch section: nothing here waits on a stage. Declare one in wherefore.json - "
              "where each thing's stage lives, the stages in order, and what each needs")
        return 0
    found = find(cfg)
    if "--json" in args:
        print(json.dumps(found, indent=1, ensure_ascii=False))
        return 1 if any(not t["known"] or not all(r["held"] for r in t["now"])
                        for lad in found["ladders"] for t in lad["things"]) else 0
    text, code = report(found)
    print(text)
    return code
