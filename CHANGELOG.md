# Changelog

Every release of the engine, newest first. A client pins one commit (its
`requirements-engine.txt`), and moving that pin is a pull request its own full
suite judges, so a release reaches no client by itself.

The version is stated in `pyproject.toml`, in `wherefore.__version__` and here,
and `tests/test_version.py` holds the three together until they are one fact.

## 0.22.0 (2026-11-06)

**Many ladders, one by default.** A `launch` section was one ladder: one set
of stages for every thing it held. Things move differently - a feature
through building, beta and live, the site through draft and launched, a
roadmap item through later, next and shipped - so a section may now name
several under `ladders`, each with its own things, stages and needs. The
one-ladder form stays as it was, the default, and most corpora need no
more. A thing is on one ladder: two ladders that read the same things are
refused. The check lists each ladder under its name and a fault names its
ladder; `--json` is now every ladder with the things on it, which is what
the app will draw. A hard change to the JSON, made while nobody reads it.

## 0.21.1 (2026-11-06)

**A stopped build says why, this time truly.** 0.20.1 had the watch quote
the build when the build failed, and the gate when it did not. But a build
exits 1 whenever a release moves a generated file, which is every release,
so the pull request still quoted moved pages: the 0.21.0 pin on the
company's own site opened that way, with the generators' reasons further
up. The watch now quotes each stopped generator's own words, and the gate's
last lines only when nothing stopped. A client with the watch already makes
the same change in its own copy, or takes the template again.

## 0.21.0 (2026-11-06)

**Launches that wait.** Release is not launch: code ships any day, and what
waits is the moment a thing is said to be ready. A `launch` section in
wherefore.json names where each thing's stage lives - a feature's in a
source, a site's own, a roadmap item's - and the stages in order, and what
each stage needs from then on: a field the thing has, a file that exists,
words a page says. It names what must not be said before a stage, too, so
nothing public names a feature still being built. `wherefore check launch`
fails a thing at a stage it does not have everything for, in the words the
section gave each requirement, and for every other thing says what its next
stage still waits on; `--json` prints the same for a reader that draws it.
The engine holds its own roadmap to it: an item is later, then next, then
shipped, and a shipped item names its release, its feature and its
changelog entry. One repository first; across repositories, and a person's
sign-off, are the app's. Off the roadmap, where it was `launch`.

## 0.20.1 (2026-11-06)

**A stopped build says why, in the pull request.** The watch `wherefore
init` writes quoted the gate's last lines when a release stopped the build,
and the gate can only name the files a stopped build left unwritten; the
words the build asked for - a feature this corpus does not describe yet,
in the generator's own terms - were in the build's output, and discarded.
Its first live run, on the company's own site, opened the 0.20.0 pin that
way. The pull request now quotes the build when the build failed, and the
gate when it did not. The watch is the client's from the day `init` writes
it, so a client that already has one makes the same change in its own copy,
or takes the template again.

The reporting doc says the closing note on an issue plays the feature's
clip, as it now does.

## 0.20.0 (2026-11-06)

**Drift, on the map.** The scan, turned on a corpus's own hand-written
files: a value stated in two or more of them that no source holds is drift,
a copy nobody is keeping current. `wherefore check drift` names each such
value with the files that say it and counts them, and the map draws them
beside those files with the count in its legend, so what is not yet
tracked is seen. A `drift` section in wherefore.json declares how many the
corpus still allows, with why, and which third-party files are not read;
the check fails when more drift than that, and when fewer do it asks for
the number to come down, so the allowance only ever falls. Code is not
read: a string in a script is the script's business, and a generator that
restates a source is reach's. Off the roadmap, where it was `drift`.

**Pins are the client's own.** A release reached a client because the
engine's release workflow told it, with a token the engine's makers held and
a list of clients they kept - one company's plumbing, described as a
feature. Now `wherefore init` writes the client a workflow of its own that
asks PyPI for the newest release every few hours, moves the pin, rebuilds,
and opens the draft pull request; the engine tells nobody and keeps no list,
and a client needs nobody's permission to be one. The release workflow's
`clients` job and CLIENTS_TOKEN are gone. A hard change, made while nobody
depends on the old way.

The inbox's closing note on an issue now links the feature's clip on the
company's site, which plays what shipped.

## 0.19.0 (2026-11-06)

**Docs from each release.** The product's docs, compiled from the release
they describe: five pages ship inside the release as data, beside the
commands, the features and the releases, and `wherefore.docs` hands them to
any client. Start is the skill's own start guide, so the person and their
agent read one text. Commands has a section per command with a worked
example on the example company. Configuration has a section per section of
wherefore.json the engine reads. Checks and proofs says what each check
holds, how it fails, and how to prove one. Reporting says what a report
carries and what becomes of it.

The engine's tests hold the pages to the code: every command has its
section and every section is a command; every section of the configuration
the engine reads is documented; every `wherefore` command a page names
exists; and every example is run again and must print what the page says, in
order, so a page cannot show output a command no longer prints. Off the
roadmap, where it was `docs`.

## 0.18.1 (2026-11-06)

**Scan any number of repositories at once.** The scan has taken any number of places
since 0.13.0 - `wherefore scan site app backend docs` reads all four, tags
each statement with where it came from, and says where any two disagree -
and every word about it said two. The feature, the roadmap's ledger, the
skill and the scan's own notes now say what it does, and a test holds four
places. Nothing in the code moved.

## 0.18.0 (2026-11-06)

**The inbox, held.** Six issues were answered by four releases on 6 November
and nothing wrote back to them: no plan when they were taken on, no word when
they shipped, no link from the feature that answered them, and the roadmap
items that carried two of them vanished the release they shipped. GitHub's
"Closes" line closed the issues; nothing of ours did. The owner's rule: this
is the engine's to hold, so it is not missed again.

- **The roadmap is the ledger.** An item no longer leaves when it ships: its
  state becomes `shipped`, with `since` the release and `feature` the
  feature that answers it. An item that answers issues names them
  (`issues`), who asked, and its `plan` - the design intent, written when it
  is taken on. The engine's own tests hold the chain: a shipped item's
  feature names the same issues; a feature's `issues` appear in the ledger;
  a release's `answers` equal the ledger's; and a changelog entry that names
  an issue the ledger does not have fails, which is the case that caught
  nobody on 0.14.0.
- **The release writes back.** `corpus/inbox.py` carries the ledger to the
  issues: on a push to main, the plan onto each issue an open item answers;
  on a release, what shipped onto each issue it answers - the feature, its
  details, how to install, where to read more, and a line an agent reads -
  and then closes the issue. Once each, by a marker in the comment; the
  first run catches up every issue answered before this existed.
- **Every feature has details**: the paragraph a person reads when they open
  it, beside the line they read in a list, and the issues it answers. The
  company's site shows both.
- **The skill** tells an agent that filed a report where to read what became
  of it.

The ledger is backfilled for 0.12.1 through 0.17.0; this release's own run
of the inbox writes the six issues their closing notes.

## 0.17.0 (2026-11-06)

**A page you publish but cannot build** (wherefore-build/wherefore#22). A
public site on a hosted CMS that marketing edits in a form states the
company's facts and nobody builds it from the source; it is a copy, edited
where it is published, and it drifts like any copy. The corpus can now say
so and hold it:

- A `published` section names each such page - its address, why nobody here
  builds it, and the facts it states, each with how it appears there: a
  template with the value in braces (`"{} day free trial"`, or several), a
  bare value, or `each` for a list every item of which must appear.
- `wherefore check published` reads each page live, as a person reads it,
  and fails SAYS OTHERWISE when the page states the template with another
  value - quoting the page - NOT SAID when it states nothing like it, and
  UNREACHABLE when it does not answer, unless the entry says why that should
  not stop the corpus. It goes to the network, so it is never part of the
  gate, the build or the hook: run it before a deploy, and on a schedule if
  the client wants one, since the drift it catches happens on the other side,
  when nobody is deploying.
- `reach` counts a fact named here as reaching that page by declaration, and
  says so (`pub`) instead of calling the fact dead.
- The gate validates the section offline, every reason present, and reads no
  page.

This is the opposite of `upstream`, and an intermediate step: a published
page is a copy until it is built from the source, and the check says so each
time it runs. The skill's section on such pages is now the real instruction.
Off the roadmap, where it was `published`.

## 0.16.1 (2026-11-06)

**A colour quoted in code is not paint.** The company's site shows the
newest release's own output in its hero, and 0.16.0's names two greys it
found on an example site; `wherefore check palette` read them as colours the
page paints and failed the brand. It now blanks what a page quotes - the
contents of `<pre>` and `<code>`, and Markdown's fences and backticks - line
for line, so a quoted colour is text a visitor reads, and a line number still
means the same line. A colour painted beside quoted text fails as before.

## 0.16.0 (2026-11-06)

**The scan says what it read** (wherefore-build/wherefore#19, #20, and the
owner's ask for colours). The first field session trusted a scan that had
read icons and vendored READMEs and none of an app's 4,329 source files, and
reported six disagreements that were pricing tables. Four changes to
`wherefore scan`, none of them to what it asks of you:

- **What each place contributed,** under the first line: for every place,
  how many files of each kind were read, and the kinds it saw and did not
  read, so "0 things in common" comes with "not read: 3357 .elm" beside it,
  or does not.
- **An app's own words.** Source code in the common languages is read for
  its string literals - what a program says to a person, typed whole - and
  nothing else of it. A site and its app can now disagree in the scan.
- **A table is not a stale copy.** Two values said in exactly the same files
  - a pricing table's two columns, on every page that has it - are reported
  as tied, apart from the disagreements, and do not fail the scan.
- **The colours a site states,** before any brand is declared: how many
  distinct colours its stylesheets, its pages' style blocks and attributes and
  its drawings state, and which are within a shade of one another - the
  greys that were meant to be one grey. A live site's own stylesheets are
  fetched for it, each a fetch like any other against `--max-pages`. Prose
  is never read for colours, where #bad is a word.

The skill's words for the scan follow. Off the roadmap, where it was
`scan-read`.

## 0.15.0 (2026-11-06)

**The skill learns from the field.** The first session on a stranger's
company - an app that decided none of the plans it showed, a public site on
a hosted CMS with 17 pricing tables, 14 of them disagreeing with the other 3
and with the app - came back as six reports (wherefore-build/wherefore#17 to
#22), and `start.md` and `SKILL.md` are rewritten from them. The engine's
code does not move; the words that start every corpus do.

- **Scan before you ask** (#18). The start guide now opens with the scan,
  shows the person what it found, and begins the interview from the
  findings: which value is true and who decides it, then what the scan
  missed.
- **Find where each fact is decided before choosing the repository** (#17).
  A new step before the first fact: search the organisation for the phrases
  the scan found, name the repository or system that decides each, and start
  the corpus there. The repository the agent was opened in may only be a
  reader.
- **What the scan cannot see, and reading each finding where it was found**
  (#19). Names, lists and wording; a value alone on its line; an app's words
  in its source code; pages nothing links to. Two values tied on every page
  are a table, not a stale copy. Report only what you have read.
- **Two places at once, and "0 things in common"** (#20). Both files cover
  the two-place scan and its `DIFFER` and `agree` lines, and say that
  "0 things in common" is not agreement until what each place contributed
  has been read.
- **Facts that live in application code** (#21). Three cases in order:
  something owns the fact already, so the app reads it at run time; nothing
  does, so keep it once in the language's own terms and hold the module as
  authored; generate source only when neither works.
- **A page you publish but cannot build** (#22). What to do today - scan it
  with the built surfaces, retire old values, write down that it is a copy -
  and that it is the opposite of `upstream`, which the engine has no check
  for yet. That check, and the scan saying what it read, are on the roadmap,
  each naming its issue and who asked.

## 0.14.0 (2026-11-06)

**One report, with a title** (wherefore-build/wherefore#15). The first real
use of `wherefore report` found what was wrong with it, and this is that
report acted on. Choosing bug, ask or feature asked the reporter for the
maintainers' judgment - whether a thing is a bug or a missing feature depends
on what the engine was meant to do - and an agent chose "feature" for
feedback that was mostly a bug and a question. So there is no kind now:
`wherefore report --title TITLE WORDS ...` is one command for all of it, and
the issue is labelled in triage. The old form is refused with the new one
beside it; nobody else had used it, so it is not kept as an alias.

- The title is its own line, at most 100 characters and never cut; the words
  are the body, so feedback with seven points arrives as seven points, not a
  one-paragraph heading under a title cut mid-word.
- `--link` prints the report and a link that opens the issue filled in, and
  sends nothing even with `gh` signed in: the person reads it there and sends
  it themselves. A report too long for a link GitHub will open says so,
  instead of handing over a link that opens nothing.
- With no corpus, the report says "no corpus here", and with one the engine
  refuses, only that; it no longer quotes the engine's error, which named the
  whole working directory.
- The skill: one report per topic, never one per kind; the agent may draft the
  title and the words from what the person said, shows them with `--show`,
  and sends only when the person says - or hands them `--link`.
- One issue template, Report, in place of three, the same shape as the
  command.

## 0.13.0 (2026-11-05)

**Scan two repositories at once.** `wherefore scan` given more than one
place - the site and the app, the docs and the deck - tags every place with
the root it came from, and says what the roots state in common: every
statement said in more than one root, and which of those the roots disagree
on. "Both say 'start your {} day free trial': site 14, app 30" is the drift
between two teams, which no one repository's own checks can see - the first
thing the Team layer shows, with nothing installed. One place scans as
before. Off the roadmap, where it was `scan2`.

## 0.12.1 (2026-11-05)

**The roadmap says what shipped, and who asked.** Releases that reach every
client has been true since 0.8.0 - the release opens each client's pin pull
request itself - and sat on the roadmap as "next"; it is a feature now, and
off the roadmap, as the roadmap's own test requires. The first request to
come in through `wherefore report feature` is on it, naming the issue and who asked:
an app you log in to and see every repository you connected, what each
builds, what is held, and what is drifting.

## 0.12.0 (2026-11-05)

**Tell us.** A developer tells their agent to ping us, and this is what the
agent runs: `wherefore report bug`, `wherefore report ask` or `wherefore report feature`,
with the words after it and `--from FILE` for a command's output,
writes the report a maintainer needs and nothing private - the release, the
shape of the corpus in counts, the output given, the person's words, never a
file's contents - prints it whole, and opens it as an issue on
wherefore-build/wherefore with `gh`, or prints a link that opens it filled in.
`--show` sends nothing; the skill tells an agent to run that first and show
the person. Issues are the inbox for all three; what becomes a feature is the
maintainers' call, and the roadmap item that answers an issue may now say who
asked (`asked_by`). Three issue templates give a person the same shape by hand.

## 0.11.0 (2026-11-05)

**The map says what it is.** Three things the company's owner saw on the
site's own map, made the engine's.

- "Written by hand" said a person, and most of it is written by agents: the
  map now says *written, not built* - by a person or by an agent, and never
  regenerated, so it is current only while someone keeps it so. The page's
  foot says the opposite of itself: nothing on it is written, all of it is
  built.
- `wherefore graph --home URL [WORDS]` puts a way back on the map, to the
  site it is of, in WORDS or in the corpus's name.
- A theme gets two marks beside the accent: `--mark`, what the map marks with
  (the bar down a script's card), and `--em` with `--em-mark`, the headline's
  word and the highlighter behind it. A brand whose accent is a highlighter -
  lime on white - writes with its ink and marks with its accent, and the word
  takes the brand's colour again.

The roadmap gains *drift, on the map* (later): what the scan finds, drawn
beside the files that say it, so what is not yet tracked is seen shrinking.

## 0.10.1 (2026-11-05)

**The gate's palette notice reads nothing it did not read to judge.** 0.10.0
had the gate read every tracked text file to count the colours said, which
widened what the gate opens - and the first client holds its gate to exactly
that, recording every file a job reads against the files its rules promise it
never does. The notice now counts colours only in the files the build made,
which the gate wrote and compared anyway, and says so: "colours are said in N
files the build made". A courtesy must not change what a command touches.

## 0.10.0 (2026-11-05)

**One palette.** A brand is a fact like a price, and a colour typed anywhere
else is the brand said twice. `wherefore check palette` reads every tracked
text file and fails a colour literal - #hex, rgb(), hsl() and their kin, a
named colour on a colour property - that is not one of the values the brand's
source holds, naming the file and the line.

- Declared in `wherefore.json`: `palette.source`, the JSON file the colours
  live in (every #RRGGBB string in it, wherever it sits, is the brand's);
  `read`, globs that limit what is read; `not_ours`, files whose colours are
  somebody else's, each with why. A corpus with no brand declines it:
  `{"none": why}`.
- On by default: a corpus that declares neither fails the check in words, and
  the gate - which never fails for it - says when colours are said in more
  than one file and no palette is declared. The company's site had to ask for
  this; nobody should have to.

## 0.9.0 (2026-11-05)

**The map in the corpus's own colours.** `wherefore graph --theme CSS`, which
may be given more than once, puts the stylesheets where the page's own light
and dark palettes were, so the page's rules read the corpus's custom
properties instead: `--ground`, `--surface`, `--line`, `--ink`, `--muted`,
`--accent`, `--accent-ink`, `--lit`, `--gen`, `--capt`, `--hand`, `--unk`,
`--bad`, `--sans`, `--serif`, `--mono` and `--r`. A corpus that holds its
brand in one place need not carry a second palette typed into the engine - the
company's site found the engine's dark accent was its own accent, typed twice.
A map generator that names a theme is still credited rather than run.

## 0.8.0 (2026-11-05)

**The map credits itself.** A corpus may publish its own map: a `run`
generator that is `wherefore graph --html site/map/index.html`, so the page is
built, committed and judged like any other generated file, and a site can link
to the whole chain of what builds it.

- Under the gate it runs as any command does, and the page it writes is the
  same bytes on every run, so the gate holds it.
- Under `wherefore graph` it is not run - the map runs every generator, and
  that one would run the map, without end. It is credited with the files its
  `--html` and `--json` name instead, as their generator, with its reads not
  observed. Its command is recognised as `wherefore graph` or
  `python -m wherefore graph`; anything else runs as before.

## 0.7.0 (2026-11-04)

**What builds what.** `wherefore graph` draws a corpus's chain of authorship:
every source, the scripts that read it, and every file they make.

- It runs every generator once, the way the gate does, with the observer
  recording what each wrote and - through its read log, one per generator, so
  whose read it was never rests on a script's name - what each read. Every
  tracked file is classified exactly as the gate classifies it: generated,
  captured by its group, or authored by its rule and the rule's reason. A
  corpus that configures the engine in its own scripts (`entry`) is read
  through those scripts.
- It changes nothing. Every tracked file is put back byte for byte, and what
  the run made that was not there before - a file a generator wrote, the
  bytecode its imports left, a directory it created - is removed again.
- A generated file is credited to its FIRST writer; a generator that saves it
  again is recorded as `also`, so a pack builder that re-saves the sheets it
  embeds no longer makes the script that drew them look as if it made nothing.
- A script's `.py` reads are its code, said apart from its sources; writes,
  its own outputs and untracked files are not reads. A `run` generator says
  `reads: null` - not observed - and never claims it reads nothing.
- `--json PATH` (or `-`, stdout) writes the model: a `schema` number, the
  engine version, the repository, the counts, every generator with its cwd,
  makes, reads, code, writes, rewrites and failure, then every file, every
  captured group and every authored rule.
- `--html PATH` (default `wherefore-graph.html`) writes one self-contained
  page, standard library only: no font, script or style from anywhere else,
  light and dark, a phone's width with nothing sideways, every control
  reachable by keyboard and 44 px to tap. Choose a source and it says what
  changes with it - "Change facts.json and 4 scripts rebuild 4 files" - or a
  file, and where it comes from. Below: the captured groups with their stamps
  and upstream addresses, and every authored rule with its reason and files.
- It prints one line - "15 files: 4 generated by 4 scripts, 10 written by
  hand, 1 captured; 6 reads traced; wrote wherefore-graph.html" - and exits 1
  if a generator failed, with the page written anyway and the failure on it.
- `generators.run_all(reads=...)` records each generator's reads, for any
  tool that wants them.

## 0.6.0 (2026-11-04)

**A generator can be any command.** Until now every generator was a Python
script, because what the gate knows a generator wrote came from an observer
that only Python loads. A team whose generators are Node, Go, a shell script
or a CAD export had to wrap each one in Python to be covered.

- A generator may say `run` instead of `script`: its command, as a list of
  words - `["node", "gen/site.mjs"]`, `["sh", "fonts.sh"]` - run as given, with
  no shell between, in its `cwd`, with the environment a generator always
  has. `script` and `run` are one or the other, and `wherefore.json` refuses
  both, neither, or a `run` that is not a list of words, in words. Everything
  else about a generator - `makes`, `stdout_to`, `probe`, `resettle`, the two
  passes, the gate - is as it was, and a Python script is still the default.
- What a `run` generator wrote is seen by picturing the tree just before it
  starts and just after it ends - every file's inode, size, mtime and ctime -
  and naming what changed. Generators run one at a time, so the difference is
  exactly theirs. It is ctime, which no process can set back, that makes it
  as strict as the observer: a write that restores its mtime is still seen,
  and a command that skips its write when nothing changed still leaves its
  file unclassified. Before each picture is used it waits, if it must, until
  the newest ctime in it is a filesystem tick in the past, so two writes in
  one tick cannot look like none.
- A command that cannot be started - a program that is not installed - fails
  like a generator that throws, in words.
- `proofs/run_proof.py` plants every fault the gate's own proof plants in a
  Python generator in a shell one: never invoked, the write skipped when
  unchanged, its output edited by hand, a file nobody tracks, a non-zero exit -
  and the write that hides its mtime, and one made by its child, which pass.
- The skill says when to use `run`, and the README's install section says a
  generator is a Python script by default, or any command.

## 0.5.1 (2026-11-03)

**What a pre-publication review found.** The first release meant for PyPI.
Nothing a corpus declares changes; what changes is how the engine behaves when
what it reads is not what it expected.

- `wherefore check upstream`:
  - a server that closes before the body it promised now "did not answer",
    instead of a traceback - and is never read as a shorter body;
  - `true`, `false` and `null` read from a source and recorded in the corpus are
    compared as the same JSON, so equal values no longer report MOVED;
  - a `json` pointer must be `""` or start with `/` (RFC 6901), and anything
    else is refused in words;
  - it reads at most 10 MB of an answer, and refuses one past that in words;
  - a MOVED line prints at most 80 characters of each value;
  - a recorded-values file that is not JSON is refused naming it.
- A section included from its own file (`"inventory": "checks/inventory.json"`)
  that is not JSON is refused naming the file, instead of a traceback.
- `wherefore scan` on a live address:
  - `--max-pages` caps every address fetched, not only the HTML pages, so a page
    linking to hundreds of downloads costs no more than the limit;
  - an answer that is not HTML is not read past its headers;
  - a redirect to another host is refused, and reported as not read.
- The package: `pip install wherefore-build` (or `uv tool install` / `pipx
  install`) in the README; the licence as an SPDX expression; the project's
  addresses and author; and an sdist that carries its tests' helpers, fixture
  and changelog, so its tests run.
- The README opens with what Wherefore is for - your company, compiled - and
  the hardware company it was built alongside, and the install section says
  what it needs: Python 3.10 or later, and nothing else.
- Contributions from outside are welcome: `CONTRIBUTING.md` says how (an issue
  first for anything bigger than a fix; Apache-2.0, section 5; each commit
  signed off under the Developer Certificate of Origin), and
  `CODE_OF_CONDUCT.md` adopts the Contributor Covenant 2.1. CI runs on every
  pull request, a fork's included, and on pushes to `main`; a new `sign-off`
  job checks each commit of a fork's pull request is signed off by its author.

## 0.5.0 (2026-11-03)

**Every surface, held to the source.** The skill's `start.md` gains a step for
after the first fact compiles: ask where else the product is described - the
site, the docs, the app's strings, a changelog, often each in its own
repository - which repository decides each fact, and which may read from
which. Then set every other surface up the same way: it pins the source, reads
what the source ships as data instead of typing its own list, and fails its
build on a feature it does not say, with a deliberate omission written down
like any exemption. `wherefore init` ends by pointing there.

**Derived from elsewhere: `wherefore check upstream`.** A captured group can
say where it was taken from when that is outside the repository - another
company's published file, counts taken from another product's public site - in
an `upstream`: the address, what to read there (a JSON pointer, a meta tag, or
a pattern, optionally base64-decoded), and what must still match - the group's
one file byte for byte, or a version the corpus records once, in a tracked
JSON file. `wherefore check upstream` reads each one now, and fails:

- **MOVED** when the source says something else: take the copy again, and
  record the new version in the same change - never the number alone;
- **no longer says** when the source answered without what `read` looks for:
  it changed shape, which is a change too;
- **did not answer**, unless the upstream gives the reason a source being down
  should not stop this corpus.

It is the one command that goes to the network, so it is never part of the
gate, the build or the pre-push hook: the gate stays offline, and the same
tree always gives the same answer. Run it where the corpus is compiled for a
deploy. The skill says what to do when it fails.

**One skill, one feature.** "The skill, for Claude Code" and "The skill, for
Codex" were two features in 0.4.0, for one skill written in two places. They
are one now - "The skill, for Claude Code and Codex", since 0.2.0 - so a page
that lists what the engine does says it once. A client with words for `codex`
is told the release no longer ships it, and drops them.

**Every release, said once as data: `releases.json`.** Each release's version,
date, title, one sentence, and a picture of it working - the command it is
best shown by and what it printed. It ships in the package, so the company's
changelog page is built from the release it pins: it lists every release, and
cannot list one that was never cut. `tests/test_releases.py` holds it to this
file's headings, every feature to a release that was cut, and the newest
release to the version `pyproject.toml` states, so a version cannot move
without its entry. The newest release's picture is run again on every change,
so it cannot drift from what the engine prints. The pictures of earlier
releases were made by running each tagged release.

## 0.4.0 (2026-11-03)

**The skill reaches Codex.** Codex reads a repository's skills from
`.agents/skills/<name>/SKILL.md` - the open Agent Skills format, the same one
Claude Code reads from `.claude/skills/` - so the skill generator now writes
the one skill the release ships to both places:

- `wherefore init` writes `.claude/skills/wherefore/` and
  `.agents/skills/wherefore/`, and says which agent reads which;
- the `wherefore.skill` generator writes both on every build, and the gate
  holds each copy to the release: an edit by hand to either is named;
- `start.md` says where both live.

**What the engine does, as data: `features.json`.** Each feature, the release
it arrived in, and its commands - whose words stay in `commands.json` - or its
own words if it has none. It ships in the package, so a client that describes
the product (the company's site) reads it from the release it pins and must
say something about every feature, or its build stops: a release that adds a
feature fails every page that does not yet tell people about it. Every command
belongs to exactly one feature, and a test fails a command that belongs to
none. The README's "What it does" is generated from it.

A corpus that already declares the generator writes the Codex copy at its next
build after moving its pin. That copy is generated, so a rule that claims
`*.md` as authored needs `.agents/skills/wherefore/*` excepted, as it already
excepts the Claude Code copy.

## 0.3.0 (2026-11-03)

**`wherefore scan`, the first win with no setup.** Point it at what a company
publishes - a built site, a docs folder, exported notes, or a live site's
address - and it reports every value stated more than one way:

    "start your {} day free trial"  - said 4 times, 2 ways
       14   3x   site/index.html:2, docs/start.md:3, site/pricing.html:1
       30   1x   help/billing.md:1

- It needs no `wherefore.json`: the scan comes before there is a corpus.
- A statement is a value with real words on both sides, keyed by the words
  around it; a version is keyed by the name in front of it.
- What it reports is a stale copy - the same statement in more than one file,
  saying at most three things, the commonest at least as often as the rest.
  It leaves alone identifiers (P-005, V83), dates, history ("since 2.1"),
  tables of different things, numbered lists, code, and files that are history
  by name unless `--all` asks for them. It would rather miss a disagreement
  than invent one.
- Pages are read the way a person reads them: sentences across inline tags,
  a picture's alt text, a page's description; script, style and code are not.
- A live address is read page by page on its own host, up to `--max-pages`
  (50). `--json` lists every statement and every place.
- Exit status 1 when copies disagree, so it can stand in CI before a corpus
  does.
- The skill's `start.md` begins the count with it.

Run on `chaotic-pendulums-co`'s docs, pack and brand - 152 files - its one
report was real: two brand documents give the swing's damping as viscous x60
and x8.

## 0.2.1 (2026-10-30)

What a fresh review found, fixed, and ready to be published. Every fault
below was reproduced on the fixture company first, and each now has a test
that plants it (`tests/test_false_passes.py`, `tests/test_hook.py`).

**The gate no longer passes when it should fail:**
- a generator that succeeds on the first pass and throws on the second is a
  failure, not "the corpus settles";
- a tracked file missing from the working tree is said, not compared with
  nothing - the pre-push hook passed a stale tree that way - and the gate
  leaves it missing, as it found it;
- `--restamp` takes exactly one group: re-stamping every group at once would
  certify captures nobody re-made;
- a captured group must say what it was made from (`shot_from`,
  `spec_values`) or why there is nothing (`no_stamp`, with the reason), and
  must name its `files`. A group with neither stamped the hash of nothing and
  passed for ever.

**`check retired` and `check claims` read what they missed:**
- a page whose name is not plain ASCII (`précis.html`) was never read: git
  quoted the name and it matched no file;
- a retired number is searched for written out in full - a million was
  searched for as `1e+06` - with a thousands comma and trailing zeros allowed,
  so 12.5 finds "$12.50" and 1000000 finds "1,000,000".

**The pre-push hook:**
- when git cannot say what a push changes - the first push of a new
  repository, or a remote tip this clone has not fetched - it rolls the corpus
  rather than assume nothing moved;
- nothing is skipped unless `hook.skip` says so. Prose was skipped by default,
  which excused a Markdown template a generator reads;
- it runs with the interpreter the engine is installed in, not whatever
  `python3` is on PATH, which blocked every push from a virtual environment.

**Commands:**
- it runs on Python 3.10 and 3.11, as it says: a backslash inside an
  f-string made `generators.py` a syntax error before 3.12, and CI now tests
  3.10 to 3.13;
- `wherefore init` and then `wherefore gate` does what init says - names every
  file nobody has accounted for - instead of refusing a corpus with no source
  yet;
- `wherefore prove` with a `proofs` glob that matches nothing fails: "0/0
  proofs held" passed;
- a flag a command does not take is refused, not ignored (`gate --kep` ran
  the whole gate), and `--help` prints the usage and runs nothing;
- a generator `cwd` that does not exist, a directory that is not a git
  repository, an inventory with no `captured` section, and a capture reading
  `spec_values` from an untracked source each say so, instead of a traceback;
- `wherefore list` says that what it wrote is left in the working tree.

Ready to be published, not published. The owner decided on 2026-10-30 that the
engine is open source.

- **Apache-2.0** (`LICENSE`), and the distribution is renamed
  **`wherefore-build`**: `wherefore` on PyPI is another project's. The import
  name and the command are still `wherefore`. A pin that names a commit after
  this one must say `wherefore-build @ git+...`.
- **`release.yml` can publish to PyPI** by trusted publishing, with no token
  stored - but only while the repository variable `PUBLISH_TO_PYPI` is `true`,
  which the owner sets when it is time.
- **`PUBLISHING.md`:** what the public repository leaves out (the pendulum's
  patch series and the design records about its internals), and the steps.
  **`CONTRIBUTING.md`** and **`SECURITY.md`**.

## 0.2.0 (2026-10-30)

The skill ships with the engine, and starts a corpus as well as working in one.

- **A second half of the skill, `start.md`:** the first session in a
  repository with no corpus yet, for a coding agent. It interviews the owner
  (what the company says in more than one place, where, and which systems
  already own a fact), counts every copy before changing anything, and takes
  one fact end to end - source, generator, reach, the hook and CI - before a
  second asset is touched. `SKILL.md` sends an agent there when there is
  nothing to work in yet.
- **The skill is in the package** (`src/wherefore/skills/wherefore/`), so each
  release carries the skill that matches its commands, and
  `corpus/commands_named.py` reads both files.
- **A corpus's copy is generated, not kept.** `wherefore init` now declares one
  generator, `python -m wherefore.skill`, which writes the release's skill into
  `.claude/skills/wherefore/` on every build. The gate holds that copy to the
  pinned release: move the pin and the skill moves with it, or the gate names
  the file that did not.
- **A generator's `script` may be `-m MODULE`,** run as `python -m` runs it, so
  a corpus can declare a module of an installed package without a copy of it.

## 0.1.1 (2026-10-28)

Wherefore on Wherefore: this repository becomes a client of its own engine.

- **The commands are said once,** in `src/wherefore/commands.json`:
  - `wherefore --help` prints them from there;
  - the README's list is generated from them (`corpus/readme.py`);
  - `tests/test_commands.py` holds the CLI's own dispatch to them.

  The three hand-typed lists had already drifted: the README's was missing
  both `hook` commands.
- **So are the principles,** in `src/wherefore/principles.json`. The README
  states them from there, and so can a client: both files ship in the
  package, so the company's site reads them from the release it pins.
  `tests/test_package_data.py` fails a data file the wheel would leave out.
- **This repository's own corpus is gated** (`wherefore.json`), by the
  previous release (`requirements-engine.txt`), never by the code being
  edited, the way a compiler builds itself. `corpus/commands_named.py` fails
  any user-facing document that tells a person to type a command the CLI does
  not have.
- **The version moves whenever the engine does** (`corpus/version_moves.py`,
  #32), and a release is tagged and published from `CHANGELOG.md` by
  `.github/workflows/release.yml`, never by hand.

## 0.1.0 (2026-10-28)

The first release: the machinery extracted from chaotic-pendulums-co, moved
rather than rewritten, with the pendulum as its first client.

- **Moved, byte for byte but for recorded edits** (`tools/moved/`): the
  generator runner and the roll, the write observer, the coverage gate, the
  comparators (pictures, numbers, workbook cells, inlined pictures), the proof
  harness, the retired-facts sweep and the source-reach probe.
- **New:**
  - `wherefore.json`, with includes and a required `why` for every
    exemption;
  - `entry`, for a client that configures the engine in Python;
  - the CLI: `init`, `list`, `build`, `gate`, `prove`, `check retired`,
    `check reach`, `check claims` and `hook install`;
  - two source adapters (`params`, `leaves`);
  - the claim rule.
- **Proved** against a fictional client, `tests/fixture/`. Each proof breaks it
  one way and requires the right failure, in the right words.
