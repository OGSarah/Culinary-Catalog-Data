#!/usr/bin/env python3
"""
Populate real YouTube (and source) URLs in data/recipes.master.json by looking
up each dish on TheMealDB by its meal ID.

TheMealDB returns a canonical `strYoutube` (a real youtube.com/watch?v=… link)
and often a `strSource` for every meal. This script fetches those by ID and
writes them into the master, replacing the YouTube-search fallbacks. Recipes
not present in the mapping (e.g. dishes TheMealDB doesn't carry) are left as-is.

Run from the repository root:

    python scripts/enrich_links.py

Then regenerate the feeds:

    python scripts/generate.py

The script is idempotent and uses only the Python standard library.
"""
from __future__ import annotations
import json
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
MASTER = ROOT / "data" / "recipes.master.json"
LOOKUP = "https://www.themealdb.com/api/json/v1/1/lookup.php?i={id}"

# Recipe name (as it appears in the master) -> TheMealDB meal ID.
MEAL_IDS = {
    "Apam Balik": "53049",
    "Bakewell Tart": "52767",
    "Eton Mess": "52791",
    "Sticky Toffee Pudding": "52883",
    "Treacle Tart": "52892",
    "New York Cheesecake": "52858",
    "Chocolate Gateau": "52776",
    "Pasteis de Nata": "53046",        # "Portuguese custard tarts" on TheMealDB
    "Carrot Cake": "52897",
    "Krispy Kreme Donut": "53015",
    "Apple Frangipan Tart": "52768",
    "Budino Di Ricotta": "52961",
    "Chinon Apple Tarts": "52910",
    "Rock Cakes": "52901",
    "Strawberry Rhubarb Pie": "53005",
}


def is_fallback_youtube(url: str) -> bool:
    """True if the link is empty or a YouTube *search* placeholder (not a video)."""
    return (not url) or "youtube.com/results" in url


def is_fallback_source(url: str) -> bool:
    """True if the link is empty or a search-engine placeholder."""
    return (not url) or "google.com/search" in url


def fetch_meal(meal_id: str) -> dict:
    url = LOOKUP.format(id=meal_id)
    with urllib.request.urlopen(url, timeout=20) as resp:
        payload = json.load(resp)
    meals = payload.get("meals") or []
    if not meals:
        raise RuntimeError(f"no meal returned for id {meal_id}")
    return meals[0]


def main() -> None:
    data = json.loads(MASTER.read_text())
    updated = 0
    skipped: list[str] = []

    for recipe in data["recipes"]:
        meal_id = MEAL_IDS.get(recipe["name"])
        if not meal_id:
            skipped.append(recipe["name"])
            continue
        try:
            meal = fetch_meal(meal_id)
        except Exception as exc:  # network/transient
            print(f"WARN: {recipe['name']} (id {meal_id}): {exc}", file=sys.stderr)
            skipped.append(recipe["name"])
            continue

        youtube = (meal.get("strYoutube") or "").strip()
        source = (meal.get("strSource") or "").strip()
        changed = False
        if youtube and is_fallback_youtube(recipe.get("youtube_url", "")):
            recipe["youtube_url"] = youtube
            changed = True
        if source and is_fallback_source(recipe.get("source_url", "")):
            recipe["source_url"] = source
            changed = True
        if changed:
            updated += 1
            print(f"OK: {recipe['name']} -> {youtube or '(no youtube)'}")
        else:
            print(f"-- {recipe['name']}: already set, leaving as-is")

    MASTER.write_text(json.dumps(data, indent=2) + "\n")
    print(f"\nEnriched {updated} recipe(s); skipped {len(skipped)}: {skipped or 'none'}")
    print("Next: python scripts/generate.py")


if __name__ == "__main__":
    main()
