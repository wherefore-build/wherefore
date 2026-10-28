"""deck/one-pager.svg: the one-page deck, from the same facts as the landing page."""
from kit import COMPANY, PRODUCT, ROOT, dollars, litres, made_where

OUT = ROOT / "deck/one-pager.svg"
lines = [
    PRODUCT["name"],
    f"{litres(PRODUCT['capacity_l'])} · {PRODUCT['boil_minutes']} minutes to the boil",
    f"{dollars(PRODUCT['price_usd'])} · {PRODUCT['warranty_years']}-year warranty",
    made_where(),
    COMPANY["name"],
]
texts = "\n".join(f'  <text x="40" y="{80 + 60 * i}" font-size="{36 if i == 0 else 22}">{t}</text>'
                  for i, t in enumerate(lines))
svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
  <rect width="1280" height="720" fill="#f6f1e7"/>
{texts}
</svg>
"""
OUT.parent.mkdir(exist_ok=True)
OUT.write_text(svg, encoding="utf-8")
