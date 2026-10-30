# Changelog

Every release of the engine, newest first. A client pins one commit (its
`requirements-engine.txt`), and moving that pin is a pull request its own full
suite judges, so a release reaches no client by itself.

The version is stated in `pyproject.toml`, in `wherefore.__version__` and here,
and `tests/test_version.py` holds the three together until they are one fact
(DIRECTIONS.md §12, §13).

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
