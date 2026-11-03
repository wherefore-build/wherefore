# Publishing Wherefore

Wherefore is open source, under Apache-2.0 (`LICENSE`). It is on PyPI as
`wherefore-build`; what is imported and what is typed are still `wherefore`.

## How a release is published

1. **The version moves together:** in `pyproject.toml`, in
   `wherefore.__version__`, in `CHANGELOG.md` and in
   `src/wherefore/releases.json`, in one pull request.
2. **On merge,** `.github/workflows/release.yml` tags the new version and makes
   its GitHub release.
3. **It uploads to PyPI** by trusted publishing, so no PyPI token is stored
   anywhere - and only while the repository variable `PUBLISH_TO_PYPI` is
   `true`.

## Setting up PyPI, once

1. On pypi.org, add a *pending* trusted publisher: project `wherefore-build`,
   owner `wherefore-build`, repository `wherefore`, workflow `release.yml`,
   environment `pypi`.
2. Create the `pypi` environment in this repository's settings.
3. Set the repository variable `PUBLISH_TO_PYPI` to `true`. The next version
   `release.yml` tags is uploaded; versions tagged before are not.

Clients then pin a release: `wherefore-build==X.Y.Z` in
`requirements-engine.txt`.

## What this repository's history leaves out

Wherefore began as a private repository. Its history here is that history,
commit for commit, less its first client's private detail and the product's
roadmap. Commits that touched only those are gone; every other commit and
message is as it was.

## One thing to know

The package `wherefore` on PyPI is another project's (`tracelore/wherefore`),
and it may import as `wherefore` too. Installing both into one environment
would put two packages in one import name. Unlikely, since the two do different
things, but worth knowing if a user reports something strange.
