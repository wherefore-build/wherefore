"""`wherefore check published`: a page the company publishes but cannot build still states the source's facts.

SOME PAGES ARE BUILT BY NOBODY. A public site on a hosted CMS that marketing
edits in a form; a listing on someone else's marketplace. The company cannot,
or will not yet, build it from the source - and it states the company's own
facts all the same: the plans, the trial, the prices. It is a copy, edited
where it is published, and it drifts like any copy.

This is the opposite of `upstream`. An upstream is a copy the corpus took from
elsewhere, held to where it was taken from. Here the corpus is the source and
the page is the copy. A `published` section names each such page, why nobody
builds it, and the facts it states, with how each appears there:

    "published": {
     "pricing": {
      "url": "https://www.example.com/pricing",
      "why": "the public site, on a hosted CMS marketing edits; it states the plans the app decides",
      "states": [
       {"fact": "plans.pro.trial_days", "as": ["{} day free trial", "{}-day free trial"]},
       {"fact": "plans.pro.price", "as": "${} per month"},
       {"fact": "plans.pro.features", "each": true}
      ],
      "unreachable": "the CMS being down is not the page moving; a deploy goes ahead and says so"
     }
    }

`fact` is a dotted path into the corpus's facts (the source `reach` names, or
the one `leaves` source, or the page's own `source`). `as` is a template, or
several, with the value in the braces: a page says "14-day free trial" and
the fact is 14. A fact with no `as` must appear as its bare value. `each` is
for a list: every item must appear, in any order.

`wherefore check published` reads each page, now, as a person reads it - the
scan's reader, so script and style are not read and an inline tag does not
break a sentence - fills each template with the source's value, and looks for
it. It fails:

  - SAYS OTHERWISE: the page states the template with another value. It quotes
    what the page says. A person edits the page where it is published, or the
    source, and runs this again.
  - NOT SAID: the page states it with no value at all - the page changed shape,
    or the template is wrong.
  - UNREACHABLE: the page did not answer, unless the entry says `unreachable`
    - the reason the page being down should not stop this corpus - and then
    it is said and passes.

It is never part of the gate, the build or the pre-push hook: it goes to the
network. Run it before a deploy, so nothing ships beside a page that disagrees
with it; and on a schedule if the client wants one, because the drift this
catches happens on the other side, when nobody is deploying. `reach` counts a
fact named here as reaching that page, by declaration, and says so.

A PUBLISHED PAGE IS A COPY UNTIL IT IS BUILT FROM THE SOURCE. Holding it by
reading is the intermediate step; the goal is a page the corpus compiles.
"""
import http.client
import json
import re
import urllib.error

from . import __version__
from .config import ConfigError, _why

FIELDS = ("url", "why", "states", "unreachable", "source")
STATE_FIELDS = ("fact", "as", "each")
SHOWN = 80
HOLE = "wherefore0value0here"   # stands in for the braces while a template is squashed: a word, so the spaces beside it stay


def declared(cfg):
    return cfg.doc.get("published") or {}


def validate(doc):
    """Refuse what cannot be meant, before anything runs - offline, from the gate."""
    pub = doc.get("published")
    if pub is None:
        return
    if not isinstance(pub, dict):
        raise ConfigError("`published` is an object: each key a page nobody here builds, "
                          "with its url, why, and the facts it states")
    for name, page in pub.items():
        where = f"published[{name!r}]"
        if not isinstance(page, dict):
            raise ConfigError(f"{where} is an object: url, why, states, and unreachable if the page "
                              f"being down should not stop this corpus")
        unknown = set(page) - set(FIELDS)
        if unknown:
            raise ConfigError(f"{where} has {', '.join(sorted(unknown))}, which it does not take: "
                              f"{', '.join(FIELDS)}")
        if not (isinstance(page.get("url"), str) and re.match(r"^https?://", page["url"])):
            raise ConfigError(f"{where}.url is the page's address, http or https")
        _why(page.get("why"), f"{where}.why")
        if "unreachable" in page and not (isinstance(page["unreachable"], str) and page["unreachable"].strip()):
            raise ConfigError(f"{where}.unreachable is the reason the page being down should not stop "
                              f"this corpus, or is left out")
        states = page.get("states")
        if not (isinstance(states, list) and states):
            raise ConfigError(f"{where}.states is a list of the facts the page states, one object each: "
                              f"fact, and as or each")
        for i, st in enumerate(states):
            w = f"{where}.states[{i}]"
            if not isinstance(st, dict) or not (isinstance(st.get("fact"), str) and st["fact"]):
                raise ConfigError(f"{w} is an object with `fact`, a dotted path into the facts")
            unknown = set(st) - set(STATE_FIELDS)
            if unknown:
                raise ConfigError(f"{w} has {', '.join(sorted(unknown))}, which it does not take: fact, as, each")
            if "as" in st:
                tpls = st["as"] if isinstance(st["as"], list) else [st["as"]]
                if not tpls or not all(isinstance(t, str) and "{}" in t for t in tpls):
                    raise ConfigError(f"{w}.as is a template with the value in braces - \"{{}} day free "
                                      f"trial\" - or a list of them")
            if "each" in st and st["each"] is not True:
                raise ConfigError(f"{w}.each is true, for a fact that is a list every item of which the page states")


def _source(cfg, page):
    """(name, doc) of the facts a page's statements point into."""
    sources = cfg.doc.get("sources", {})
    name = page.get("source") or (cfg.doc.get("reach") or {}).get("facts", {}).get("source")
    if not name:
        leaves = [n for n, s in sources.items() if s.get("adapter", "leaves") == "leaves"]
        if len(leaves) != 1:
            raise ConfigError("a published page says `source`, the facts it states, when reach names "
                              "none and the corpus has more than one")
        name = leaves[0]
    if name not in sources:
        raise ConfigError(f"published: source {name!r} is not one wherefore.json declares")
    path = cfg.root / sources[name]["path"]
    try:
        return name, json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise ConfigError(f"published: source {name!r} ({sources[name]['path']}) cannot be read: {e}")


def value_at(doc, dotted):
    node = doc
    for part in dotted.split("."):
        if isinstance(node, list) and part.isdigit():
            node = node[int(part)]
        elif isinstance(node, dict) and part in node:
            node = node[part]
        else:
            raise KeyError(dotted)
    return node


def rendered(value):
    """A value as a page would print it: 9.0 is 9, 14 is 14, words are words."""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _squash(text):
    """Lowercase, one space between words, and no space beside punctuation -
    so "14</b>-day", read as "14 -day", is "14-day" like the template."""
    text = re.sub(r"\s+", " ", text).strip().lower()
    return re.sub(r"\s*([^\w\s])\s*", r"\1", text)


def visible(body):
    """What a person reads on the page, as one lowercase stretch of text."""
    from .scan import read_markup
    lines = read_markup(body.decode("utf-8", errors="replace"))[0]
    return _squash("\n".join(line for _, line in lines))


def look(text, template, value):
    """ok, or what the page says in the value's place, or None when it states
    nothing like the template. The braces are kept apart from the squash, so
    "{} day" stays a template with a space in it."""
    tpl = _squash(template.replace("{}", HOLE))
    if tpl.replace(HOLE, _squash(value)) in text:
        return "ok"
    prefix, suffix = tpl.split(HOLE, 1)
    if not prefix and not suffix:
        return None                                   # a bare value: there is no "otherwise" to quote
    # With words before the value, the value is whatever sits between them and
    # the words after; with none, it is the one word before the words after -
    # anything looser reads the sentence's start as the value.
    capture = r"(.{1,40}?)" if prefix else r"(\S+?)"
    m = re.search(re.escape(prefix) + capture + re.escape(suffix), text)
    if not m:
        return None
    return "ok" if _squash(m.group(1)) == _squash(value) else m.group(1).strip()


def shown(s):
    return s if len(s) <= SHOWN else s[:SHOWN - 1] + "…"


def judge(cfg, name, page):
    """[(state, line)] for one page: one line per statement, or one for the page."""
    from .upstream import fetch, TooLarge, LIMIT
    url = page["url"]
    src_name, doc = _source(cfg, page)
    wanted = []
    for st in page["states"]:
        try:
            value = value_at(doc, st["fact"])
        except (KeyError, IndexError, TypeError):
            raise ConfigError(f"published[{name!r}] states {st['fact']}, which {src_name} does not hold")
        tpls = st["as"] if isinstance(st.get("as"), list) else [st["as"]] if "as" in st else ["{}"]
        if st.get("each"):
            if not isinstance(value, list):
                raise ConfigError(f"published[{name!r}] says each of {st['fact']}, which is not a list")
            wanted += [(f"{st['fact']}[{i}]", rendered(v), tpls) for i, v in enumerate(value)]
        else:
            wanted.append((st["fact"], rendered(value), tpls))
    try:
        body = fetch(url)
    except TooLarge:
        return [("unread", f"FAIL {name}: {url} answered with more than {LIMIT // (1024 * 1024)} MB, more than this reads")]
    except (urllib.error.URLError, OSError, ValueError, http.client.HTTPException) as e:
        why = getattr(e, "reason", None) or e
        if page.get("unreachable"):
            return [("excused", f"--   {name}: {url} did not answer ({why}). Passed, because {page['unreachable']}")]
        return [("unreachable", f"FAIL {name}: {url} did not answer ({why}), so nothing says the page still "
                                f"states what the source does")]
    text = visible(body)
    out = []
    for fact, value, tpls in wanted:
        said = None
        for tpl in tpls:
            r = look(text, tpl, value)
            if r == "ok":
                said = ("ok", f"ok   {name}: {url} says {shown(tpl.replace('{}', value))!r}, as {fact} does")
                break
            if r is not None and said is None:
                said = ("otherwise", f"SAYS OTHERWISE {name}: {url} says {shown(tpl.replace('{}', r))!r}, and {fact} is "
                                     f"{shown(value)!r}. The page is a copy edited where it is published: change it "
                                     f"there, or the source, and run this again")
        if said is None:
            how = " or ".join(repr(t) for t in tpls)
            said = ("notsaid", f"NOT SAID {name}: {url} does not state {fact} as {how}: the page changed "
                               f"shape, or the template is wrong")
        out.append(said)
    return out


def main(cfg, args):
    if args:
        if args[0] in ("-h", "--help"):
            print("usage: wherefore check published")
            return 0
        print(f"::error::wherefore check published takes nothing: {' '.join(args)}")
        return 2
    validate(cfg.doc)
    pages = declared(cfg)
    if not pages:
        print("nothing here is published without being built: every page a visitor receives is the corpus's own")
        return 0
    results = []
    for name, page in pages.items():
        results += judge(cfg, name, page)
    for _, line in results:
        print(line)
    states = [s for s, _ in results]
    bad = [s for s in states if s in ("otherwise", "notsaid", "unreachable", "unread")]
    said = sum(1 for s in states if s == "ok")
    excused = sum(1 for s in states if s == "excused")
    n = len(pages)
    tail = "A published page is a copy until it is built from the source: holding it by reading is the step before that."
    if bad:
        print(f"\n::error::{len(bad)} of {len(states)} statements on {n} published page{'s' if n != 1 else ''} "
              f"no longer hold, or could not be read. {tail}")
        return 1
    print(f"\n{said} statement{'s' if said != 1 else ''} on {n} published page{'s' if n != 1 else ''} "
          f"still say what the source says"
          + (f"; {excused} page{'s' if excused != 1 else ''} did not answer, and passed for the reason each gives"
             if excused else "") + f". {tail}")
    return 0
