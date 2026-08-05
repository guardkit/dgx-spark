# Task T5: reorganize the working directory (effects, not words)

> This brief is identical in every harness tier. Deliverable: the **resulting state of the
> filesystem** — a reorganized `work/` tree plus `manifest.json` in the workspace root.
> Nothing the model *says* is scored; only what is actually on disk afterwards.

## The brief

`work/` is a messy tree of files (recreate a pristine copy any time with
`cd validate && npm run reset`). Reorganize it **in place** into
`work/organized/<YYYY>/<MM>/<category>/<filename>` and write a manifest. Nothing may be
lost, duplicated, or byte-altered.

## Rules

1. **Category** by extension, case-insensitive:
   `docs` = pdf txt md doc docx · `images` = jpg jpeg png gif · `data` = csv zip json xls
   xlsx · `other` = everything else (including no extension).
2. **Date** (UTC), first rule that applies to the *filename* wins:
   a. an ISO `YYYY-MM-DD` substring;
   b. the first 8-digit run that parses as a valid `YYYYMMDD` date;
   c. an English `DD Mon YYYY` (e.g. `14 Jul 2026`);
   d. otherwise the file's **mtime** (UTC).
   Note: name-derived dates win **even when the mtime disagrees**.
3. **Collisions** (same target directory + filename): process files in lexicographic order
   of their original relative path; the first keeps its name, later ones get `-1`, `-2`, …
   before the extension (`report.txt` → `report-1.txt`).
4. Afterwards `work/` contains **only** `organized/` — original subdirectories (including
   empty ones) are removed. Filenames are otherwise preserved.
5. **`manifest.json`** in the workspace root: a JSON array sorted by `newPath`, one entry
   per file:
   ```json
   { "originalPath": "work/inbox/invoice_2026-03-12.pdf",
     "newPath": "work/organized/2026/03/docs/invoice_2026-03-12.pdf",
     "sizeBytes": 123, "sha256": "<hex>" }
   ```
   Paths are relative to the workspace root, forward slashes. `sha256` is of the file
   content (which must be unchanged).

## Acceptance checklist

1. Every original file present under `organized/` exactly once, bytes identical.
2. Every file in the correct `<YYYY>/<MM>/<category>/` per the rules (mtime decoys not taken).
3. Collision handling exactly as specified; no empty directories; nothing outside
   `organized/` except the manifest.
4. `manifest.json` accurate for every entry (paths, sizes, hashes) and sorted.
