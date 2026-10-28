import pathlib
import re
import unittest

SRC = pathlib.Path(__file__).resolve().parents[1] / "src/wherefore"
PYPROJECT = SRC.parents[1] / "pyproject.toml"


class EveryDataFileIsShipped(unittest.TestCase):
    """A wheel carries a package's modules and only the data pyproject.toml
    names. A file left off that list is found in this checkout and in every
    editable install - which is how this repository's own tests run - and is
    missing from every client's, which reads the commands and the principles
    from the release it pins. So the list must name every file in the package
    that is not a module of it."""

    def shipped(self):
        block = re.search(r"^\[tool\.setuptools\.package-data\]\n(.*?)(?=^\[|\Z)",
                          PYPROJECT.read_text(encoding="utf-8"), re.S | re.M).group(1)
        return set(re.findall(r'"([^"]+)"', re.search(r"^wherefore = \[(.*?)\]", block, re.S | re.M).group(1)))

    def data(self):
        for path in SRC.rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            if path.suffix == ".py" and (path.parent / "__init__.py").exists():
                continue                         # a module of the package
            yield path.relative_to(SRC).as_posix()

    def test_the_package_data_names_every_file_that_is_not_a_module(self):
        self.assertEqual(set(self.data()), self.shipped())


if __name__ == "__main__":
    unittest.main()
