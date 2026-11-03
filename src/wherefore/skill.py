"""python -m wherefore.skill - the skill, written where a corpus's agents read it.

A coding agent working in a corpus reads the skill: how to work in a corpus
that compiles (SKILL.md), and how to start one (start.md). Claude Code reads it
from .claude/skills/wherefore/ and Codex from .agents/skills/wherefore/. Both
take the same files - the open Agent Skills format, a folder per skill with a
`name` and a `description` at the top of its SKILL.md - so the one skill the
release ships is written to each place, and neither copy can drift from it. The
skill is the release's. It ships in the package beside the commands it names,
and corpus/commands_named.py fails it if it names one the CLI does not have.

So a corpus does not keep its own copy of the skill. It declares this as a
generator - `wherefore init` does - and the generator writes the skill from the
installed engine, every run, unconditionally. The gate then holds the copy to
the release the corpus pins: move the pin, and the skill the agents read moves
with it, or the gate names the file that did not.

`wherefore init` also writes it once, there and then: the skill is how an agent
starts a corpus, and a build refuses a corpus that declares no source yet.

Run from the corpus's root, as the generator's `cwd` says.
"""
import pathlib
from importlib.resources import files

# Where each coding agent reads a repository's skills.
INTO = {
    "Claude Code": pathlib.Path(".claude/skills/wherefore"),
    "Codex": pathlib.Path(".agents/skills/wherefore"),
}


def shipped():
    """{name: text} for every file of the skill this release ships."""
    skill = files("wherefore") / "skills" / "wherefore"
    return {f.name: f.read_text(encoding="utf-8")
            for f in sorted(skill.iterdir(), key=lambda f: f.name) if f.name.endswith(".md")}


def write(root="."):
    """Write the release's skill under `root`, once for every agent; return the paths written."""
    out = []
    for place in INTO.values():
        into = pathlib.Path(root) / place
        into.mkdir(parents=True, exist_ok=True)
        for name, text in shipped().items():
            (into / name).write_text(text, encoding="utf-8")
            out.append(into / name)
    return out


def main():
    write()


if __name__ == "__main__":
    main()
