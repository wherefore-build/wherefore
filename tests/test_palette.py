"""`wherefore check palette`: every colour is one the brand's source holds, or excused with why."""
import unittest

from _util import repo, wherefore

BRAND = {"color": {"ground": {"value": "#F7F6F2"}, "ink": {"value": "#17181B"}, "accent": {"value": "#3F6B00"}}}
BASE = {"wherefore": 1, "name": "fern"}


def corpus(palette, **files):
    doc = dict(BASE)
    if palette is not None:
        doc["palette"] = palette
    return repo({"wherefore.json": doc, "brand/tokens.json": BRAND, **files})


class OnePalette(unittest.TestCase):
    def test_the_brands_own_values_pass_and_a_stray_one_fails_by_file_and_line(self):
        root = corpus({"source": "brand/tokens.json"},
                      **{"site/page.css": "body { background: #f7f6f2; color: var(--ink); }\n.promo { color: #FF3355; }\n"})
        code, out = wherefore(root, "check", "palette")
        self.assertEqual(code, 1, out)
        self.assertIn("site/page.css:2: #FF3355 - a colour that is not one of brand/tokens.json's", out)
        self.assertNotIn("page.css:1", out, "the brand's own value, in any case, passes")

    def test_a_function_colour_and_a_named_colour_fail_too(self):
        root = corpus({"source": "brand/tokens.json"},
                      **{"gen/site.py": "SHADOW = 'box-shadow: 0 1px rgba(0,0,0,.4)'\n",
                         "site/a.css": ".x { border: 1px solid white; }\n"})
        code, out = wherefore(root, "check", "palette")
        self.assertEqual(code, 1, out)
        self.assertIn("gen/site.py:1: rgba(…)", out)
        self.assertIn("site/a.css:1: white", out)

    def test_a_clean_corpus_passes_and_counts(self):
        root = corpus({"source": "brand/tokens.json", "not_ours": {"vendor/model.html": "another company's page; its own suite holds its brand"}},
                      **{"site/page.css": "body { color: var(--ink); background: #F7F6F2; }\n",
                         "vendor/model.html": "<style>body{background:#123456}</style>\n"})
        code, out = wherefore(root, "check", "palette")
        self.assertEqual(code, 0, out)
        self.assertIn("ok   every colour in 1 files is one of brand/tokens.json's 3; 1 files excused, each with why", out)

    def test_read_limits_what_is_read(self):
        root = corpus({"source": "brand/tokens.json", "read": ["site/**"]},
                      **{"site/page.css": "body { color: #17181B; }\n", "notes/old.css": ".y { color: #ABCDEF; }\n"})
        code, out = wherefore(root, "check", "palette")
        self.assertEqual(code, 0, out)

    def test_no_brand_declined_with_why_passes(self):
        root = corpus({"none": "a parts list: nothing here is coloured"}, **{"a.txt": "plain\n"})
        code, out = wherefore(root, "check", "palette")
        self.assertEqual(code, 0, out)
        self.assertIn("ok   no palette, and why: a parts list", out)

    def test_nothing_declared_fails_in_words(self):
        root = corpus(None, **{"site/page.css": "body { color: #17181B; }\n"})
        code, out = wherefore(root, "check", "palette")
        self.assertEqual(code, 1, out)
        self.assertIn("no palette is declared", out)
        self.assertIn('{"none": "..."}', out)

    def test_a_declaration_that_cannot_be_meant_is_refused(self):
        root = corpus({"source": "brand/tokens.json", "not_ours": {"x.css": ""}})
        code, out = wherefore(root, "check", "palette")
        self.assertNotEqual(code, 0)
        self.assertIn("palette.not_ours['x.css']", out)

    def test_the_gate_says_so_when_the_build_makes_coloured_files_and_nothing_is_declared(self):
        gen = ("import pathlib\n"
               "pathlib.Path('site').mkdir(exist_ok=True)\n"
               "pathlib.Path('site/a.css').write_text('a { color: #17181B; }\\n')\n"
               "pathlib.Path('site/b.css').write_text('b { color: #F7F6F2; }\\n')\n")
        made = {"gen.py": gen, "site/a.css": "a { color: #17181B; }\n", "site/b.css": "b { color: #F7F6F2; }\n",
                "notes/old.css": ".y { color: #ABCDEF; }\n"}
        doc = dict(BASE, generators=[{"script": "gen.py", "cwd": ".", "makes": "two stylesheets"}])
        root = repo({"wherefore.json": doc, "brand/tokens.json": BRAND, **made})
        code, out = wherefore(root, "gate")
        self.assertIn("NOTICE colours are said in 2 files the build made and no palette is declared", out,
                      "the two files the generator wrote count; the brand file and notes/old.css, which "
                      "nothing made, do not - the gate reads nothing for the notice it did not read to judge")
        doc["palette"] = {"source": "brand/tokens.json"}
        root = repo({"wherefore.json": doc, "brand/tokens.json": BRAND, **made})
        code, out = wherefore(root, "gate")
        self.assertNotIn("NOTICE colours", out)

if __name__ == "__main__":
    unittest.main()
