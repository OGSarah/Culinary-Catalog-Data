#!/usr/bin/env python3
"""
Validate data/recipes.master.json and generate the app-facing feed files.

Source of truth:  data/recipes.master.json   (you edit this; may include a
                                               generator-only "category" key)
Generated feeds:  recipes.json                (full list)
                  <category>.json             (e.g. desserts.json)
                  cuisine/<slug>.json          (e.g. cuisine/british.json)
                  index.json                   (manifest of every feed + counts)

Usage:
    python scripts/generate.py            # validate + (re)write feeds
    python scripts/generate.py --check    # validate only; fail if feeds are stale
"""
from __future__ import annotations
import json
import re
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
MASTER = ROOT / "data" / "recipes.master.json"

REQUIRED = [
    "uuid",
    "name",
    "cuisine",
    "photo_url_small",
    "photo_url_large",
    "source_url",
    "youtube_url",
]
UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def fail(message: str) -> None:
    print(f"::error::{message}")
    sys.exit(1)


def load_master() -> list[dict]:
    if not MASTER.exists():
        fail(f"missing source file: {MASTER.relative_to(ROOT)}")
    try:
        data = json.loads(MASTER.read_text())
    except json.JSONDecodeError as exc:
        fail(f"{MASTER.name} is not valid JSON: {exc}")
    if not isinstance(data, dict) or not isinstance(data.get("recipes"), list):
        fail('source file must be an object with a top-level "recipes" array')
    return data["recipes"]


def validate(recipes: list[dict]) -> None:
    errors: list[str] = []
    seen: set[str] = set()
    for i, recipe in enumerate(recipes):
        label = recipe.get("name", "<no name>")
        for key in REQUIRED:
            if not recipe.get(key):
                errors.append(f"recipe #{i} ({label}): missing or empty '{key}'")
        uuid_val = recipe.get("uuid", "")
        if uuid_val and not UUID_RE.match(uuid_val):
            errors.append(f"recipe #{i} ({label}): invalid uuid '{uuid_val}'")
        if uuid_val in seen:
            errors.append(f"recipe #{i} ({label}): duplicate uuid '{uuid_val}'")
        seen.add(uuid_val)
    if errors:
        fail("validation failed:\n  - " + "\n  - ".join(errors))


def app_fields(recipe: dict) -> dict:
    """Strip helper keys (e.g. 'category'); emit only what the app decodes."""
    return {key: recipe[key] for key in REQUIRED}


def feed(recipes: list[dict]) -> str:
    payload = {"recipes": [app_fields(r) for r in recipes]}
    return json.dumps(payload, indent=2) + "\n"


def build(recipes: list[dict]) -> dict[str, str]:
    files: dict[str, str] = {"recipes.json": feed(recipes)}

    # One feed per category (desserts.json, ...)
    categories: dict[str, list[dict]] = {}
    for r in recipes:
        cat = r.get("category")
        if cat:
            categories.setdefault(slugify(cat), []).append(r)
    for slug, items in categories.items():
        name = "desserts.json" if slug == "dessert" else f"{slug}s.json"
        files[name] = feed(items)

    # One feed per cuisine (cuisine/british.json, ...)
    cuisines: dict[str, list[dict]] = {}
    for r in recipes:
        cuisines.setdefault(slugify(r["cuisine"]), []).append(r)
    for slug, items in cuisines.items():
        files[f"cuisine/{slug}.json"] = feed(items)

    manifest = {
        "generated_count": len(recipes),
        "feeds": sorted(
            [{"path": p, "count": len(json.loads(b)["recipes"])} for p, b in files.items()],
            key=lambda x: x["path"],
        ),
    }
    files["index.json"] = json.dumps(manifest, indent=2) + "\n"
    return files


def write(files: dict[str, str], check_only: bool) -> None:
    stale: list[str] = []
    for rel, body in files.items():
        path = ROOT / rel
        current = path.read_text() if path.exists() else None
        if current == body:
            continue
        if check_only:
            stale.append(rel)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body)
    if check_only and stale:
        fail(
            "feeds are out of date. Run `python scripts/generate.py` and commit:\n  - "
            + "\n  - ".join(stale)
        )


def main() -> None:
    check_only = "--check" in sys.argv
    recipes = load_master()
    validate(recipes)
    files = build(recipes)
    write(files, check_only)
    verb = "validated" if check_only else "generated"
    print(f"OK: {verb} {len(files)} feed(s) from {len(recipes)} recipe(s).")


if __name__ == "__main__":
    main()
