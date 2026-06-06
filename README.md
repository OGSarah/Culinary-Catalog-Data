# Culinary Catalog — recipe feeds

Static, version-controlled JSON feeds for the Culinary Catalog iOS app, served
free over HTTPS via GitHub Pages. There is no server to run: you edit one file,
push, and a GitHub Action regenerates every feed automatically.

## How it works

```
data/recipes.master.json   ← the ONLY file you edit (source of truth)
        │
        │  scripts/generate.py  (run automatically by GitHub Actions)
        ▼
recipes.json               ← full list (all desserts)  app points here
desserts.json              ← category: Dessert  (same as recipes.json today)
cuisine/british.json       ← cuisine: British
cuisine/italian.json       ← …one per cuisine
index.json                 ← manifest of every feed + its recipe count
```

Every generated feed has the identical shape your app already decodes:

```json
{ "recipes": [ { "uuid": "...", "name": "...", "cuisine": "...",
                 "photo_url_small": "...", "photo_url_large": "...",
                 "source_url": "...", "youtube_url": "..." } ] }
```

The master file may also carry a `"category"` key per recipe. It is used only
by the build script to split feeds and is **stripped** from every generated
file, so your app's model needs no changes.

## One-time setup

1. Create a **public** repo (e.g. `culinary-data`) and push these files to `main`.
2. **Settings → Pages → Build and deployment → Deploy from a branch**, choose
   `main` / `/ (root)`, save.
3. After Pages builds, your feeds live at:
   - `https://<you>.github.io/culinary-data/recipes.json`
   - `https://<you>.github.io/culinary-data/desserts.json`
   - `https://<you>.github.io/culinary-data/cuisine/british.json`
4. Put the URL you want into your app's networking layer. HTTPS, so no
   `Info.plist` ATS changes are needed.

## Adding or editing recipes

1. Edit `data/recipes.master.json` only. Give each recipe all seven app fields
   plus an optional `"category"`.
2. Commit and push to `main`.
3. The **Build recipe feeds** Action validates the data, regenerates every
   feed, and commits the results back. Pages redeploys automatically.

If you open a pull request instead, the Action runs in validate-only mode and
fails the check when the data is invalid or the feeds are out of date — so bad
data never reaches `main`.

## Run it locally

```bash
python scripts/generate.py          # validate + rewrite feeds
python scripts/generate.py --check  # validate only (used by PR checks)
```

Validation rejects: missing/empty required fields, malformed UUIDs, and
duplicate UUIDs.

## Notes

- GitHub Pages is CDN-cached, so an edit can take a minute or two to appear.
- Image URLs use seeded placeholders that always load; swap in real photo URLs
  in the master file whenever you like.
- `source_url` / `youtube_url` point to search links, which always resolve in a
  web view.
