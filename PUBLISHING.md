# Publishing Wherefore

How this private repository becomes a public one, and the engine a package
anyone can install. Decided by the owner on 2026-10-30: the engine is open
source, under Apache-2.0, published as `wherefore-build`. The owner publishes
it when it is ready; nothing in this file happens on its own.

## What is ready

- **`LICENSE`:** Apache-2.0, exactly as the Apache Software Foundation
  publishes it.
- **`pyproject.toml`:** the distribution is `wherefore-build`, with the licence
  and classifiers. What is imported and what is typed are still `wherefore`.
- **`.github/workflows/release.yml`:** a `pypi` job that uploads a newly tagged
  release by PyPI's trusted publishing, so no PyPI token is stored anywhere. It
  runs only while the repository variable `PUBLISH_TO_PYPI` is `true`: until
  the owner sets it, nothing is published.
- **`CONTRIBUTING.md` and `SECURITY.md`.**

## What the public repository leaves out

Nothing in this repository is a secret: no token, password or key is in any
file. (A search for "password" finds the word, in prose about the pendulum's
password-gated packs, and nothing else.) But some of it is the first client's
private detail, and that is the owner's to publish or not.

| path | what it holds | recommendation |
|---|---|---|
| `integration/chaotic-pendulums-co/` | the pendulum's own code, as a patch series | leave out |
| `ENGINE_INVENTORY.md` | the pendulum's checks, tools and infrastructure, file by file | leave out |
| `ARCHITECTURE_REVIEW.md` | the same, with its runners, packs and part numbers | leave out |
| `VERSIONING_SHAPE.md` | the pendulum's versioning and release questions | leave out |
| `DIRECTIONS.md` | the roadmap: obligations, onboarding, going public | keep, after reading it once more for anything private |
| `src/`, `proofs/`, `tools/moved/` | the engine. Some docstrings tell the pendulum's history - a fork that went from 210 to 216, a part number - as the reason a check exists | keep, if the owner is content for those details of the pendulum to be public: it is why the engine is shaped as it is |

`README.md` names the paths left out and points at the pendulum's repository,
so its template (`docs/README.template.md`) loses those rows and sentences, and
the README is regenerated, in the same change.

## The steps

1. **The names** (wherefore-co `DECISIONS.md`, section 2): register
   `wherefore.build` and `getwherefore.com`; create the GitHub organisation
   `wherefore-build`.
2. **The public repository:** create `wherefore-build/wherefore`, empty. Fill it
   from a copy of this tree without the paths above, as one first commit - a
   fresh history, so nothing left out survives in an old commit. This private
   repository stays as it is, with its history.
3. **PyPI:** on pypi.org, add a *pending* trusted publisher for the project
   `wherefore-build` - owner `wherefore-build`, repository `wherefore`, workflow
   `release.yml`, environment `pypi`. Create the `pypi` environment in the
   public repository's settings.
4. **The switch:** set the repository variable `PUBLISH_TO_PYPI` to `true`. The
   next version that `release.yml` tags is uploaded; versions tagged before
   are not.
5. **The clients:** each moves its pin to the PyPI release
   (`wherefore-build==X.Y.Z` in `requirements-engine.txt`) and deletes the
   `WHEREFORE_READ_TOKEN` secret, which nothing needs once the engine is public.
   A pin that names a commit of this repository after the rename must say
   `wherefore-build @ git+...`, not `wherefore @ ...`: pip refuses a name that
   does not match the package.
6. **The site:** `company.domain` and `start.install` in wherefore-co's facts,
   so the page's install line is the real one.

## One thing to know

The package `wherefore` on PyPI is another project's (`tracelore/wherefore`),
and it may import as `wherefore` too. Installing both into one environment
would put two packages in one import name. Unlikely, since the two do different
things, but worth knowing if a user reports something strange.
