"""THE CORPUS DOES NOT LEAVE THIS MACHINE STALE: the pre-push guard.

Generalised from chaotic-pendulums-co's .githooks/pre-push. Every document is
generated and COMMITTED, and a deploy that assembles what is committed would
show the old facts if a source change were pushed without the documents it
moves - and say nothing about it, which is the part that matters. The gate
catches it in CI, minutes later; this catches it here, before the push.

IT STOPS, IT DOES NOT COMMIT. A hook that writes commits behind you is the
thing that later makes you distrust your own history. Being told is one
command from fixed.

WHAT CANNOT MOVE A GENERATED FILE, and nothing else is assumed: paths matching
wherefore.json `hook.skip` skip the roll, and nothing is skipped unless the
corpus says so. Everything else runs it - a needless roll costs a push its
seconds, a missed one costs a review of the wrong facts. (Prose used to be
skipped by default, which excused a Markdown template a generator reads: the
one change that makes its output stale.)

WHEN GIT CANNOT SAY WHAT CHANGED - the first push of a new repository, or a
remote tip this clone has not fetched - the roll runs. Not knowing is not
"nothing changed".

    wherefore hook install     write .git/hooks/pre-push (or into core.hooksPath)
    wherefore hook pre-push    what the hook runs; git feeds it the refs on stdin
"""
import os
import pathlib
import re
import stat
import subprocess
import sys

ZERO = "0" * 40
MARK = "# Installed by `wherefore hook install`."


def script():
    """The hook, run by the interpreter the engine is installed in.

    Not a bare `python3`: in a virtual environment that is some other Python,
    with no wherefore in it, and the hook blocked every push with "No module
    named wherefore".
    """
    import shlex
    return (f"#!/bin/sh\n{MARK} Skip once, and know why: git push --no-verify\n"
            f'exec {shlex.quote(sys.executable)} -m wherefore hook pre-push "$@"\n')


def _git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)


def changed_paths(root, refs, base_ref):
    """Every path the pushed commits change, from git's `local remote` lines;
    None when git cannot say, which the caller must treat as anything."""
    changed = set()
    for line in refs:
        parts = line.split()
        if len(parts) != 4:
            continue
        _local_ref, local_sha, _remote_ref, remote_sha = parts
        if local_sha == ZERO:
            continue                                  # a branch being deleted
        if remote_sha == ZERO:
            # A NEW BRANCH has no remote side; its merge base with the default
            # branch is what this branch actually adds.
            # With no merge base - no base_ref here yet - the last commit alone
            # would hide every commit before it in the push: that is unknown too.
            base = _git(root, "merge-base", local_sha, base_ref).stdout.strip()
            if not base:
                return None
            rng = f"{base}..{local_sha}"
        else:
            rng = f"{remote_sha}..{local_sha}"
        r = _git(root, "diff", "--name-only", rng)
        if r.returncode:
            return None
        changed |= set(r.stdout.split("\n")) - {""}
    return sorted(changed)


def pre_push(cfg, refs):
    hook = cfg.doc.get("hook", {})
    skip = [re.compile(p) for p in hook.get("skip", [])]
    changed = changed_paths(cfg.root, refs, hook.get("base_ref", "origin/main"))
    if changed is None:
        print("pre-push: git cannot say what this push changes (a first push, or a remote "
              "tip this clone has\nnot fetched) - rolling the corpus rather than assume "
              "nothing moved.")
    elif not changed or all(any(p.search(c) for p in skip) for c in changed):
        return 0
    else:
        print("pre-push: something here can move a generated document - rolling the corpus.")
    r = subprocess.run([sys.executable, "-m", "wherefore", "build"], cwd=cfg.root)
    if r.returncode:
        print("\npre-push: STOPPED. The documents above are not what the sources say any "
              "more.\n\nThey have just been regenerated in your working tree, so the fix is "
              "to look at\nthem and commit them with the change that caused them. A "
              "document and the fact\nit prints belong in one commit.", file=sys.stderr)
        return 1
    return 0


def install(cfg):
    hooks = _git(cfg.root, "config", "core.hooksPath").stdout.strip()
    d = (cfg.root / hooks) if hooks else pathlib.Path(
        _git(cfg.root, "rev-parse", "--git-path", "hooks").stdout.strip())
    if not d.is_absolute():
        d = cfg.root / d
    d.mkdir(parents=True, exist_ok=True)
    path = d / "pre-push"
    if path.exists() and MARK not in path.read_text(encoding="utf-8", errors="replace"):
        print(f"::error::{path} exists and is not this hook. Merge them by hand rather than "
              f"have one guard silently replace another.")
        return 1
    path.write_text(script(), encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"wrote {path}: a push that can move a generated document rolls the corpus "
          f"first, and stops if it moved")
    return 0


# What `wherefore hook` takes: install writes the hook, and the hook runs pre-push.
SUBCOMMANDS = ("install", "pre-push")


def main(cfg, argv):
    if argv[:1] == ["install"]:
        return install(cfg)
    if argv[:1] == ["pre-push"]:
        return pre_push(cfg, sys.stdin.read().splitlines())
    print(f"::error::wherefore hook {' | '.join(SUBCOMMANDS)}")
    return 1
