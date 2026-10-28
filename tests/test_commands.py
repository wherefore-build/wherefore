import unittest

from _util import repo, wherefore
from wherefore import cli, hook


class TheCommandsAreSaidOnce(unittest.TestCase):
    """commands.json is the one place the commands are said. What the CLI
    actually dispatches must be exactly what it lists - a command added to the
    code and not to the list is undocumented, and one in the list and not the
    code is a promise the CLI breaks."""

    def words(self, at):
        return [c["usage"].split()[at] if len(c["usage"].split()) > at else None
                for c in cli.commands()]

    def test_every_command_is_listed_and_every_listed_one_exists(self):
        self.assertEqual(set(self.words(1)), set(cli.COMMANDS))

    def test_check_and_hook_take_exactly_what_the_list_says(self):
        rows = [c["usage"].split() for c in cli.commands()]
        self.assertEqual({r[2] for r in rows if r[1] == "check"}, set(cli.CHECKS))
        self.assertEqual({r[2] for r in rows if r[1] == "hook"}, set(hook.SUBCOMMANDS))

    def test_help_prints_the_list(self):
        code, out = wherefore(repo({"x": "x"}), "--help")
        self.assertEqual(code, 0)
        for c in cli.commands():
            self.assertIn(c["usage"], out)
            self.assertIn(c["does"], out)


if __name__ == "__main__":
    unittest.main()
