# Wherefore at organization scale

A design record. Owner, 22 November 2026: "Let's do it independently of
Hamster and not assume we will work with them." The order of the stages is
the owner's.

## Why

A Wherefore repository today is facts in files, generators that build every
page, doc, deck and clip from them, and a gate that refuses any change that
leaves a copy disagreeing. A person reviews and merges each change. That is
right for one team. It tears when a whole organization and its agents change
facts at once:

- many writers contend for the same source files;
- the gate rebuilds everything on every change, so its cost grows with the
  whole corpus, per change, however small the change;
- a person merging every change becomes the queue;
- the record of who decided a fact is a quote in a commit message, which
  anyone can type.

The outcome is right; the data model and the review model are built for one
team. This record says what stays, what changes, and in what order.

## What does not change

These are the product. Every stage keeps all five.

1. **One source per fact.** A fact is said once; every copy is built from it.
2. **Every file accounted for.** Generated, authored with a reason, or
   captured and stamped. Generated is derived by running the generators,
   never declared by hand.
3. **Nothing ships that disagrees.** A change that leaves any copy out of step
   with its source is refused.
4. **Every check is shown to fail.** A check is not trusted until a proof has
   watched it catch the fault it is for.
5. **No model at build time.** The build is plain code. Agents may write the
   generators and propose facts; they never sit inside the build.

## Stage 1: check only what a change touches

**What.** The gate, given `--since REF`, runs only the generators a change can
reach, and compares only what they write. Everything else is classified from
the last full run, not re-derived.

**How.** A full gate already runs every generator and can record what each one
reads (generators.run_all, `reads=`). The full gate writes that record, the
read map, as a generated file of the corpus, so the gate holds its own map
current like any other output. With `--since REF`, a generator runs when any
of these hold, and is skipped otherwise:

- its script, or any file it read in the map, changed since REF;
- it is not observed (a command, not a Python script: its reads are unknown);
- it is new, or the map does not name it;
- it wrote a file that changed since REF, or that is missing;
- the engine's own version differs from the one that wrote the map.

A file the map says a skipped generator writes is classified generated, by
that generator, at the bytes committed. That is the one place the gate trusts
a record instead of a run, so the record is the gate's own output and never
a hand-kept list, and it is guarded twice:

- **The backstop.** The full gate still runs on main and once a day. A file the
  incremental gate trusted and the full gate finds stale fails the full run,
  and names the generator whose reads the map missed.
- **The proof.** A proof plants a generator that reads a file the map does not
  record, changes that file, and requires the full gate to catch what the
  incremental one could not, so the limit is shown, not assumed.

**Done when.** On every change in the last month of the company's site and the
pendulum, `--since` reaches the same verdict as a full run, and both corpora's
pull requests run it.

## Stage 2: every fact change carries a decision

**What.** A repository declares which facts are sensitive - pricing, plan
limits, compliance claims - and who may decide them. A new check,
`decisions`, refuses a change to a fact unless it carries an approval from
someone allowed to give it.

**How.** In wherefore.json, `decisions` names fact paths (a source and a key
glob) and who decides each: anyone with review rights, or named people. The
check reads the change's facts against its base, and the approvals from where
they are verified - on GitHub, a pull request's approving reviews, whose
author is GitHub's account, not a typed name. A decision is recorded with the
release it shipped in, so `wherefore status` can say who decided each fact.

**Done when.** The company's site and the pendulum declare their sensitive
facts, and a change to one without the right approval fails; a proof shows a
typed "approved by" in a commit message does not count.

## Stage 3: facts as a typed model, behind a pluggable source

**What.** Each fact has an identity, a type, a schema checked when it is
written, and provenance: who decided it and every place it is stated. The
engine reads facts through one interface. Files stay the default; a graph
store can stand behind the same interface.

**How.** The interface is small and read-only to the engine: facts at a
version, the changes between two versions, and each fact's provenance. The
files source is today's sources, unchanged. A graph source speaks an open
protocol any store can implement, and one reference backend proves it.
Everything above the interface - the gate, reach, drift, claims, the scan -
does not change.

**Done when.** The same corpus, built once from files and once from the
reference graph backend, produces byte-identical output, and the checks pass
on both.

## Not now

- Replacing git for generators, checks and pages. Only facts move.
- Merging routine fact changes without a person. It comes after Stage 2 has
  run on real changes.
- Reading the chatter between agents. A curator distils it into proposed fact
  changes; Wherefore only ever sees those.

## How each stage ships

A draft pull request on the engine with its tests and proofs, piloted on the
company's site and the pendulum before anywhere else. Merging a stage cuts a
release, so each waits for the owner. After any stage, what has shipped is
worth having on its own.
