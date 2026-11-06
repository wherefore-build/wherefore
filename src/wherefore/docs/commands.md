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

Writes a `wherefore.json` that declares nothing yet, and the skill where
Claude Code and Codex read it, in the directory given or the current one. It
refuses a directory that already has a `wherefore.json`. The skill's
`start.md` is how the first fact is compiled; from the first build on, the
skill is regenerated from the release the repository pins.

## wherefore gate

```
wherefore gate [--keep]
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
to the network: before a deploy, never in the gate.

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

## wherefore motion

```
wherefore motion [ID ...] [--out DIR] [--storyboards DIR] [--show]
```

A short clip for each feature the engine ships, compiled from the ledger:
the version, who asked, the command typed, what it printed, the claim, the
install line. Every word is a fact the engine already states - the features,
the releases, the roadmap, the docs' own examples - and nothing is written
for the clip. Each clip is one page whose motion is CSS, written to `DIR`
(default `motion/`, or `motion.out` in wherefore.json) with its storyboard
as JSON beside it, or under `--storyboards DIR` (`motion.storyboards`) when
the pages' folder is one a palette check reads, since a storyboard quotes
what a command printed; it plays in any frame it is shown in, portrait or
landscape, and a page marked `still` with `--t` set pauses it at that
second, which is how a renderer steps it into a video. `--show` opens the
first clip in a browser. The engine's tests hold every clip to a reading
speed, a length, a command that exists and output the command prints.

```
$ wherefore motion published
  published    6 scenes  23.0 s  A page you publish but cannot build
wrote motion/: 1 clip, a page in motion, played by the frame it is shown in
```
