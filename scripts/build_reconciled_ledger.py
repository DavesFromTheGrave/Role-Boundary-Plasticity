"""Build out/reconciled_ledger.csv — source inventory for Role-Boundary-Plasticity.

READ-MOSTLY / non-destructive:
  - Never deletes, moves, or overwrites raw out/*.csv batches.
  - Never touches rescored_all.csv, annotated_*, or cot rollups.
  - Writes ONLY:
      out/reconciled_ledger.csv   (one row per source file)
      (optionally refreshes numbers printed to stdout)

Why this exists (2026-09-10 reconciliation):
  rescored_all.csv is a frozen 2026-08-10 snapshot (2700 rows) taken BEFORE the
  cloud batch landed. annotate.py reuses rescore.load_all() live and therefore
  already folds cloud_*.csv into annotated_main.csv (4264). CoT lives under
  out/cot/ and is invisible to the non-recursive out/*.csv glob. local-fill
  lives under out/local-fill-2026-09-05/ and is likewise excluded.

Denominators must be counted with csv.DictReader / Import-Csv, never wc -l:
  response_text embeds newlines; physical lines overcount true records.
"""

from __future__ import annotations

import csv
import hashlib
import sys

# smollm / CoT rows carry huge response_text; default 128KiB limit lies.
csv.field_size_limit(min(sys.maxsize, 50 * 1024 * 1024))
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
LEDGER = OUT / "reconciled_ledger.csv"


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def csv_row_count(path: Path) -> int:
    with path.open(encoding="utf-8", newline="") as f:
        return sum(1 for _ in csv.DictReader(f))


def physical_newlines(path: Path) -> int:
    with path.open("rb") as f:
        return f.read().count(b"\n")


def classify(rel: str, name: str) -> tuple[str, str, bool]:
    """Return (stratum, role, paper_facing_main)."""
    if rel.startswith("out/annotated/"):
        if name.startswith("annotated_main"):
            return "annotated_main", "derived_aggregate", True
        if name.startswith("annotated_cot"):
            return "annotated_cot", "derived_aggregate", False
        return "annotated_other", "derived", False
    if rel.startswith("out/cot/"):
        if name == "cot_all_scored.csv":
            return "cot_rollup", "derived_aggregate", False
        if "smoke" in name:
            return "cot_smoke", "excluded_smoke", False
        return "cot_raw", "raw_batch", False
    if rel.startswith("out/local-fill-"):
        return "local_fill_2026_09_05", "raw_batch_subdir", False
    if name == "rescored_all.csv":
        return "rescored_snapshot", "derived_aggregate_stale", False
    if any(x in name for x in ("smoke", "repeats_5")):
        return "out_root_excluded", "excluded_by_rescore", False
    if name.startswith("cloud_"):
        return "cloud_raw", "raw_batch", True  # folded into live main / annotated_main
    if name.startswith("partial_"):
        return "partial_raw", "raw_batch_partial", True  # visible to load_all; mostly deduped
    return "main_raw", "raw_batch", True


def iter_csv_files() -> list[Path]:
    files: list[Path] = []
    skip_names = {LEDGER.name, "reconciled_ledger.csv"}
    for p in OUT.rglob("*.csv"):
        if p.name in skip_names:
            continue
        files.append(p)
    return sorted(files)


def build() -> list[dict]:
    rows = []
    generated = datetime.now(timezone.utc).isoformat()
    for path in iter_csv_files():
        rel = path.relative_to(ROOT).as_posix()
        name = path.name
        stratum, role, paper_main = classify(rel, name)
        try:
            n = csv_row_count(path)
        except Exception as e:  # noqa: BLE001 — ledger must not abort on one bad file
            n = -1
            err = str(e)
        else:
            err = ""
        phys = physical_newlines(path) if n >= 0 else -1
        st = path.stat()
        mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat()
        rows.append(
            {
                "generated_utc": generated,
                "path": rel,
                "stratum": stratum,
                "role": role,
                "in_paper_facing_main": "yes" if paper_main else "no",
                "in_rescore_load_all_glob": (
                    "yes"
                    if (path.parent == OUT and not any(x in name for x in ("rescored", "smoke", "repeats_5")))
                    else "no"
                ),
                "rows_import_csv": n,
                "physical_newlines_wc": phys,
                "wc_overcount_delta": (phys - n) if (n >= 0 and phys >= 0) else "",
                "bytes": st.st_size,
                "mtime_utc": mtime,
                "sha256": file_sha256(path) if n >= 0 else "",
                "error": err,
            }
        )
    return rows


def summarize(rows: list[dict]) -> None:
    def sum_stratum(s: str) -> int:
        return sum(int(r["rows_import_csv"]) for r in rows if r["stratum"] == s and int(r["rows_import_csv"]) >= 0)

    print("=== reconciled ledger summary (Import-Csv / DictReader rows) ===")
    print(f"  rescored_all.csv (stale snapshot) : {sum_stratum('rescored_snapshot')}")
    print(f"  cloud_*.csv sum                   : {sum_stratum('cloud_raw')}")
    print(f"  annotated_main.csv                : {sum_stratum('annotated_main')}")
    print(f"  cot_all_scored.csv                : {sum_stratum('cot_rollup')}")
    print(f"  annotated_cot.csv                 : {sum_stratum('annotated_cot')}")
    print(f"  local-fill-2026-09-05 sum         : {sum_stratum('local_fill_2026_09_05')}")
    print(f"  ledger rows written               : {len(rows)}")
    print(f"  output                            : {LEDGER}")


def main() -> None:
    rows = build()
    fieldnames = list(rows[0].keys()) if rows else []
    with LEDGER.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    summarize(rows)


if __name__ == "__main__":
    main()


