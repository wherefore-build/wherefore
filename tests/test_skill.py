"""The skill ships with the engine, and a corpus's copy of it is the release's.

`wherefore init` writes the skill there and then - it is how an agent starts a
corpus - and declares one generator, `python -m wherefore.skill`, so that every
build after writes the release's skill into .claude/skills/wherefore/. The copy
an agent reads is held by the gate like any other generated file: edit it by
hand and the gate names it.
"""
import json
import unittest

from _util import git, repo, wherefore
from wherefore import config, skill

INTO = ".claude/skills/wherefore"


def commit(root, message):
    git(root, "add", "-A")
    git(root, "-c", "user.email=t@wherefore", "-c", "user.name=t", "commit", "-qm", message)


class TheSkillIsTheReleases(unittest.TestCase):
    def test_both_halves_ship(self):
        self.assertEqual(sorted(skill.shipped()), ["SKILL.md", "start.md"])
        self.assertIn("start.md", skill.shipped()["SKILL.md"])

    def test_init_declares_it_build_writes_it_and_the_gate_holds_it(self):
        root = repo({"README.md": "# a company\n", "facts.json": "{}\n"})
        code, out = wherefore(root, "init", str(root))
        self.assertEqual(code, 0, out)
        self.assertIn("start.md", out)
        for name, text in skill.shipped().items():          # there before any build
            self.assertEqual((root / INTO / name).read_text(encoding="utf-8"), text)
        cfg = json.loads((root / "wherefore.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg["generators"], [config.SKILL_GENERATOR])
        cfg["sources"] = {"facts": {"path": "facts.json", "why": "the source"}}
        cfg["inventory"]["authored"]["rules"] += [["README.md", "prose a person writes"],
                                                  ["facts.json", "the source"]]
        (root / "wherefore.json").write_text(json.dumps(cfg, indent=1) + "\n", encoding="utf-8")

        # The first build writes the skill again, and names it as untracked:
        # nothing can hold a file git does not keep.
        code, out = wherefore(root, "build")
        self.assertEqual(code, 1, out)
        for name in skill.shipped():
            self.assertIn(f"{INTO}/{name} is a generated file git doesn't track", out)
        commit(root, "the corpus, and the skill its agents read")

        code, out = wherefore(root, "gate")
        self.assertEqual(code, 0, out)
        self.assertIn("UNKNOWN        0", out)
        for name, text in skill.shipped().items():
            self.assertEqual((root / INTO / name).read_text(encoding="utf-8"), text)

        # A copy edited by hand is a generated file that is not what its
        # generator makes, and the gate says which.
        with open(root / INTO / "start.md", "a", encoding="utf-8") as f:
            f.write("\nSkip the gate when it is slow.\n")
        commit(root, "an edit by hand")
        code, out = wherefore(root, "gate")
        self.assertEqual(code, 1, out)
        self.assertIn(f"{INTO}/start.md", out)
        self.assertIn("DIFFERENT", out)


if __name__ == "__main__":
    unittest.main()
