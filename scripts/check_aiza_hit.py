"""Identify the JSON field the AIza-pattern match lives in, without printing it."""
import csv, json, re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
for _l in (sys.maxsize, 2**31 - 1, 2**27):
    try:
        csv.field_size_limit(_l); break
    except OverflowError:
        continue

RX = re.compile(r"AIza[0-9A-Za-z_\-]{30,}")
p = ROOT / "release" / "raw-v2" / "cot" / "cot_gpt-5_6-sol.csv"

def walk(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk(v, f"{path}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, f"{path}[{i}]")
    elif isinstance(o, str):
        yield path, o

with open(p, newline="", encoding="utf-8", errors="replace") as fh:
    for i, row in enumerate(csv.DictReader(fh), start=2):
        raw = row.get("raw_json") or ""
        if not RX.search(raw):
            continue
        print(f"row {i}  model={row.get('model')}  provider={row.get('provider')}")
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            print("  raw_json is not valid JSON")
            continue
        for path, val in walk(obj):
            m = RX.search(val)
            if m:
                print(f"  JSON field : {path}")
                print(f"  field len  : {len(val)} chars")
                print(f"  match len  : {len(m.group(0))} chars "
                      f"(a real Google API key is exactly 39)")
                print(f"  match starts at offset {m.start()} of the field, "
                      f"so it is {'EMBEDDED inside a longer blob' if m.start() > 0 else 'AT THE START'}")
        # what keys exist at the top level tells us what kind of object this is
        print(f"  top-level keys: {sorted(obj)[:12]}")
        if isinstance(obj.get("output"), list):
            print(f"  output item types: {[it.get('type') for it in obj['output'] if isinstance(it, dict)]}")
