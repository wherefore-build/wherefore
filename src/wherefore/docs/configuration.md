# Configuration

`wherefore.json` sits at the root of a corpus and says what the corpus is:
where the facts live, what builds each asset, why every other tracked file is
there, and what each check holds. Every exemption carries a `why`, and the
engine refuses one without it. A section may be kept in its own file and
named with `include`; the engine reads it as if it were here. This page has a
section for each section the engine reads.

## wherefore

The schema this engine reads: `1`. The engine refuses any other.

## name

The corpus's name, as reports and the map say it: `"fernhollow-kettles"`.

## sources

Where the facts live, each with a reason:

```json
"sources": {
 "facts": {"path": "facts.json", "adapter": "leaves",
           "why": "THE SOURCE: every fact the corpus states is here once"}
}
```

`adapter` is `leaves` - a JSON file whose scalars are the facts, named by
their dotted path - or `params`, the pendulum's own parameter schema.

## generators

What builds each asset, in order, each saying what it makes:

```json
"generators": [
 {"script": "landing.py", "cwd": "gen", "makes": "site/index.html, the landing page"},
 {"run": ["node", "site.mjs"], "cwd": "gen", "makes": "the site, by the repository's own tooling"},
 {"script": "notes.py", "cwd": "gen", "makes": "the speaker notes", "stdout_to": "deck/speaker-notes.txt"}
]
```

`script` is a Python file run by the engine's Python; `run` is any command,
its words as a list, with no shell. `cwd` is where it runs. `stdout_to`
captures what it prints as the file it makes. `probe` and `resettle` tune how
the reach probe and the gate's second run treat it, with a `why`. The gate
sees what a generator wrote by comparing the tree before and after.

## not_a_generator

Scripts in the tree that look like generators and are not - a helper, a
one-off - each with why, so the gate does not ask about them.

## inventory

Why every tracked file that is not generated is there:

```json
"inventory": {
 "authored": {"rules": [["*.py", "code: the generators"], ["facts.json", "THE SOURCE"]]},
 "captured": {"groups": {
  "photos": {"files": ["photos/kettle.jpg"], "why": "shot by hand, from the product as it is",
             "upstream": {"url": "https://example.com/spec.json", "read": {"json": "/version"},
                          "matches": {"file": "facts.json", "at": "spec.version"}}}}}
}
```

`authored.rules` are `[pattern, why]` pairs, narrow on purpose: `*.py` is a
reason; `**` is never one. `captured.groups` are files made by hand from
something, stamped with what they were made from; `wherefore gate --restamp`
records a re-made group. A group taken from outside the repository names its
`upstream`: the address, what to `read` there (a JSON pointer, a meta tag, or
a pattern), what it must still `match` (the file's bytes, or a value the
corpus records), and `unreachable`, the reason the source being down should
not stop the corpus. `no_stamp` with why excuses a copy the gate cannot read.

## compare

How a generated file is compared with what is committed when bytes will not
do, by glob, first match wins, each with why:

```json
"compare": [
 {"glob": "deck/*.xlsx", "as": "xlsx-cells", "why": "a workbook's bytes carry its save time"},
 {"glob": "renders/*.png", "as": "picture", "edge_tol": 0.02, "tone_tol": 0.01,
  "why": "a raster differs by rasteriser; held as a picture, measured here"}
]
```

`bytes` is the default. `xlsx-cells` compares a workbook by its cells;
`numbers` with `tol` every number within a tolerance; `picture` and
`html-inlined-pictures` a raster, or a page's inlined pictures, as pictures.
The thresholds are measured on the corpus, not defaults.

## surfaces

Where a person reads, named once and used by the retired and claims checks:

```json
"surfaces": {
 "read": {"include": [["site", "*.html"], ["deck", "*.svg"], [".", "*.md"]],
          "skip": [], "archive": ["CHANGELOG"],
          "why": "everything a customer reads; code is not here"}
}
```

`include` is `[directory, pattern]` pairs; `skip` leaves paths out;
`archive` names files that are history and may say what was.

## retired

What a value or a phrase used to be, and that nothing a person reads may say
it again:

```json
"retired": {
 "register": {"source": "facts", "at": "retired"},
 "surface": "read",
 "assertion_patterns": ["\\$\\s*{v}(?!\\d|[.,]\\d)", "^\\s*{v}\\s*$"],
 "exemptions": [],
 "why": "a fact goes stale as a number and a description as a sentence"
}
```

The register lives in the source, at `at`: its `values` say what a number
was, what replaced it and why; its `phrases` the same for wording.
`assertion_patterns` say how this corpus states a number, with `{v}` for the
value. Each exemption names the file, the value, the text on the line and
why.

## reach

Every fact moved one at a time, and what must move with it:

```json
"reach": {
 "facts": {"source": "facts", "include": ["product.*"], "exclude": [], "why": "every fact the page states"},
 "watched": ["site", "deck"],
 "exclude": [],
 "exempt": {"site.draft_banner": "said on every page while the site is a draft, and nowhere once launched"},
 "unconsumed": {},
 "probes": [{"name": "the price", "fact": "product.price_usd",
             "reaches": "the page and the deck", "files": ["site/index.html", "deck/one-pager.svg"]}],
 "audience": "a customer"
}
```

`watched` is every directory a fact may reach; `probes` name the files a
fact must move; `exempt` excuses a fact with why; `unconsumed` records a fact
proven to reach nothing, as a defect still open, with why. `audience` is who
receives what the probe watches, in the check's own words.

## claims

What may be claimed, of what, and why:

```json
"claims": [
 {"name": "the origin", "trigger": "in Portugal", "surface": "read",
  "may_say": {"assembled": "every kettle is assembled at the bench in Porto"},
  "never": {"made": "the heating element is bought in"},
  "why": "an origin claim has a regulated meaning"}
]
```

A sentence that triggers the claim and names anything but what `may_say`
allows fails, naming the word; `never` says why the rest must not be said.

## palette

Where the brand lives, so every colour said anywhere else fails:

```json
"palette": {"source": "brand/tokens.json", "read": ["gen/**", "site/**"],
            "not_ours": {"site/pendulum/index.html": "the pendulum's own page, in its brand"},
            "why": "a brand is a fact like a price"}
```

Or, for a corpus with no brand, `{"none": "why there is no brand here"}`.
`read` limits what is read; `not_ours` excuses files whose colours are
somebody else's, each with why.

## published

Pages the company publishes but cannot build, and the facts each states:

```json
"published": {
 "pricing": {"url": "https://www.example.com/pricing",
             "why": "the public site, on a hosted CMS marketing edits",
             "states": [{"fact": "plans.pro.trial_days", "as": ["{} day free trial", "{}-day free trial"]},
                        {"fact": "plans.pro.features", "each": true}],
             "unreachable": "the CMS being down is not the page moving"}
}
```

`as` is a template with the value in braces, or several; `each` holds every
item of a list. `source` names the facts when reach does not and the corpus
has more than one.

## motion

Where the feature clips go, and the brand they take, all optional:

```json
"motion": {"out": "site/motion",
           "css": "site/brand.css",
           "vars": {"accent": "--brand-accent"},
           "name": "Wherefore",
           "install": "pip install wherefore-build=={version}",
           "site": "https://wherefore.build/"}
```

`out` is the directory the clips are written to (default `motion/`). `css`
is a stylesheet the clip links, relative to the corpus root, for the brand's
variables and fonts; without one the clip carries plain colours. `vars`
names the variable a role reads when the stylesheet names it differently
from `--ground`, `--surface`, `--line`, `--ink`, `--muted`, `--accent`,
`--font-display`, `--font-body` and `--font-mono`. `name` is the product's
(default Wherefore), `install` the install line with `{version}` where the
version goes, and `site` where the feature pages are.

## proofs

Where the corpus's proofs are: `{"glob": "proofs/*_proof.py"}`. `wherefore
prove` runs each, one at a time, in place.

## hook

What the pre-push hook may skip: `{"skip": ["^docs/"]}`, patterns for paths
that cannot move a generated file. Nothing is skipped unless the corpus says
so.

## entry

For a corpus that configures the engine in Python: the script each command
runs, as `{"gate": "checks/gate.py"}`. That script is where the generator
list, the comparators and the exemptions live, with their reasons; the
engine refuses them here as well.

## messages

The corpus's own words where the engine's are not its: `{"reach_ok": "every
fact probed reaches something a buyer receives"}`.

## observer

Where the engine watches what a generator reads: `{"dir": ".wherefore",
"env_prefix": "WHEREFORE_"}`. Few corpora need to say this.

## temp_prefix

The prefix of the temporary directories the engine makes: `"wherefore-"` by
default.

## units

`"in"` for a corpus whose parameters are inches; the reach probe nudges in
those units.
