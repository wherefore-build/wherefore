# Changelog

Every release of the engine, newest first. A client pins one commit (its
`requirements-engine.txt`), and moving that pin is a pull request its own full
suite judges, so a release reaches no client by itself.

The version is stated in `pyproject.toml`, in `wherefore.__version__` and here,
and `tests/test_version.py` holds the three together until they are one fact
(DIRECTIONS.md §12, §13).

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
