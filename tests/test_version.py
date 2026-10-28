import pathlib
import re
import unittest

from _util import ENGINE
import wherefore


class OneVersion(unittest.TestCase):
    """The version is written in three places; they must say the same thing."""

    def test_pyproject_package_and_changelog_agree(self):
        pyproject = re.search(r'^version = "([^"]+)"$',
                              (ENGINE / "pyproject.toml").read_text(), re.M).group(1)
        changelog = re.search(r"^## (\S+) \(", (ENGINE / "CHANGELOG.md").read_text(),
                              re.M).group(1)
        self.assertEqual(wherefore.__version__, pyproject)
        self.assertEqual(changelog, pyproject,
                         "the newest CHANGELOG.md entry is not the version pyproject.toml states")


if __name__ == "__main__":
    unittest.main()
