"""Inspect secret-scanner hits in release/raw-v2 WITHOUT printing any credential.

Prints the matched pattern class, the CSV column it lives in, and a masked
excerpt (first 4 and last 2 characters only). If a hit is a real key this is
enough to confirm it and rotate; it is never enough to leak it.
"""
import csv, re, sys, pathlib, collections

ROOT = pathlib.Path(__file__).resolve().parent.parent
for _l in (sys.maxsize, 2**31 - 1, 2**27):
    try:
        csv.field_size_limit(_l); break
    except OverflowError:
        continue

PATTERNS = {
    "openai-style sk-":   re.compile(r"sk-[A-Za-z0-9_\-]{16,}"),
    "anthropic sk-ant-":  re.compile(r"sk-ant-[A-Za-z0-9_\-]{16,}"),
    "google AIza":        re.compile(r"AIza[0-9A-Za-z_\-]{30,}"),
    "xai-":               re.compile(r"xai-[A-Za-z0-9]{20,}"),
    "github token":       re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}"),
    "private key block":  re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "aws AKIA":           re.compile(r"AKIA[0-9A-Z]{16}"),
    "auth header name":   re.compile(r"x-api-key|Authorization|x-goog-api-key", re.I),
}

def mask(s):
    s = s.strip()
    return f"{s[:4]}...{s[-2:]}  (len {len(s)})" if len(s) > 8 else "<short>"

found = collections.Counter()
for p in sorted((ROOT / "release" / "raw-v2").rglob("*.csv")):
    with open(p, newline="", encoding="utf-8", errors="replace") as fh:
        for i, row in enumerate(csv.DictReader(fh), start=2):
            for col, val in row.items():
                if not val:
                    continue
                for name, rx in PATTERNS.items():
                    m = rx.search(val)
                    if not m:
                        continue
                    key = (name, col)
                    found[key] += 1
                    if found[key] <= 2:
                        ctx = val[max(0, m.start() - 60):m.start()].replace("\n", " ")
                        print(f"[{name}] {p.name} row {i}, column '{col}'")
                        print(f"    match : {mask(m.group(0))}")
                        print(f"    before: ...{ctx[-60:]}")
print("\n--- totals by (pattern, column) ---")
for (name, col), n in sorted(found.items(), key=lambda x: -x[1]):
    print(f"  {n:5d}  {name:20s} in column '{col}'")
