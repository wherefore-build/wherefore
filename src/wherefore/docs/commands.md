# Commands

Every command finds its corpus by looking for `wherefore.json` in the working
directory and above it, or in `WHEREFORE_ROOT`. Each exits 0 when what it
judges holds, 1 when it does not, and 2 for a line it cannot act on. The
examples below are run on the example company, fernhollow-kettles, on every
change to the engine, and must print what they say.

## wherefore scan

```
wherefore scan PATH|URL ... [--json] [--all] [--max-pages N]
```

The first win, with nothing set up. Point it at what a company publishes - a
built site, a docs folder, exported notes, or a live address - and it reads
what a person reads there, finds every value stated in words, and reports
each statement whose copies disagree, the commonest value first and every
place it was said. Given several places, it tags each statement with where it
came from and says what the places state in common and where any two
disagree. Under the first line it says what each place contributed, and the
kinds of file it saw and did not read. Source code is read for its string
literals; stylesheets, style attributes and drawings for their colours, which
it counts and groups by shade. A table - two values said in the same files
alike - is set apart from the stale copies. `--all` reads files that are
history by name, such as a changelog; `--max-pages` bounds a crawl, fifty by
default. Exits 1 when any statement disagrees.

```
$ wherefore scan .
8 stated values in 11 files or pages; 0 statements whose copies disagree
  read  .: 6 .py, 2 .svg, 1 .md, 1 .txt, 1 .html · not read: 3 .json, 1 .gitignore
…
Every statement found says one thing everywhere it is said.
```

## wherefore init

```
wherefore init [DIR]
```

Writes a `wherefore.json` that declares nothing yet, the skill where Claude
Code and Codex read it, and `.github/workflows/wherefore-pin.yml`, the
repository's own watch for the engine's releases, in the directory given or
the current one. It refuses a directory that already has a `wherefore.json`.
The skill's `start.md` is how the first fact is compiled; from the first
build on, the skill is regenerated from the release the repository pins. The
watch is the repository's from then on: every few hours it asks PyPI for the
newest release, moves the pin, rebuilds, and opens a draft pull request whose
checks say what the corpus still has to describe. Two settings in its header
are the repository's to make.

## wherefore gate

```
wherefore gate [--keep]
wherefore gate --since REF [--keep]
wherefore gate --restamp GROUP
```

The coverage gate: every tracked file must be generated during this run,
authored under a rule in the inventory with a reason, or captured and stamped
with what it was made from. It runs every generator twice and requires the
second run to change nothing, compares every generated file with what is
committed, and names each file nobody wrote and nobody claimed. The tree is put
back unless `--keep`. `--restamp GROUP` records a re-made capture against its
sources, for a group a person has just re-made by hand.

```
$ wherefore gate
15 tracked files; 4 generators
…
  ok   4 generated files, 0 differ from what is committed
  ok   the corpus settles: a second regeneration moves 0 files
…
every tracked file is classified, and every generated one was written
during this run and matches what is committed
```

`--since REF` judges a change by what it can reach. REF is a commit the full
gate passed: in a pull request, its base. A generator runs when its script,
a file it reads or a file it writes changed since REF, when a generator
before it in this run rewrote a file it reads, or when what it reads is not
observed - a command, not Python, or the generator that materializes a store
(`wherefore facts pull`), since what a store holds is no file the map can
watch. Every other generator is skipped, and the
files it wrote are taken as generated, at the bytes committed. Every tracked
file is still classified, and the ones that ran are still compared and
settled; a skipped generator whose input the run rewrote runs in the second
pass.

What each generator reads and writes comes from the corpus's own map:
`wherefore graph --json PATH`, declared as a generator, so the full gate keeps
it current like any file it builds and nobody keeps it by hand. Under
`--since` the map is not run, since running it runs everything; it is
composed from this run and the map at REF, and compared like any other file.
Every generator runs instead - a full gate, and it says why - when there is
no map at REF, another release of the engine wrote it, the generators are not
the ones it names, a file was added or removed, the tree holds a file git
neither tracks nor ignores, a generator reads the map, or `wherefore.json` or
anything else that tells the gate what to do changed.

```
$ wherefore gate --since HEAD
15 tracked files; 4 generators
since HEAD: every generator runs - no generator writes the map (`wherefore graph --json PATH`), so there is nothing to skip by
…
every tracked file is classified, and every generated one was written
during this run and matches what is committed
```

The map holds what Python's `open()` was seen reading. A file a generator
reads through a shell, a C extension, or from outside the tree is not in it,
so a change to that file alone is skipped and passes. The engine's
`proofs/since_proof.py` shows it, in the case "a read through a shell". So
`--since` is for pull requests, and the full gate stays the backstop: run it
on main and on a schedule, where a file `--since` trusted and the full gate
finds stale fails, naming the generator whose read the map missed.

## wherefore build

```
wherefore build
```

The roll: every generator, in order, twice, compared with what is committed,
and the results left in place so the diff shows exactly what a change to a
fact moves. The same judgement as the gate, with the tree left as the
generators wrote it.

## wherefore list

```
wherefore list
```

Runs every generator once and says what each wrote: which tracked files, and
whether any write went to a path git does not track.

```
$ wherefore list
4 generators, in order
…
4 tracked writes, 0 writes to paths git does not track
```

## wherefore graph

```
wherefore graph [--html PATH] [--json PATH|-] [--theme CSS ...] [--home URL [WORDS]]
```

What builds what. Runs every generator once, traces what each reads and
writes, and draws one self-contained page - every source, script and file,
with the lines between them - changing nothing. `--json` writes the same as
data, or prints it with `-`. `--theme` draws it in a stylesheet's custom
properties, so a corpus publishes its map in its own brand; `--home` puts a
way back to the site on it. A corpus whose generator is itself `wherefore
graph` is credited with that file rather than run, so a map never maps itself
without end.

## wherefore prove

```
wherefore prove [SCRIPT ...]
```

Runs the corpus's proofs, in place, one at a time: each plants the fault its
check exists to catch, runs the check, requires it to fail naming the fault,
and puts the tree back. A check nobody has seen fail is not trusted.

```
$ wherefore prove
…
1/1 proofs held
```

## wherefore check retired

```
wherefore check retired
```

Nothing a person reads may still say a retired value or phrase. The register
lives in the source; the `retired` section says where, and which files a
person reads.

```
$ wherefore check retired
…
nothing anywhere still claims a retired value or a retired phrase
```

## wherefore check reach

```
wherefore check reach
```

Every fact, moved one at a time, must reach what it should: the probe nudges
each fact, regenerates, and requires something a visitor receives to change.
A fact that moves nothing is dead, or copied by hand into a generator; a fact
a published page states reaches it by declaration. Every exemption carries a
reason.

```
$ wherefore check reach
…
every fact probed reaches something a customer receives
```

## wherefore check claims

```
wherefore check claims
```

Every claim says only what its rule allows: a rule names what may be claimed,
of what, and why, and the check fails any page that says more.

```
$ wherefore check claims
…
every claim says only what its rule allows
```

## wherefore check upstream

```
wherefore check upstream
```

Every copy taken from elsewhere still matches where it was taken from, read
there now. A captured group with an `upstream` names the address and what
must still match; the check fails MOVED when the source says something else,
NO LONGER SAYS when the source changed shape, and UNREACHABLE when it does
not answer, unless the group says why that should not stop the corpus. It goes
to the network: before a deploy, never in the gate. A corpus that configures
the engine in its own scripts (`entry`) is read the way its gate reads it:
the groups are the ones those scripts configure.

```
$ wherefore check upstream
nothing captured here names an upstream (1 captured groups): nothing is derived from elsewhere, or nothing says so
```

## wherefore check palette

```
wherefore check palette
```

Every colour said anywhere is one the brand's source holds, or the file says,
with a reason, whose colours they are. A colour quoted in code is text, not
paint, and passes. A corpus with no brand declines the check with why.

## wherefore check published

```
wherefore check published
```

Every page the company publishes but cannot build - a site on a hosted CMS -
still states the source's facts, read live. A `published` section names each
page and the facts it states as templates; the check fails SAYS OTHERWISE
when the page states another value, quoting it, NOT SAID when the page
states nothing like it, and UNREACHABLE when it does not answer, unless the
entry says why that should not stop the corpus. Before a deploy, and on a
schedule if the client wants one; never in the gate. A published page is a
copy until it is built from the source.

```
$ wherefore check published
nothing here is published without being built: every page a visitor receives is the corpus's own
```

## wherefore check drift

```
wherefore check drift
```

Of the files a person writes by hand - authored, or captured - which state
a value in two or more of them that no source holds? A generated file
restates its sources by construction; a hand-written file that states a
value also stated in another, with no source behind either, is a copy
nobody is keeping current. The check names each such value with the files
that say it and counts them. A `drift` section declares how many the corpus
still allows, with why, and which third-party files are not read; the check
fails when more drift than that, and when fewer do it asks for the number
to come down. Without a section it reports and passes: the first run says
what there is to declare. The map draws the same values beside the files.

```
$ wherefore check drift
ok   nothing drifts: every value said by hand in two or more of 2 files is held by a source
```

## wherefore check launch

```
wherefore check launch [--json]
```

Every thing with a stage - a feature in beta, a site launched, a roadmap
item shipped - held to what its stage needs. The `launch` section names
where each thing's stage lives, the stages in order, what each needs from
then on, and what must not be said before it. The check fails a thing at a
stage it does not have everything for, naming the stage and what is
missing in the section's own words, and for every other thing says what
the next stage still waits on. So a pull request that moves a stage is red
until the stage is earned. With several ladders, each is listed under its
name and a fault names its ladder. `--json` prints every ladder, every thing
on it, its stage, and each requirement held or not, for a reader that draws
it. Without a section it says so and passes.

```
$ wherefore check launch
ok   no launch section: nothing here waits on a stage. Declare one in wherefore.json - where each thing's stage lives, the stages in order, and what each needs
```

## wherefore check decisions

```
wherefore check decisions [--base REF] [--pr N | --approvals FILE]
```

Every fact a change adds, removes or gives another value carries the
decision its rules ask for. The `decisions` section names facts - a source
and a glob of its dotted keys - and who decides them: named GitHub logins,
or any reviewer. The check reads each source a rule names at the base and at
HEAD, as committed, and for each changed key finds every rule that names it;
a key no rule names needs nothing and is listed as such. A decision is a
review on the pull request that is the reviewer's latest that is not a
comment, is APPROVED, is by someone other than the pull request's author, and
was given on the head commit being judged - an approval on an earlier commit
does not count, since the change moved after it, and a dismissed one does not
either. For "reviewer" the account must also have review rights here (GitHub
says OWNER, MEMBER or COLLABORATOR) and not be a bot; a named login counts
whatever GitHub says of it. Nothing typed counts: a commit message, a trailer,
the pull request's body or a comment saying "approved" is never read. It
fails naming each fact, who approved what, and what is missing from whom; a
rule whose glob names no fact fails too, since it guards nothing.

In GitHub Actions it reads the pull request from the event and its reviews
from the REST API with `GITHUB_TOKEN`, and judges the change against the base
the pull request merges onto. `--base REF` names the base instead; `--pr N`
reads pull request N from anywhere `GITHUB_TOKEN` and `GITHUB_REPOSITORY` are
set; `--approvals FILE` reads a stand-in with the API's shape -
`{"author": "sam", "reviews": [...]}`, and `"head"` if the reviews judge
another commit than HEAD - for tests and proofs. With none of them it prints
what the change would need and exits 2: approvals can only be read on a pull
request, and a check that cannot read them does not pass.

```
$ wherefore check decisions --base HEAD
  rule  facts: product.price_usd - fern-founder decides
  rule  facts: company.*, product.*, origin.activities.* - any reviewer who is not the author decides
no fact changed since HEAD: nothing waits on a decision
```

A review changes the verdict without changing the code, so the check must
run again when one is submitted or dismissed: the workflow triggers on
`pull_request_review` as well as `pull_request`. It needs the history, to
read the facts where the change began, and a token that can read the pull
request:

```yaml
on:
  pull_request:
  pull_request_review:
    types: [submitted, dismissed]
permissions:
  contents: read
  pull-requests: read
jobs:
  decisions:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0
      - run: pip install -r requirements-engine.txt
      - run: python3 -m wherefore check decisions
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Make the job a required check, so a pull request that changes a fact
merges only once it is decided. A push after the approval makes the
approval stale, and the run for that push fails until it is approved again.

### Who the author is

The author is the account that opened the pull request, as GitHub records
it - not a name in a commit. GitHub does not let an author approve their own
pull request, and this check does not count it if they do. So a coding agent
that opens pull requests with its owner's own GitHub credentials makes the
owner the author of every one of them, and the owner can then never give the
decision the check asks for. For the check to be satisfiable, the agent acts
under its own identity - a GitHub App or a bot account - and the owner
reviews. That is the point of the check, not a workaround of it: the decision
is a verified account's, never a typed name.

What it cannot see: who pushed each commit. A reviewer who pushes a fact
change to someone else's pull request and then approves it has decided their
own change; GitHub's "require approval of the most recent reviewable push"
is the guard for that.

## wherefore facts import

```
wherefore facts import [FILE] [--source NAME] --decided-by WHO [--note WORDS]
```

A source's facts, from its own file or from FILE, as the next version of the
store behind it (the configuration page, `sources`, says how a source is
backed by one). Each fact is kept with its identity - the source's name and
its dotted key, `facts:product.price_usd` - its type and its value, and the
version records who decided it and when. The import is the whole of the
version: a fact the file does not hold is removed. A fact of a type the
source's schema does not allow is refused, named, and nothing is written; a
file the store already holds writes nothing. It says how many facts were
added, changed and removed, and whether the first pull will rewrite the
file's spacing. Then `wherefore facts pull`.

## wherefore facts set

```
wherefore facts set KEY VALUE [--as TYPE] [--source NAME] --decided-by WHO [--note WORDS]
```

One fact, as a new version of the store, with who decided it. VALUE is read
as JSON - `95`, `true`, `null`, `"a string"` - and as a string when it is not
JSON; `--as string|number|boolean|null` says which is meant. A fact keeps its
type: giving `ninety` for a number is refused unless `--as` says the type is
to change, and a type the schema does not allow is refused either way,
naming the fact. A new key is added where its dotted path says, and a new
item at the end of an array; a key inside a fact, or one that holds other
facts, is refused. The file does not move until it is pulled, and the gate
fails until it is: the store says what the corpus does not.

A store records who decided a version as the words given to it; it does not
verify them. On a pull request, `wherefore check decisions` is what verifies
a decision, and it reads the pulled file's change like any other.

## wherefore facts pull

```
wherefore facts pull [--source NAME]
```

The store's newest version, written to the source's file - the same path and
the same JSON shape a file source has, so every generator reads it as it
always did - and the version pinned in `wherefore.json`. Commit the two
together, with what the build then moves. A version holding a fact of a type
the schema does not allow is not pulled. From then on the gate holds the
file to the store: its generator, `python -m wherefore.facts`, writes the
facts at the pinned version, so a file edited by hand differs from what the
store says there and is named, and when the store has moved past the pin
the generator fails and says so. With several store-backed sources, every
one is pulled unless `--source` names one.

### The store protocol

`wherefore-store/1` is open: any command that speaks it is a store. The
engine starts it in the corpus's root, writes one JSON request per line to
its standard input, and reads one JSON answer per line from its standard
output; when it closes standard input, the store exits. Every answer says
`"ok"`, and one that is false says `"error"`, words a person reads.

```
> {"op": "hello", "protocol": "wherefore-store/1"}
< {"ok": true, "protocol": "wherefore-store/1", "store": "the reference store, SQLite, at facts.db", "head": 2}
> {"op": "facts", "version": 2}
< {"ok": true, "version": 2, "facts": [{"key": "product.price_usd", "path": ["product", "price_usd"],
   "type": "number", "value": 95, "provenance": {"version": 2, "decided_by": "fern-founder",
   "at": "2026-11-22T09:14:03Z"}}, ...]}
> {"op": "changes", "from": 1, "to": 2}
< {"ok": true, "changes": [{"key": "product.price_usd", "was": {...}, "now": {...}}]}
> {"op": "log"}
< {"ok": true, "versions": [{"version": 1, "decided_by": "fern-founder", "at": "...", "note": "", "changed": 19}, ...]}
> {"op": "write", "base": 2, "replace": false, "decided_by": "sam", "note": "",
   "schema": {"product.price_usd": "number"},
   "facts": [{"key": "product.price_usd", "path": ["product", "price_usd"], "type": "string", "value": "ninety"}]}
< {"ok": false, "error": "refused: product.price_usd is a string (\"ninety\"), and the schema says product.price_usd is number", "fact": "product.price_usd"}
```

`head` is the newest version, 0 for an empty store. `facts` lists every fact
at a version in document order, each with the version its value was set at,
by whom and when. `changes` lists every fact whose type or value differs
between two versions. `write` makes one new version: with `replace` the
facts given are all of it; without, they are set and the rest kept. A store
refuses a write whose `base` is not its newest version - another writer
moved it in between - a fact of a type the schema does not allow, naming it,
and a write that changes nothing; and it never changes a version once
written. The engine reads through `hello`, `facts`, `changes` and `log`, and
writes only through `wherefore facts import` and `set`.

The reference store is `python -m wherefore.store PATH`, one SQLite file,
declared with `"at"`. A trigger in the database refuses any change to a
version written, so old versions read back as they were. Kept in the
repository, it is a binary file: two branches that each write it cannot be
merged by git, so the second one is rebased and its `wherefore facts set`
run again. A store anywhere but this machine, authentication, and storing
anything but facts are not in this release.

## wherefore facts log

```
wherefore facts log [KEY] [--source NAME]
```

A source's versions, newest first, with who decided each and how many facts
it changed; for a store, the version the file is pulled at. With KEY, that
fact: its value and type, who decided it and at which version, what the
schema says of it, and every value it has had. A file source answers too:
its versions are the commits that touched it, and who decided a fact is the
author of the commit that last set it, as git records it - which anyone can
type.

```
$ wherefore facts log product.price_usd
facts:product.price_usd is 89, a number
…
history, newest first:
```

## wherefore status

```
wherefore status [--gate] [--json] [--out PATH]
```

Where this repository stands, in one read: what each file is, how many
values drift, where every launch stands, how many facts need a decision to
change, and which engine release it pins.
It judges nothing the other commands do not; it puts their answers in one
place, as a few lines or as JSON. Without `--gate` nothing runs: files are
sorted by what `wherefore.json` declares, and the rest are left for the
gate. With `--gate` the gate runs first, and its verdict and counts are in
the document. `--out` writes the JSON to a file, which is how CI keeps it
for the app to read. A repository with no `wherefore.json` is scanned
instead: how many values it states, in how many files, and how many
disagree.

```
$ wherefore status
fernhollow-kettles
  files    15 tracked: 10 written, 1 captured, 4 for the gate to judge
  drift    0 values said by hand twice with no source, none declared
  launch   no ladders
  decisions 11 of 19 facts need an approval to change, by 2 rules; 1 from someone named
```

## wherefore hook

```
wherefore hook install
wherefore hook pre-push
```

`install` writes a pre-push hook that rolls the corpus before a push that
could move a generated document, and refuses the push if one moved.
`pre-push` is what the installed hook runs; it is not for typing.

## wherefore report

```
wherefore report --title TITLE WORDS ... [--from FILE] [--show | --link]
```

Feedback for the engine's makers - a bug, a question or a request, one topic
each. It writes a title, the words as the body, the release, the corpus's
shape in counts, and the output of a command given with `--from`; never a
file's contents or a path. `--show` prints it and sends nothing; `--link`
prints it with a link that opens the issue filled in, for the person to send;
with neither, it opens the issue with `gh`, signed in, or prints the link.

```
$ wherefore report --title Hello the words --show
# Hello
…
--show: nothing was sent. Show the person; send it only when they say.
```
