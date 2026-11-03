# Changelog

Every release of the engine, newest first. A client pins one commit (its
`requirements-engine.txt`), and moving that pin is a pull request its own full
suite judges, so a release reaches no client by itself.

The version is stated in `pyproject.toml`, in `wherefore.__version__` and here,
and `tests/test_version.py` holds the three together until they are one fact
(DIRECTIONS.md §12, §13).

## 0.5.0 (2026-11-03)

**Every surface, held to the source.** The skill's `start.md` gains a step for
after the first fact compiles: ask where else the product is described - the
site, the docs, the app's strings, a changelog, often each in its own
repository - which repository decides each fact, and which may read from
which. Then set every other surface up the same way: it pins the source, reads
what the source ships as data instead of typing its own list, and fails its
build on a feature it does not say, with a deliberate omission written down
like any exemption. `wherefore init` ends by pointing there.

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
