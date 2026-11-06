"""The docs, shipped with each release: src/wherefore/docs/*.md, held to the code they describe.

Every command has its section and every section is a command; every section
of wherefore.json the engine reads has its section; every example is run
again on the example company and must print what the page says, in order.
"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

from _util import ENGINE, SRC
from wherefore import cli, docs

ELIDED = "…"


def command_name(usage):
    """`wherefore check retired` from `wherefore check retired`; `wherefore gate` from `wherefore gate [--keep]`."""
    words = []
    for w in usage.split()[1:]:
        if w[:1] in "[-" or w.isupper() or "|" in w:
            break
        words.append(w)
    return "wherefore " + " ".join(words)


class EveryPageIsWhole(unittest.TestCase):
    def test_every_page_has_a_title_and_words_in_reading_order(self):
        ids = [p[0] for p in docs.pages()]
        self.assertEqual(ids, [p[0] for p in docs.PAGES])
        for pid, title, text in docs.pages():
            self.assertTrue(title.strip(), pid)
            self.assertTrue(text.lstrip().startswith("# "), f"{pid} opens with its heading")
            self.assertGreater(len(text), 400, f"{pid} is a page, not a stub")

    def test_the_commands_page_has_a_section_per_command_and_no_section_that_is_not_one(self):
        text = dict((p[0], p[2]) for p in docs.pages())["commands"]
        commands = {command_name(c["usage"]) for c in cli.commands()}
        heads = set(docs.sections(text))
        # `wherefore hook install` and `wherefore hook pre-push` share one section, `wherefore hook`;
        # `wherefore gate --restamp GROUP` is `wherefore gate`'s.
        want = {h if h in heads else " ".join(h.split()[:2]) for h in commands}
        self.assertEqual(heads, want, "a command without its section, or a section that is not a command")

    def test_the_configuration_page_has_a_section_per_section_the_engine_reads(self):
        text = dict((p[0], p[2]) for p in docs.pages())["configuration"]
        heads = set(docs.sections(text))
        self.assertEqual(heads, set(docs.CONFIG_SECTIONS),
                         "a section of wherefore.json the engine reads has no page, or a page names a section the engine does not read")


class EveryExampleIsTrue(unittest.TestCase):
    """Each fenced block that begins `$ wherefore ...` is run on a fresh copy of
    the example company, and must print what the page shows, in order."""

    def run_example(self, command):
        base = pathlib.Path(tempfile.mkdtemp(prefix="wherefore-docs-"))
        try:
            root = base / "fernhollow"
            shutil.copytree(ENGINE / "tests/fixture", root)
            for args in (["init", "-q"], ["add", "-A"],
                         ["-c", "user.email=t@wherefore", "-c", "user.name=t", "commit", "-qm", "x"]):
                subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
            env = dict(os.environ, PYTHONPATH=str(SRC))
            env.pop("WHEREFORE_ROOT", None)                        # the report's example uses --show: nothing is sent
            r = subprocess.run([sys.executable, "-m", "wherefore", *command.split()[1:]], cwd=root, env=env,
                               capture_output=True, text=True)
            return [l.rstrip() for l in (r.stdout + r.stderr).replace(str(root), "~/fernhollow").splitlines()]
        finally:
            shutil.rmtree(base, ignore_errors=True)

    def test_every_example_prints_what_the_page_says(self):
        seen = 0
        for pid, _, text in docs.pages():
            for command, lines in docs.examples(text):
                seen += 1
                printed = self.run_example(command)
                at = 0
                for line in lines:
                    if line == ELIDED:
                        continue
                    try:
                        at = printed.index(line.rstrip(), at) + 1
                    except ValueError:
                        self.fail(f"{pid}: `{command}` no longer prints, in this order:\n  {line}\nIt printed:\n"
                                  + "\n".join(printed))
        self.assertGreaterEqual(seen, 8, "the commands page shows the engine working")


if __name__ == "__main__":
    unittest.main()
