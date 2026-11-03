"""What a corpus took from elsewhere, still matching where it was taken from.

A captured group is made by hand from something - and sometimes that something
is outside the repository: a copy of another company's published file, counts
taken from another product at one of its versions. The gate cannot see it, and
deliberately does not read it: the gate is offline and deterministic, so the
same tree always gives the same answer. That leaves a copy nobody is watching,
true on the day it was taken and silently old after.

An `upstream` on a captured group says where the copy was taken from - a public
address - and what must still match there:

    "upstream": {
     "url": "https://example.com/",
     "read": {"pattern": "var MODEL=\\"([A-Za-z0-9+/=]+)\\"", "decode": "base64"},
     "matches": "bytes"
    }

`read` takes what the address serves and keeps one part of it - a JSON
pointer (`{"json": "/version"}`), a meta tag (`{"meta": "version"}`), or the
first group of a pattern, optionally base64-decoded - or, with no `read`, all
of it. `matches` says what that part must equal: `"bytes"`, the group's one
file byte for byte; or `{"file": "facts.json", "at": "pack.version"}`, a value
the corpus records, said once, in a tracked JSON file.

`wherefore check upstream` reads each one, now, and fails:

  - MOVED: the source says something else. Take the copy again, from the source
    as it is, record where and when in the same change, and the gate holds it.
    Never move the recorded value alone: that certifies a copy nobody re-made.
  - NO LONGER SAYS: the address answered, and what `read` looks for is not in
    it - the source changed shape, which is a change too.
  - UNREACHABLE: the address did not answer, or answered with an error. This
    fails as well, unless the upstream says `unreachable` - the reason a source
    being down should not stop this corpus - and then it is said and passes.

It is never part of the gate, the build or the pre-push hook: it is the one
command that goes to the network, and is run where that is the point - before
a deploy, so nothing ships with a copy of something that has since changed;
and on a schedule as well, if a source moving between deploys matters.
"""
import base64
import hashlib
import html.parser
import http.client
import json
import re
import urllib.error
import urllib.request

from . import __version__
from .config import ConfigError

READERS = ("json", "meta", "pattern")
TIMEOUT = 30
LIMIT = 10 * 1024 * 1024   # the most of an answer this reads; past it, it refuses
SHOWN = 80                 # the most of a value a MOVED line prints


class TooLarge(Exception):
    """The address answered with more than LIMIT bytes."""


def declared(cfg):
    """[(group name, group, upstream)] for every captured group that names one."""
    groups = cfg.doc.get("inventory", {}).get("captured", {}).get("groups", {})
    return [(n, g, g["upstream"]) for n, g in groups.items() if g.get("upstream")]


def validate(where, up, files):
    """Refuse an upstream that could not be checked, in words."""
    if not isinstance(up, dict):
        raise ConfigError(f"{where}: `upstream` is an object - url, read, matches")
    url = up.get("url")
    if not (isinstance(url, str) and re.match(r"(https?|file):", url)):
        raise ConfigError(f"{where}: `upstream.url` is the address the copy was taken from "
                          f"(https://, http:// or file:), not {url!r}")
    read = up.get("read", {})
    if not isinstance(read, dict) or len(set(read) & set(READERS)) > 1 or \
            set(read) - set(READERS) - {"decode"}:
        raise ConfigError(f"{where}: `upstream.read` takes one of {', '.join(READERS)}, "
                          f"and `decode` with a pattern; it says {read!r}")
    if "json" in read and not (isinstance(read["json"], str) and
                               (read["json"] == "" or read["json"].startswith("/"))):
        raise ConfigError(f"{where}: `upstream.read.json` is a JSON pointer - \"\" for the whole "
                          f"document, or a path that starts with \"/\", such as \"/version\"; "
                          f"it says {read['json']!r}")
    if "decode" in read and (read["decode"] != "base64" or "pattern" not in read):
        raise ConfigError(f"{where}: `upstream.read.decode` is \"base64\", for what a pattern finds")
    if "pattern" in read:
        try:
            if re.compile(read["pattern"]).groups != 1:
                raise ConfigError(f"{where}: `upstream.read.pattern` keeps exactly one group")
        except re.error as e:
            raise ConfigError(f"{where}: `upstream.read.pattern` is not a pattern: {e}")
    matches = up.get("matches")
    if matches == "bytes":
        if len(files) != 1 or any(c in files[0] for c in "*?["):
            raise ConfigError(f"{where}: `upstream.matches` \"bytes\" compares one file, and the "
                              f"group's `files` must name exactly one, with no wildcard")
    elif not (isinstance(matches, dict) and isinstance(matches.get("file"), str)
              and isinstance(matches.get("at"), str) and set(matches) == {"file", "at"}):
        raise ConfigError(f"{where}: `upstream.matches` is \"bytes\", or "
                          f"{{\"file\": ..., \"at\": ...}} - where this corpus records the value")
    if "unreachable" in up and not (isinstance(up["unreachable"], str) and up["unreachable"].strip()):
        raise ConfigError(f"{where}: `upstream.unreachable` is the reason a source being down "
                          f"should not stop this corpus, in words")


class _Meta(html.parser.HTMLParser):
    def __init__(self, name):
        super().__init__()
        self.name, self.found = name.lower(), None

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): v for k, v in attrs}
        if tag == "meta" and self.found is None and \
                (a.get("name") or a.get("property") or "").lower() == self.name:
            self.found = a.get("content")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": f"wherefore/{__version__} (check upstream)"})
    # Read a piece at a time, so an answer past LIMIT is refused before it is
    # all in memory. A read of a given size does not raise when the server
    # closes before the Content-Length it promised, so that is checked here:
    # an answer cut short is not a shorter body, it is no answer.
    body = bytearray()
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        while chunk := r.read(64 * 1024):
            body += chunk
            if len(body) > LIMIT:
                raise TooLarge()
        missing = getattr(r, "length", None)
        if missing:
            raise http.client.IncompleteRead(bytes(body), missing)
    return bytes(body)


def as_text(value):
    """A value as a comparison sees it: a string as itself, anything else as JSON says it."""
    return value if isinstance(value, str) else json.dumps(value)


def shown(text):
    return text if len(text) <= SHOWN else text[:SHOWN - 3] + "..."


def read(body, how):
    """The part of `body` that `how` keeps, as bytes; None when it is not there."""
    if "json" in how:
        try:
            node = json.loads(body)
        except ValueError:
            return None
        for part in [p.replace("~1", "/").replace("~0", "~") for p in how["json"].split("/")[1:]]:
            if isinstance(node, list) and part.isdigit() and int(part) < len(node):
                node = node[int(part)]
            elif isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return None
        return as_text(node).encode()
    text = body.decode("utf-8", errors="replace")
    if "meta" in how:
        p = _Meta(how["meta"])
        p.feed(text)
        return None if p.found is None else p.found.encode()
    if "pattern" in how:
        m = re.search(how["pattern"], text)
        if not m:
            return None
        if how.get("decode") == "base64":
            try:
                return base64.b64decode(m.group(1), validate=True)
            except ValueError:
                return None
        return m.group(1).encode()
    return body


def recorded(cfg, matches):
    """(what the corpus records, where) for a `matches` that names a file and a path."""
    path = cfg.root / matches["file"]
    try:
        node = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigError(f"`upstream.matches` names {matches['file']}, which is not there")
    except ValueError as e:
        raise ConfigError(f"`upstream.matches` names {matches['file']}, which is not JSON: {e}")
    for part in matches["at"].split("."):
        if not isinstance(node, dict) or part not in node:
            raise ConfigError(f"`upstream.matches` reads {matches['at']} from {matches['file']}, "
                              f"which does not say it")
        node = node[part]
    return as_text(node), f"{matches['file']} {matches['at']}"


def short(data):
    return hashlib.sha256(data).hexdigest()[:12]


def judge(cfg, name, group, up):
    """(state, line): state is ok, moved, unread, unreachable or excused."""
    url = up["url"]
    # What this corpus records is read first: a value it does not say is this
    # corpus's fault, and is said without asking the network anything.
    mine = recorded(cfg, up["matches"]) if up["matches"] != "bytes" else None
    try:
        body = fetch(url)
    except TooLarge:
        return "unread", (f"FAIL {name}: {url} answered with more than {LIMIT // (1024 * 1024)} MB, "
                          f"more than `check upstream` reads. Point `upstream.url` at the part "
                          f"the copy was taken from")
    except (urllib.error.URLError, OSError, ValueError, http.client.HTTPException) as e:
        why = getattr(e, "reason", None) or e
        if up.get("unreachable"):
            return "excused", (f"--   {name}: {url} did not answer ({why}). Passed, because "
                               f"{up['unreachable']}")
        return "unreachable", (f"FAIL {name}: {url} did not answer ({why}), so nothing says the copy "
                               f"is still what it was taken from")
    part = read(body, up.get("read", {}))
    if part is None:
        return "unread", (f"FAIL {name}: {url} answered, and no longer says what `read` looks for "
                          f"({json.dumps(up.get('read', {}))}): the source changed shape. Look at it, "
                          f"and take the copy again or read it another way")
    if up["matches"] == "bytes":
        rel = group["files"][0]
        mine = (cfg.root / rel).read_bytes()
        if mine == part:
            return "ok", f"ok   {name}: {rel} is what {url} serves ({short(part)})"
        return "moved", (f"MOVED {name}: {url} now serves something else ({short(part)}) than "
                         f"{rel} ({short(mine)}). Take the copy again from it, record where and when "
                         f"in the same change, and run the gate")
    value, where = mine
    now = part.decode("utf-8", errors="replace").strip()
    if now == value:
        return "ok", f"ok   {name}: {url} says {now}, as {where} records"
    files = ", ".join(group["files"])
    return "moved", (f"MOVED {name}: {url} says {shown(now)}, and {where} records {shown(value)}. "
                     f"Take {files} again from the source as it is now, and record what it says "
                     f"in the same change - "
                     f"never the number alone")


def main(cfg, args):
    if args:
        if args[0] in ("-h", "--help"):
            print("usage: wherefore check upstream")
            return 0
        print(f"::error::wherefore check upstream takes nothing: {' '.join(args)}")
        return 2
    watched = declared(cfg)
    groups = cfg.doc.get("inventory", {}).get("captured", {}).get("groups", {})
    if not watched:
        print(f"nothing captured here names an upstream ({len(groups)} captured groups): "
              f"nothing is derived from elsewhere, or nothing says so")
        return 0
    results = [judge(cfg, n, g, up) for n, g, up in watched]
    for _, line in results:
        print(f"  {line}")
    bad = [s for s, _ in results if s in ("moved", "unread", "unreachable")]
    unwatched = len(groups) - len(watched)
    print()
    if bad:
        print(f"::error::{len(bad)} of {len(watched)} copies taken from elsewhere no longer match where "
              f"they were taken from, or cannot be checked")
        return 1
    ok = sum(1 for st, _ in results if st == "ok")
    excused = len(results) - ok
    said = (f"{ok} of {len(watched)} copies taken from elsewhere still match where they were taken from"
            if excused else f"every copy taken from elsewhere still matches where it was taken from ({ok})")
    if excused:
        said += f"; {excused} could not be checked, and passed for the reason each gives - not checked is not matching"
    if unwatched:
        said += f". {unwatched} captured groups name no upstream"
    print(said)
    return 0
