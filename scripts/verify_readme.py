"""Check every factual claim in release/README.md against release/raw/.

Read-only. Prints CLAIM / ACTUAL / verdict for each. Nothing is edited here;
this exists so no number goes into the public README that wasn't re-derived
from the raw files in the same session.
"""
import csv, glob, sys, pathlib, collections

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
for _l in (sys.maxsize, 2**31 - 1, 2**27):
    try:
        csv.field_size_limit(_l); break
    except OverflowError:
        continue

RAW = ROOT / "release" / "raw"

def rows(p):
    with open(p, newline="", encoding="utf-8", errors="replace") as fh:
        return list(csv.DictReader(fh))

per = collections.defaultdict(lambda: {"logged": 0, "usable": 0, "err": collections.Counter()})
cloud_files = sorted(glob.glob(str(RAW / "cloud_*.csv")))
for p in glob.glob(str(RAW / "*.csv")):
    for r in rows(p):
        m = (r.get("model") or "?").strip()
        if not m or m == "?":
            continue
        per[m]["logged"] += 1
        if r.get("error"):
            per[m]["err"][r["error"][:60]] += 1
        else:
            per[m]["usable"] += 1

def check(label, claim, actual):
    ok = "OK " if str(claim) == str(actual) else "FIX"
    print(f"[{ok}] {label}\n      claim : {claim}\n      actual: {actual}")

print("=" * 72)
check("L25: number of cloud_*.csv files", "16", len(cloud_files))
cloud_models = set()
for p in cloud_files:
    for r in rows(p):
        if r.get("model"):
            cloud_models.add(r["model"].strip())
check("L25: distinct models in cloud_*.csv", "16", len(cloud_models))
full90 = [m for m in cloud_models if per[m]["logged"] == 90]
check("L25: cloud models with exactly 90 logged rows", "16", len(full90))

for m, claim_logged, claim_usable in (("nemotron-3-nano:30b", 34, 32),
                                      ("qwen3.5:397b", None, 89),
                                      ("kimi-k2.6", None, 87)):
    d = per[m]
    if claim_logged is not None:
        check(f"L112: {m} logged", claim_logged, d["logged"])
    check(f"L112/116: {m} usable", claim_usable, d["usable"])

d = per["kimi-k3"]
print(f"[   ] L108: kimi-k3 logged={d['logged']} usable={d['usable']}")
print(f"      error(s): {dict(d['err'])}")

g = per["gemini-3.6-flash"]
errs = sum(g["err"].values())
check("L118: gemini-3.6-flash errored rows", "3", errs)
print(f"      error(s): {dict(g['err'])}")

cs = per["claude-sonnet-5"]
print(f"[   ] L120: claude-sonnet-5 errored={sum(cs['err'].values())} -> {dict(cs['err'])}")

print("=" * 72)
print("models with ANY errored rows in the snapshot:")
for m, d in sorted(per.items()):
    if d["err"]:
        print(f"   {m:24s} logged={d['logged']:3d} usable={d['usable']:3d} "
              f"errored={sum(d['err'].values()):3d}  {list(d['err'])[0][:52]}")

tot_logged = sum(d["logged"] for d in per.values())
tot_usable = sum(d["usable"] for d in per.values())
print("=" * 72)
print(f"snapshot totals: {tot_logged} logged rows, {tot_usable} usable, {len(per)} distinct models")
