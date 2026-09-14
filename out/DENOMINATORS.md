# Denominators & corpus reconciliation (live-checked 2026-09-10)

Machine: Yggdrasil. Project: `M:\Projects\Anthropic-Fellows\role-boundary-plasticity`.
Rule: **Import-Csv / `csv.DictReader` row counts only. Never `wc -l`.**

## Headline numbers (Import-Csv)

| Artifact | Rows | Bytes | mtime (local / America/Chicago wall from FS) | Role |
|---|---:|---:|---|---|
| `out/rescored_all.csv` | **2700** | 912711 | 2026-08-10 08:03:04 | Frozen pre-cloud snapshot. **Stale as live main.** |
| `out/cloud_*.csv` (18 files) | **1564** | — | 2026-08-10 23:53 → 2026-08-11 02:41 | Cloud large-tier raws. In `out/*.csv` glob. |
| `out/annotated/annotated_main.csv` | **4264** | 1748811 | 2026-08-26 04:44:02 | Live main after `rescore.load_all()` dedupe + annotate. **Paper-facing main.** |
| `out/cot/cot_all_scored.csv` | **1652** | 1250733 | 2026-08-16 04:55:32 | CoT rollup (derived). |
| `out/annotated/annotated_cot.csv` | **1452** | 1386782 | 2026-08-26 04:44:02 | CoT after raw-batch dedupe (excludes `cot_all_scored`). |
| `out/local-fill-2026-09-05/*.csv` (15 files) | **378** | — | 2026-09-05 18:54 → 19:28 | Defense/refund local coverage fill. **Not in paper totals.** |

Identity check: `2700 + 1564 = 4264`. Live `python -c "from rescore import load_all; print(len(load_all()))"` → **4264** (matches annotated_main). Cloud attributed inside that live load: **1563** (1 of 1564 nano rows dropped by cross-file dedupe).

`annotated_main.manifest.json` lists source file bytes/sha256; sum of those files' Import-Csv rows = **4480**; after `load_all` dedupe → **4264** (Δ **216**). Dedupe losses concentrated in: `partial_*`, `gemini_retry`, `matched_test`/`defense_test`, `matched_frontier`, `qwen3_think_on`, `new_local_variants`, 1× `cloud_nemotron-3-nano`.

## `rescore.load_all()` glob behavior (confirmed in `rescore.py`)

```text
glob.glob("out/*.csv")          # NON-RECURSIVE
skip if "rescored" | "smoke" | "repeats_5" in path
require row["scaffold"]
dedupe key: (model, scaffold, channel, level, variant, think, request_json[:200])
```

Excluded by non-recursion (invisible to rescore / annotate main):

- `out/cot/**` — separate CoT arm (`annotate.py --corpus cot` / `cot_sources()`)
- `out/annotated/**` — deliberate (annotate comments: putting annotated CSV in `out/` once doubled corpus to 8370)
- `out/local-fill-2026-09-05/**` — coverage fill, never folded

So: **cloud IS included** if you re-run `rescore.py` / `annotate.py` today; **cot and local-fill are not**. The on-disk `rescored_all.csv` simply was not re-run after the cloud batch (mtime 2026-08-10 08:03; cloud files start that night).

## Count-drift mechanisms (with evidence)

### 1. Multiline CSV vs `wc -l`

`response_text` embeds newlines → physical lines ≫ records.

| File | wc -l (Measure-Object -Line) | Import-Csv | Δ |
|---|---:|---:|---:|
| `out/rescored_all.csv` | 5737 | 2700 | 3037 |
| `out/cot/cot_all_scored.csv` | 23393 | 1652 | 21741 |
| `out/local-fill-2026-09-05/defense_smollm2_1_7b.csv` | 11510 | 36 | 11474 |

`annotate.py --verify` already documents the 2026-08-23 “7689 trials” false figure from `wc -l` on the 2700-row file (~2.85×). **AGENTS.md still recommends `wc -l out/rescored_all.csv` — that recipe is wrong.**

### 2. Double-counting raw + aggregate

- Do not sum `rescored_all` + its constituent `out/*.csv` raws.
- Do not sum `cot_all_scored` + `out/cot/cot_*.csv` / `local_*.csv` (`annotate.cot_sources` excludes `*scored*` and `*smoke*` for this reason).
- Do not place annotated CSVs in `out/` (non-recursive glob would re-ingest them).

### 3. Rescore snapshot missing cloud; cot never in rescored_all

- Cloud raws live in `out/cloud_*.csv` and **are** in the `out/*.csv` glob, but `rescored_all.csv` was written **before** they existed → snapshot stays at 2700 until someone re-runs `rescore.py`.
- CoT path is `out/cot/`, outside the glob by design (`annotate.py` / CLAUDE: new arms write to a new file).
- PAPER-v2 already splits: “Core: 2,700 … Large tier: 1,564 …” — those are complementary strata, not alternatives; live union main = annotated_main 4264.

## local-fill-2026-09-05 status: **OUT of paper-facing totals**

Evidence:

1. Directory `out/local-fill-2026-09-05/` → invisible to `glob("out/*.csv")`.
2. Import-Csv sum = **378** (9×36 defense + 6×9 refund).
3. `annotated_main` rows with `timestamp -like '2026-09-05*'` = **0**; same for `rescored_all`.
4. `annotated_main.manifest.json` `source_files` has **no** `local-fill` entries (generated 2026-08-26; fill ran 2026-09-05).
5. Timestamps on fill rows are `2026-09-05T18:…` — after both rescored and annotated snapshots.

Treat as a **coverage-gap fill corpus** pending a deliberate fold (would need either moving/copying into `out/*.csv` with dedupe review, or extending `load_all` / annotate with an explicit subdir allowlist — do **not** silently merge).

## Proposed recipe (non-destructive)

**Prefer this over overwriting `rescored_all.csv`.**

1. Keep raws untouched.
2. Treat **`out/annotated/annotated_main.csv` (4264)** as the current paper-facing **main** denominator (already = live `load_all()`).
3. Treat **`out/annotated/annotated_cot.csv` (1452)** / **`out/cot/cot_all_scored.csv` (1652)** as the CoT arm (document which one a given number uses; they differ because scored rollup ≠ raw-deduped annotate set).
4. Keep **`out/rescored_all.csv` (2700)** as the FINDINGS/PAPER “core” snapshot cited historically; label it **stale vs live**.
5. Inventory regenerator: `python scripts/build_reconciled_ledger.py` → `out/reconciled_ledger.csv` (per-file rows, strata, paper-facing flags, sha256). Does not rewrite aggregates.
6. Optional later: re-run `python rescore.py` only if you intentionally want a new `rescored_all.csv` that includes cloud (would bump 2700 → ~4264). Coordinate with chart/`build_charts.py` consumers first. **Do not** add local-fill or cot into that run without an explicit design pass.
7. Fix AGENTS.md `wc -l` guidance when convenient (docs-only).

## What changed in this reconciliation pass

- Added `scripts/build_reconciled_ledger.py`
- Added this file `out/DENOMINATORS.md`
- After first run: `out/reconciled_ledger.csv`
- **No raws deleted, moved, or overwritten.**

## Regenerating the ledger

```powershell
cd M:\Projects\Anthropic-Fellows\role-boundary-plasticity
python scripts\build_reconciled_ledger.py
# (Import-Csv 'out\reconciled_ledger.csv').Count   # one row per source CSV; ledger file itself is excluded
```

Live-checked again after field-size-limit fix: cot_all_scored=1652, annotated_cot=1452, local-fill sum=378, cloud sum=1564, annotated_main=4264, rescored_all=2700.
