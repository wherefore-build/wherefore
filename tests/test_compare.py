import pathlib
import tempfile
import unittest

from _util import SRC  # noqa: F401
from wherefore import compare as C


def files(a, b, suffix=".txt"):
    d = pathlib.Path(tempfile.mkdtemp())
    (d / f"a{suffix}").write_text(a)
    (d / f"b{suffix}").write_text(b)
    return d / f"a{suffix}", d / f"b{suffix}"


class Numbers(unittest.TestCase):
    def test_an_ulp_is_not_a_change_and_a_face_is(self):
        self.assertTrue(C.same_numbers(*files("P(1.00000,2)\n", "P(1.00001,2)\n"), 1e-4))
        self.assertFalse(C.same_numbers(*files("P(1.0,2)\n", "P(1.1,2)\n"), 1e-4))
        self.assertFalse(C.same_numbers(*files("P(1,2)\n", "Q(1,2)\n"), 1e-4))
        self.assertFalse(C.same_numbers(*files("P(1,2)\n", "P(1,2)\nP(3,4)\n"), 1e-4))


class Registry(unittest.TestCase):
    def test_first_match_wins_and_bytes_is_the_default(self):
        c = C.Comparators([
            {"glob": "solids/*.step", "as": "numbers", "tol": 1e-4, "why": "libm"},
            {"glob": "*.step", "as": "bytes", "why": "never reached for solids/"}])
        self.assertEqual(c.rule_for("solids/a.step"), ("numbers", {"tol": 1e-4}))
        self.assertEqual(c.rule_for("a/b/c.svg"), ("bytes", {}))
        self.assertTrue(c.same(*files("x 1.00000\n", "x 1.00001\n", ".step"), "solids/a.step"))

    def test_a_threshold_is_never_assumed(self):
        with self.assertRaises(SystemExit) as e:
            C.Comparators([{"glob": "*.png", "as": "picture", "edge_tol": 0.03, "why": "w"}])
        self.assertIn("needs tone_tol", str(e.exception.code))

    def test_a_raster_is_a_raster_and_an_svg_beside_it_is_not(self):
        c = C.Comparators([{"glob": "web/*", "as": "picture", "edge_tol": 0.035,
                            "tone_tol": 32, "why": "w"}])
        self.assertTrue(c.is_raster("web/icon.png"))
        self.assertFalse(c.is_raster("web/icon.svg"))
        self.assertFalse(c.same(*files("<svg/>", "<svg />", ".svg"), "web/icon.svg"))


if __name__ == "__main__":
    unittest.main()
