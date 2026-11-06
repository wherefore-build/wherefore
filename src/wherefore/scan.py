"""`wherefore scan` - where each stated value appears, and where the copies disagree.

THE FIRST WIN NEEDS NO SETUP. Point it at what a company publishes - a built
site, a docs folder, exported deck notes, or a live site's address - and it
reads what a person reads there, finds every value stated in words (a price, a
version, a trial length, a limit, a percentage), and reports each statement
whose copies disagree:

    "start your {} day free trial"   14 in 3 places, 30 in 1

Nothing is declared first. No wherefore.json, no sources, no generators: those
come after, when the scan has shown there is something to hold.

A STATEMENT is a value with real words on both sides of it, keyed by up to two
words each side, so "Start your 14-day free trial" and "Start your 30-day free
trial" are one statement saying two things. A version is keyed by the name in
front of it ("Acme 2.4.0"). What is reported is a STALE COPY: the same statement
in more than one file, saying at most three things, the commonest said at least
as often as all the rest. What is not:

  - identifiers - P-005, V83, S7, 007 - which name things rather than state them;
  - dates, and values after since, until, before, after: history, not a claim;
  - many values each said often - a table of different things sharing words;
  - files that are history by name - a changelog, release notes, a revision
    log - unless asked for with --all;
  - code: script and style, <code> and <pre>, fenced and inline code in Markdown.

It favours missing a disagreement over inventing one: a first scan that reports
nonsense is the last scan anybody runs.

WHAT IT CANNOT SEE: which copy is right. It says which value most places state
and lists every place; deciding is a person's, and once decided the fact belongs
in a source that every copy is built from - which is the rest of Wherefore.

EVERY REPOSITORY AT ONCE. Given more than one place - the site, the app, the
backend, the docs, the deck - every place is tagged with the root it came from, and
the scan also says what the roots STATE IN COMMON: every statement said in
more than one root, and which of those the roots disagree on. "Both say
'start your {} day free trial': site 14, app 30" is the drift between two
teams, which no one repository's own checks can see; it is the first thing
the Team layer shows, with nothing installed.

WHAT IT READ is said beside the result: for every place, how many files of
each kind it read, and the kinds it saw and did not read, so "0 things in
common" between a site and a checkout of icons and vendored READMEs is never
mistaken for agreement. An app's own words count: the scan reads the string
literals out of source code in the common languages - what a program says
to a person - and nothing else of the code.

A TABLE IS NOT A STALE COPY. Two values said on every page alike - a pricing
table with two plans, each column on every page - are two things, not one
thing said two ways; they are reported as tied, apart from the disagreements.

COLOURS are a brand nobody can list. The scan reads the colours a site states -
in its stylesheets, its pages' style blocks and attributes, its drawings - and
says how many there are, and which are within a shade of one another: the
greys that were meant to be one grey. Nothing is declared for it; declaring
the brand, and holding every colour to it, is `wherefore check palette`.

Exit status: 0 when every statement says one thing everywhere, 1 when some
disagree, 2 for a line it cannot act on.
"""
import collections
import html.parser
import json
import pathlib
import re
import sys
import urllib.parse
import urllib.request

TEXT = {".html", ".htm", ".md", ".mdx", ".markdown", ".txt", ".rst", ".svg"}
# Source code, read for the strings a program says to a person, and nothing else.
CODE = {".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".elm", ".rb", ".go", ".java", ".kt", ".swift",
        ".php", ".rs", ".cs", ".vue", ".svelte", ".dart", ".scala", ".ex", ".exs", ".clj", ".hs", ".ml",
        ".c", ".cc", ".cpp", ".h", ".m"}
# Stylesheets, read for their colours and nothing else.
STYLE = {".css", ".scss", ".sass", ".less"}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".next", ".wherefore-engine",
             ".tox", ".mypy_cache", ".pytest_cache"}
HISTORY_FILE = re.compile(r"(?i)^(changelog|changes|history|news|releases?|release[-_]notes|revisions?)\b")

# Where a block of reading ends, so a sentence is never glued to the next one.
BLOCK = {"p", "div", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "td", "th", "tr", "table",
         "br", "section", "article", "header", "footer", "nav", "main", "aside", "figcaption",
         "blockquote", "dt", "dd", "dl", "button", "label", "option", "summary", "details", "title",
         "text", "tspan", "form", "hr", "caption"}
DEAD = {"script", "style", "noscript", "template", "code", "pre"}
# Attributes a person reads: a picture's words, a control's name, a hint.
SAID = ("alt", "title", "aria-label", "placeholder")

MONTHS = {m.lower() for m in (
    "January February March April May June July August September October November December "
    "Jan Feb Mar Apr Jun Jul Aug Sep Sept Oct Nov Dec").split()}
HISTORY = {"since", "until", "before", "after", "was", "were", "formerly", "previously"}
STOP = {"a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with", "at", "by", "is", "are",
        "be", "it", "its", "as", "from", "that", "this"}

TOKEN = re.compile(r"""
    (?P<ident>\b[A-Za-z]{1,4}-?\d+\b|\b0\d+\b)
  | (?P<money>[$€£¥]\s?\d[\d,]*(?:\.\d+)?)
  | (?P<version>\bv?\d+\.\d+\.\d+(?:[-+][\w.]+)?\b|\bv\d+(?:\.\d+)?\b)
  | (?P<pct>\d+(?:\.\d+)?\s?%)
  | (?P<num>\d[\d,]*(?:\.\d+)?(?:/\d+)?)
  | (?P<word>[A-Za-z][A-Za-z'’]*)
""", re.X)


class _Visible(html.parser.HTMLParser):
    """The text a person reads in a page or drawing, one line per block."""

    def __init__(self, svg=False):
        super().__init__(convert_charrefs=True)
        self.lines, self.cur, self.dead, self.svg, self.intext, self.links, self.styles = [], [], 0, svg, 0, [], []

    def flush(self):
        line = re.sub(r"\s+", " ", "".join(self.cur)).strip()
        if line:
            self.lines.append(line)
        self.cur = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in DEAD:
            self.dead += 1
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
        if tag == "link" and "stylesheet" in str(a.get("rel", "")).lower().split() and a.get("href"):
            self.styles.append(a["href"])
        if tag == "meta" and (a.get("name") == "description"
                              or str(a.get("property", "")).startswith("og:")) and a.get("content"):
            self.lines.append(a["content"])
        for k in SAID:
            if a.get(k) and not self.dead:
                self.lines.append(a[k])
        if tag == "text":
            self.intext += 1
        if tag in BLOCK:
            self.flush()
        else:
            self.cur.append(" ")

    def handle_endtag(self, tag):
        if tag in DEAD:
            self.dead = max(0, self.dead - 1)
        if tag == "text":
            self.intext = max(0, self.intext - 1)
        if tag in BLOCK:
            self.flush()
        else:
            self.cur.append(" ")

    def handle_data(self, data):
        if self.dead or (self.svg and not self.intext):
            return
        self.cur.append(data)


def read_markup(src, svg=False, styles=False):
    """(lines, links) of a page: numbered blocks of what a person reads; with
    styles, (lines, links, stylesheets) - the sheets the page links to."""
    v = _Visible(svg=svg)
    v.feed(src)
    v.close()
    v.flush()
    lines = list(enumerate(v.lines, 1))
    return (lines, v.links, v.styles) if styles else (lines, v.links)


def read_text(src):
    """Numbered lines of a Markdown or text file, with its code left out."""
    out, fenced = [], False
    for n, line in enumerate(src.splitlines(), 1):
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
            continue
        if not fenced and line.strip():
            out.append((n, re.sub(r"`[^`]*`", " ", line)))
    return out


STRING = re.compile(r'"((?:[^"\\\n]|\\.)*)"|\'((?:[^\'\\\n]|\\.)*)\'|`((?:[^`\\\n]|\\.)*)`')


def read_code(src):
    """Numbered string literals of a source file that have words in them: what
    the program says to a person. A line too long to be anything but minified
    code is left alone."""
    out = []
    for n, line in enumerate(src.splitlines(), 1):
        if len(line) > 1000:
            continue
        for m in STRING.finditer(line):
            text = next(g for g in m.groups() if g is not None)
            if len(re.findall(r"[A-Za-z]{2,}", text)) >= 2:
                out.append((n, text))
    return out


HEX = re.compile(r"(?<![\w-])#([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![\w-])")
FUNC = re.compile(r"\b(rgba?|hsla?)\(\s*([^)]{3,80})\)")
STYLE_BLOCK = re.compile(r"<style\b[^>]*>(.*?)</style>", re.S | re.I)
STYLE_ATTR = re.compile(r"""\bstyle\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.I)
SVG_PAINT = re.compile(r"""\b(?:fill|stroke|stop-color|flood-color|lighting-color|color)\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.I)


def _channel(v, scale=255):
    v = v.strip()
    if v.endswith("%"):
        return max(0, min(255, round(float(v[:-1]) * 255 / 100)))
    return max(0, min(255, round(float(v) * (255 / scale) if scale != 255 else float(v))))


def colours(text):
    """Every colour stated in a stretch of style, as six lowercase hex digits,
    alpha dropped: the brand as it was typed, not as it was meant."""
    out = []
    for m in HEX.finditer(text):
        h = m.group(1).lower()
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h[:3])
        out.append(h[:6])
    for m in FUNC.finditer(text):
        fn, args = m.group(1).lower(), re.split(r"[,\s/]+", m.group(2).strip())
        args = [a for a in args if a]
        if len(args) < 3:
            continue
        try:
            if fn.startswith("rgb"):
                r, g, b = (_channel(a) for a in args[:3])
            else:
                import colorsys
                hdeg = float(re.sub(r"[a-z]+$", "", args[0]))
                sat, lig = (float(a.rstrip("%")) / 100 for a in args[1:3])
                r, g, b = (round(x * 255) for x in colorsys.hls_to_rgb((hdeg % 360) / 360, lig, sat))
        except ValueError:
            continue
        out.append(f"{r:02x}{g:02x}{b:02x}")
    return out


def colours_in(src, suffix):
    """The colours a file states, read where colours are typed - a stylesheet
    whole; a page's style blocks and style attributes; a drawing's paint - and
    never from prose, where #bad is a word."""
    if suffix in STYLE:
        return colours(src)
    found = []
    for m in STYLE_BLOCK.finditer(src):
        found += colours(m.group(1))
    for m in STYLE_ATTR.finditer(src):
        found += colours(m.group(1) or m.group(2) or "")
    if suffix == ".svg":
        for m in SVG_PAINT.finditer(src):
            found += colours(m.group(1) or m.group(2) or "")
    return found


def _near(a, b, shade=16):
    return all(abs(int(a[i:i + 2], 16) - int(b[i:i + 2], 16)) <= shade for i in (0, 2, 4))


def shades(hexes):
    """Groups of colours within a shade of one another - every channel within
    16 of 256 - each group sorted, darkest first; a colour alone is no group."""
    hexes = sorted(set(hexes))
    parent = {h: h for h in hexes}

    def find(h):
        while parent[h] != h:
            parent[h] = parent[parent[h]]
            h = parent[h]
        return h
    for i, a in enumerate(hexes):
        for b in hexes[i + 1:]:
            if _near(a, b):
                parent[find(a)] = find(b)
    groups = collections.defaultdict(list)
    for h in hexes:
        groups[find(h)].append(h)
    return sorted((sorted(g) for g in groups.values() if len(g) > 1), key=lambda g: (-len(g), g))


def _norm(kind, raw):
    v = raw.replace(" ", "").replace(",", "")
    if kind in ("num", "money", "pct") and "." in v:
        v = v.rstrip("0").rstrip(".") if not v.endswith("%") else v[:-1].rstrip("0").rstrip(".") + "%"
    return v


def statements(lines):
    """(key, value, line, as written) for every value stated with words around it."""
    for n, line in lines:
        toks = [(m.lastgroup, m.group()) for m in TOKEN.finditer(line)]
        if re.match(r"^\s*\d+[.)]\s", line) and toks and toks[0][0] == "num":
            toks = toks[1:]                           # a numbered list's own numbers
        for i, (kind, raw) in enumerate(toks):
            if kind in ("word", "ident"):
                continue
            left = [t[1].lower() if t[0] == "word" else "#" for t in toks[max(0, i - 2):i]]
            right = [t[1].lower() if t[0] == "word" else "#" for t in toks[i + 1:i + 3]]
            if (left and left[-1] in MONTHS) or (right and right[0] in MONTHS):
                continue                              # a date: no two pages need agree on one
            if left and left[-1] in HISTORY:
                continue                              # "since 2.1", "until V80": history, not a claim
            if kind == "version":
                prev = toks[i - 1] if i else None
                if prev and prev[0] == "word" and prev[1][:1].isupper():
                    yield (kind, (prev[1].lower(),), ()), _norm(kind, raw), n, raw
                continue
            real = [[w for w in side if w != "#" and w not in STOP and len(w) > 1] for side in (left, right)]
            if not all(real):
                continue                              # words on both sides, or it is not a statement
            yield (kind, tuple(left), tuple(right)), _norm(kind, raw), n, raw


def _files(root, everything):
    """[(file, how)] for every file under root outside the directories nobody
    reads: how is "text", "code", "style", or None for a kind the scan does not
    read - which is counted, so the report can say what was left."""
    root = pathlib.Path(root)
    found = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file())
    out = []
    for f in found:
        if set(f.parts) & SKIP_DIRS:
            continue
        suffix = f.suffix.lower()
        if suffix in TEXT:
            out.append((f, "text" if everything or not HISTORY_FILE.search(f.name) else None))
        elif suffix in CODE:
            out.append((f, "code"))
        elif suffix in STYLE:
            out.append((f, "style"))
        else:
            out.append((f, None))
    return out


HTML = ("text/html", "application/xhtml+xml")
CSS = ("text/css",)


class OffHost(Exception):
    """A redirect to another host, which a scan does not follow."""


class _SameHost(urllib.request.HTTPRedirectHandler):
    """Follow a redirect only on the host it started from; refuse any other."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        there = urllib.parse.urlsplit(urllib.parse.urljoin(req.full_url, newurl)).netloc
        if there != urllib.parse.urlsplit(req.full_url).netloc:
            raise OffHost(f"redirected to {there}, another host, which a scan does not read")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_SameHost)


def _fetch(url, timeout=15, want=HTML):
    """(content type, text): text is None for an answer that is not of a kind
    wanted - HTML for a page, CSS for a stylesheet - which is not read past its
    headers."""
    req = urllib.request.Request(url, headers={"User-Agent": "wherefore-scan"})
    with _OPENER.open(req, timeout=timeout) as r:
        kind = r.headers.get_content_type()
        if kind not in want:
            return kind, None
        return kind, r.read(2_000_000).decode(r.headers.get_content_charset() or "utf-8", "replace")


def crawl(start, max_pages=50):
    """[(url, lines, error)] for a site: the start page and the pages it links
    to on the same host, breadth first, HTML only. At most max_pages addresses
    are fetched, whatever they turn out to be - a page that links to hundreds
    of downloads costs no more than max_pages requests - and a redirect to
    another host is refused, and reported as not read."""
    host = urllib.parse.urlsplit(start).netloc
    queue, seen, out, fetched = [(start, "page")], {start}, [], 0
    while queue and fetched < max_pages:
        url, what = queue.pop(0)
        fetched += 1
        try:
            kind, body = _fetch(url, want=CSS if what == "style" else HTML)
        except Exception as e:                        # noqa: BLE001 - every failure is reported the same way
            out.append((url, None, str(e) if isinstance(e, OffHost) else f"{type(e).__name__}: {e}", "", what))
            continue
        if body is None:
            continue
        if what == "style":
            out.append((url, None, None, body, "style"))
            continue
        lines, links, styles = read_markup(body, styles=True)
        out.append((url, lines, None, body, "page"))
        for href, kind in [(h, "page") for h in links] + [(h, "style") for h in styles]:
            nxt = urllib.parse.urldefrag(urllib.parse.urljoin(url, href))[0]
            if urllib.parse.urlsplit(nxt).netloc == host and nxt not in seen \
                    and urllib.parse.urlsplit(nxt).scheme in ("http", "https"):
                seen.add(nxt)
                queue.append((nxt, kind))
    return out


def scan(targets, everything=False, max_pages=50):
    """{"sources": n, "stated": n, "unread": [...], "disagree": [group, ...]}."""
    seen = collections.defaultdict(list)
    sources, unread, read = 0, [], []
    contributed = {}                               # root -> what was read there, and what was not
    painted = collections.defaultdict(set)         # colour -> the files that state it
    painted_in = collections.defaultdict(set)      # root -> the colours stated there
    for t in targets:
        root = _root(t)
        got = contributed.setdefault(root, {"read": collections.Counter(), "not_read": collections.Counter()})
        if re.match(r"^https?://", t):
            for url, lines, err, body, what in crawl(t, max_pages):
                if err:
                    unread.append(f"{url}: {err}")
                    continue
                if what == "style":
                    got["read"]["stylesheets"] += 1
                    for c in colours_in(body, ".css"):
                        painted[c].add(url)
                        painted_in[root].add(c)
                    continue
                sources += 1
                read.append(root)
                got["read"]["pages"] += 1
                for c in colours_in(body, ".html"):
                    painted[c].add(url)
                    painted_in[root].add(c)
                for key, value, n, raw in statements(lines):
                    seen[key].append((value, url, n, raw, root))
            continue
        if not pathlib.Path(t).exists():
            unread.append(f"{t}: no such file or directory")
            continue
        for f, how in _files(t, everything):
            suffix = f.suffix.lower() or f.name
            if how is None:
                got["not_read"][suffix] += 1
                continue
            src = f.read_text(encoding="utf-8", errors="replace")
            got["read"][suffix] += 1
            if how in ("style",) or suffix in (".html", ".htm", ".svg"):
                for c in colours_in(src, suffix):
                    painted[c].add(str(f))
                    painted_in[root].add(c)
            if how == "style":
                continue
            if how == "code":
                lines = read_code(src)
            elif suffix in (".html", ".htm", ".svg"):
                lines = read_markup(src, svg=suffix == ".svg")[0]
            else:
                lines = read_text(src)
            sources += 1
            read.append(root)
            for key, value, n, raw in statements(lines):
                seen[key].append((value, str(f), n, raw, root))
    roots = list(dict.fromkeys(read))              # the places actually read, in the order given
    shared = []
    if len(roots) > 1:
        # WHAT THE ROOTS STATE IN COMMON: a statement said in more than one
        # root, with what each root says. Disagreement here is between places,
        # not within one - the drift no single repository's checks can see.
        for (kind, left, right), occ in seen.items():
            by_root = collections.defaultdict(collections.Counter)
            for v, where, n, raw, r in occ:
                by_root[r][v] += 1
            if len(by_root) < 2:
                continue
            says = " ".join(list(left) + ["{}"] + list(right))
            each = {r: [{"value": v, "count": c} for v, c in by_root[r].most_common()] for r in roots if r in by_root}
            agree = len({v for cnt in by_root.values() for v in cnt}) == 1
            shared.append({"says": says, "kind": kind, "roots": each, "agree": agree})
        shared.sort(key=lambda g: (g["agree"], -sum(c["count"] for cs in g["roots"].values() for c in cs), g["says"]))
    groups, tied = [], []
    for (kind, left, right), occ in seen.items():
        counts = collections.Counter(v for v, *_ in occ).most_common()
        if len(counts) < 2 or len({where for _, where, *_ in occ}) < 2:
            continue
        says = " ".join(list(left) + ["{}"] + list(right))
        # A TABLE, NOT A STALE COPY: every value said in exactly the same files
        # - a pricing table's two columns, on every page that has the table -
        # is two things side by side, not one thing said two ways.
        files_of = {v: {w for vv, w, *_ in occ if vv == v} for v, _ in counts}
        if len({frozenset(f) for f in files_of.values()}) == 1:
            tied.append({"says": says, "kind": kind, "values": [v for v, _ in counts],
                         "files": sorted(files_of[counts[0][0]])})
            continue
        # A STALE COPY, NOT A LIST: at most three values, the commonest said at
        # least as often as all the others together. Many values, each said
        # often, is a list of different things that happen to share their words.
        if len(counts) > 3 or sum(c for _, c in counts[1:]) > counts[0][1]:
            continue
        values = []
        for v, c in counts:
            where = [{"in": w, "at": n, "as": raw, "root": r} for vv, w, n, raw, r in occ if vv == v]
            values.append({"value": v, "count": c, "where": where})
        groups.append({"says": says, "kind": kind, "values": values})
    groups.sort(key=lambda g: (-sum(v["count"] for v in g["values"]), g["says"]))
    tied.sort(key=lambda g: (-len(g["files"]), g["says"]))
    out = {"sources": sources, "stated": sum(len(o) for o in seen.values()),
           "unread": unread, "disagree": groups, "tied": tied,
           "read": {r: {"read": dict(c["read"].most_common()), "not_read": dict(c["not_read"].most_common())}
                    for r, c in contributed.items()}}
    if painted:
        out["colours"] = {"distinct": len(painted), "files": len({f for fs in painted.values() for f in fs}),
                          "near": shades(painted), "where": {c: sorted(fs) for c, fs in sorted(painted.items())}}
        if len(contributed) > 1:
            out["colours"]["by_root"] = {r: sorted(painted_in[r]) for r in contributed if painted_in[r]}
    if len(roots) > 1:
        out["roots"] = roots
        out["shared"] = shared
    return out


def _root(target):
    """The place a target names, as the report says it: a host, or the path as given."""
    if re.match(r"^https?://", target):
        return urllib.parse.urlsplit(target).netloc
    return target.rstrip("/") or target


def report(result, limit=20):
    """The scan as a person reads it."""
    lines = []
    d = result["disagree"]
    lines.append(f"{result['stated']} stated values in {result['sources']} files or pages; "
                 f"{len(d)} statement{'s' if len(d) != 1 else ''} whose copies disagree")
    # WHAT EACH PLACE CONTRIBUTED, so a quiet result is read for what it read.
    for root, got in result.get("read", {}).items():
        read = ", ".join(f"{n} {k}" for k, n in got["read"].items()) or "nothing"
        left = list(got["not_read"].items())
        skipped = (" · not read: " + ", ".join(f"{n} {k}" for k, n in left[:6])
                   + (f", and {len(left) - 6} more kinds" if len(left) > 6 else "")) if left else ""
        lines.append(f"  read  {root}: {read}{skipped}")
    for g in d[:limit]:
        total = sum(v["count"] for v in g["values"])
        lines.append(f"\n  \"{g['says']}\"  - said {total} times, {len(g['values'])} ways")
        for v in g["values"]:
            where = [f"{w['in']}:{w['at']}" for w in v["where"]]
            shown = ", ".join(where[:3]) + (f", and {len(where) - 3} more" if len(where) > 3 else "")
            lines.append(f"     {v['value']:<12} {v['count']}x   {shown}")
    if len(d) > limit:
        lines.append(f"\n  ... and {len(d) - limit} more; --json lists every one")
    tied = result.get("tied", [])
    if tied:
        names = ", ".join('"' + g["says"] + '"' for g in tied[:5]) + (f", and {len(tied) - 5} more" if len(tied) > 5 else "")
        lines.append(f"\n{len(tied)} statement{'s' if len(tied) != 1 else ''} say{'' if len(tied) != 1 else 's'} "
                     f"{'two or more' if any(len(g['values']) > 2 for g in tied) else 'two'} things in the same files "
                     f"alike - a table, not a stale copy: {names}")
    c = result.get("colours")
    if c:
        near = c["near"]
        lines.append(f"\n{c['distinct']} colour{'s' if c['distinct'] != 1 else ''} stated in {c['files']} "
                     f"file{'s' if c['files'] != 1 else ''}; {len(near)} group{'s' if len(near) != 1 else ''} within a shade of one another")
        for g in near[:limit]:
            files = sorted({f for h in g for f in c["where"][h]})
            shown = ", ".join(files[:3]) + (f", and {len(files) - 3} more" if len(files) > 3 else "")
            lines.append("  " + " · ".join("#" + h for h in g) + f"   {shown}")
        if len(near) > limit:
            lines.append(f"  ... and {len(near) - limit} more; --json lists every one")
    if "shared" in result:
        shared = result["shared"]
        split = [g for g in shared if not g["agree"]]
        lines.append(f"\n{len(result['roots'])} places read together - {', '.join(result['roots'])} - state "
                     f"{len(shared)} thing{'s' if len(shared) != 1 else ''} in common; "
                     f"they disagree on {len(split)}")
        for g in shared[:limit]:
            said = " · ".join(f"{r}: " + ", ".join(f"{c['value']} ({c['count']}x)" for c in cs)
                              for r, cs in g["roots"].items())
            lines.append(f"  {'DIFFER' if not g['agree'] else 'agree '}  " + '"' + g["says"] + '"  ' + said)
        if len(shared) > limit:
            lines.append(f"  ... and {len(shared) - limit} more; --json lists every one")
    for u in result["unread"]:
        lines.append(f"\n::warning::could not read {u}")
    if d:
        lines.append("\nEach is one fact said more than one way. Decide which is true, say it once in a "
                     "source,\nand build every copy from it: `wherefore init` starts that.")
    else:
        lines.append("\nEvery statement found says one thing everywhere it is said.")
    return "\n".join(lines)


USAGE = "usage: wherefore scan PATH|URL ... [--json] [--all] [--max-pages N]"


def main(argv):
    args, as_json, everything, max_pages = [], False, False, 50
    it = iter(argv)
    for a in it:
        if a in ("-h", "--help"):
            print(USAGE + "\n\n" + __doc__.split("\n\n")[1])
            return 0
        if a == "--json":
            as_json = True
        elif a == "--all":
            everything = True
        elif a == "--max-pages":
            try:
                max_pages = int(next(it))
            except (StopIteration, ValueError):
                print(f"::error::--max-pages takes a number\n{USAGE}")
                return 2
        elif a.startswith("-"):
            print(f"::error::scan does not take {a}\n{USAGE}")
            return 2
        else:
            args.append(a)
    if not args:
        print(f"::error::name a folder, a file or a site's address to scan\n{USAGE}")
        return 2
    result = scan(args, everything=everything, max_pages=max_pages)
    if result["sources"] == 0:
        print(json.dumps(result, indent=1) if as_json else
              "::error::nothing here to read: no page, Markdown or text file\n" + "\n".join(result["unread"]))
        return 2
    print(json.dumps(result, indent=1, ensure_ascii=False) if as_json else report(result))
    split = any(not g["agree"] for g in result.get("shared", []))
    return 1 if result["disagree"] or split else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
