# Culinary Catalog — Data Service

Backing data for the [**Culinary Catalog**](https://github.com/OGSarah/Culinary-Catalog)
iOS app: a set of versioned JSON feeds describing dessert recipes, served as
static assets over HTTPS via GitHub Pages.

The app is a SwiftUI client with a Core Data cache and an `async/await`
networking layer. On launch it fetches a recipe feed, decodes it, and persists
the results for offline browsing and search. This repository owns the data and
guarantees the wire format that client depends on.

There is no application server. The single source of truth is one JSON file;
everything the app consumes is generated from it, validated in CI, and published
automatically.

---

## Contract

The app decodes a top-level `recipes` array of objects with exactly these
fields. This shape is a stable contract — generated feeds never include
anything outside it.

| Field             | Type      | Notes                                                        |
| ----------------- | --------- | ------------------------------------------------------------ |
| `uuid`            | `String`  | RFC 4122 UUID. Stable identifier; used as the Core Data key. |
| `name`            | `String`  | Display name.                                                |
| `cuisine`         | `String`  | Cuisine of origin (e.g. `British`, `Italian`).               |
| `photo_url_small` | `String`  | Thumbnail image URL.                                         |
| `photo_url_large` | `String`  | Full-size image URL.                                         |
| `source_url`      | `String`  | Original recipe page. **Treat as optional client-side.**     |
| `youtube_url`     | `String`  | Video walkthrough. **Treat as optional client-side.**        |

```json
{
  "recipes": [
    {
      "uuid": "0c6ca6e7-e32a-4053-b824-1dbf749910d8",
      "name": "Apam Balik",
      "cuisine": "Malaysian",
      "photo_url_small": "https://…",
      "photo_url_large": "https://…",
      "source_url": "https://…",
      "youtube_url": "https://…"
    }
  ]
}
```

> **Client note:** model `source_url` and `youtube_url` as optional
> (`String?`). They are populated for every record today, but optionality keeps
> decoding resilient if a future entry omits them — a single non-optional field
> would otherwise fail the entire decode.

Keys use `snake_case`. Decode with
`decoder.keyDecodingStrategy = .convertFromSnakeCase` or explicit `CodingKeys`.

---

## Architecture

A single authored file fans out into purpose-built feeds at build time:

```
data/recipes.master.json        Source of truth — the only file authored by hand
        │
        │  scripts/generate.py   Validate, then derive every published feed
        ▼
recipes.json                     All recipes (the app's default feed)
desserts.json                    By category: Dessert
cuisine/<slug>.json              By cuisine: british, italian, french, …
index.json                       Manifest: every feed and its record count
```

The master file may carry an authoring-only `category` key per record. It is
used solely to partition the category feeds and is **stripped** from all
generated output, so it never reaches the client and requires no model changes.

Because the catalog is dessert-only at present, `recipes.json` and
`desserts.json` are currently identical. They are kept as distinct endpoints so
the client can pin to a semantic feed without assuming the catalog's scope.

### Why static files

The dataset is small, read-only from the client's perspective, and changes
infrequently. A static, CDN-backed feed is therefore the right tool: zero
runtime cost, no cold starts, no operational surface, and every change is a
reviewable, revertible commit. Promoting this to a dynamic API would add
infrastructure without serving a present requirement; the generated layout
deliberately mirrors REST-style paths so that migration stays cheap if needs
change.

---

## Endpoints

Once GitHub Pages is enabled, feeds are served from the repository root:

```
https://<owner>.github.io/<repo>/recipes.json
https://<owner>.github.io/<repo>/desserts.json
https://<owner>.github.io/<repo>/cuisine/british.json
https://<owner>.github.io/<repo>/index.json
```

All endpoints are HTTPS, so no App Transport Security exceptions are required in
the client's `Info.plist`.

---

## Authoring workflow

1. Edit `data/recipes.master.json` only. Provide all seven contract fields per
   record, plus an optional `category`.
2. Commit and open a pull request. CI runs in validation mode and blocks the
   merge if the data is invalid or the committed feeds are stale.
3. On merge to `main`, CI regenerates every feed, commits the result, and
   GitHub Pages redeploys.

Authors never hand-edit generated files; they are build artifacts.

---

## Continuous integration

The `Build recipe feeds` workflow (`.github/workflows/build-recipes.yml`):

- **Pull requests** — runs `generate.py --check`: validates the dataset and
  fails if any feed would change, guaranteeing committed artifacts always match
  the source.
- **Push to `main` / manual dispatch** — regenerates all feeds and commits them
  back using the built-in `GITHUB_TOKEN`. Token-authored pushes do not
  re-trigger workflows, so there is no build loop.

Validation rejects missing or empty required fields, malformed UUIDs, and
duplicate UUIDs, with actionable per-record error messages in the run log.

---

## Local development

Requires Python 3.12+. No third-party dependencies.

```bash
python scripts/generate.py          # validate, then (re)write all feeds
python scripts/generate.py --check  # validate only; non-zero exit if feeds are stale
```

---

## Repository layout

```
.
├── data/
│   └── recipes.master.json         Source of truth (authored)
├── scripts/
│   └── generate.py                 Validator and feed generator
├── cuisine/                        Generated per-cuisine feeds
├── recipes.json                    Generated
├── desserts.json                   Generated
├── index.json                      Generated manifest
└── .github/workflows/
    └── build-recipes.yml           CI: validate on PR, publish on main
```

---

## Operational notes

- **Caching.** GitHub Pages is served through a CDN; published changes may take
  a minute or two to propagate. The client should not assume read-after-write.
- **Assets.** Image URLs currently use deterministic placeholder images so feeds
  always render; replace them with production photography in the master file as
  it becomes available. `source_url` and `youtube_url` resolve to stable search
  links that open correctly in a web view.
- **Visibility.** The repository must be public for GitHub Pages on the free
  tier.
