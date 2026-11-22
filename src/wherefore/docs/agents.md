# With a knowledge factory

A knowledge factory keeps your agents' knowledge current. A curator agent
reads what working agents flag, their traces and your raw notes, and updates
the skills and facts they work from. Wherefore keeps what you publish matching
its source, and refuses a change that would let a copy drift. The two meet at
the facts: the curator proposes, Wherefore judges, and a person merges.

## The curator proposes a fact, never a page

The curator edits a source - a file `sources` in wherefore.json names - on a
branch, and opens a pull request. It never edits a page, a doc or a slide:
those are built from the source, and `wherefore gate` refuses a generated file
that differs from what its generator writes. One edit to a fact moves every
copy that states it.

The pull request is the ticket nobody filed. It says what changed and why, the
person who reviews it sees every page that moved, and nothing ships until they
merge it.

## Wherefore judges the change

The checks the corpus already runs in CI judge the curator's branch the way
they judge anyone's:

- `wherefore gate`: every generated file is what its generator writes from the
  new fact, and every file is accounted for.
- `wherefore check reach`: the fact reaches every page that should state it.
- `wherefore check retired`: no page a person reads still claims a value the
  change retired.
- `wherefore check claims`: a claim says only what its rule allows, so a
  curator cannot promote "SOC 2 in progress" to "SOC 2 certified" by editing
  a sentence.

A curator that cannot get its branch through these has not found a fact; it
has found a question for a person.

## Wherefore gives the curator its flags

A curator works from flags. Wherefore raises the ones about what you publish:

- `wherefore scan` reads your site, app or docs and names every value stated
  more than one way - the site says fourteen days, the app says thirty. Each
  is a flag: one copy is wrong, and the fix is one fact.
- `wherefore check drift` names values written by hand in two or more files
  that no source holds yet, with their files and a count: candidates for a
  new fact.
- `wherefore status --json` is where the repository stands, in one read, for
  a curator that runs on a cadence.

## Your agents read the same facts

The sources are plain files in your repository. An agent may read them as its
domain knowledge, so the answer an agent gives and the page a customer reads
come from the same line. A curator that keeps its own copy of a fact Wherefore
holds is keeping a second source, and the two will drift: point it at the
source instead.

## What the curator must not do

- Edit a generated file. The gate refuses it, and the next build would write
  over it.
- Merge its own pull request. The review is the point.
- Silence a check to get a branch through. A check that fails is the answer.
