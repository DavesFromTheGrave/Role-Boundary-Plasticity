"""Triage: did the saved raw responses ever contain a reasoning/thinking channel?

Answers one question before any rescoring decision is made: for which arms is
`detected` recoverable from data already on disk, and for which would it require
a re-run?

Reads every out/*.csv, looks inside `raw_json` for a thinking field in the two
shapes the harness could have received it:
  - Ollama:    {"message": {"thinking": "..."}}
  - Anthropic: {"content": [{"type": "thinking", "thinking": "..."}]}

Prints a per-arm table. Writes nothing.
"""

import csv
import glob
import json
import os
import sys
from collections import defaultdict

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")


def extract_thinking(raw: str):
    """Return the thinking string if the response carried one, else None.

    None means 'no thinking field present at all'. An empty string means the
    field was present but blank, which is a different fact and worth separating.
    """
    if not raw:
        return None
    try:
        j = json.loads(raw)
    except Exception:
        return None
    if not isinstance(j, dict):
        return None

    msg = j.get("message")
    if isinstance(msg, dict) and "thinking" in msg:
        return msg.get("thinking") or ""

    content = j.get("content")
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "thinking":
                return block.get("thinking") or ""

    # some providers nest under choices[0].message
    choices = j.get("choices")
    if isinstance(choices, list) and choices:
        m = choices[0].get("message") if isinstance(choices[0], dict) else None
        if isinstance(m, dict):
            for k in ("thinking", "reasoning", "reasoning_content"):
                if k in m:
                    return m.get(k) or ""
    return None


def main() -> None:
    arms = defaultdict(lambda: {"rows": 0, "field_present": 0, "nonempty": 0, "chars": 0})
    no_raw_col = {}
    total = 0

    for path in sorted(glob.glob(os.path.join(OUT, "*.csv"))):
        name = os.path.basename(path)
        with open(path, encoding="utf-8", newline="") as f:
            rd = csv.DictReader(f)
            fields = rd.fieldnames or []
            if "raw_json" not in fields:
                no_raw_col[name] = sum(1 for _ in rd)
                continue
            for r in rd:
                total += 1
                key = (r.get("provider", "?"), r.get("model", "?"))
                d = arms[key]
                d["rows"] += 1
                t = extract_thinking(r.get("raw_json"))
                if t is None:
                    continue
                d["field_present"] += 1
                if t.strip():
                    d["nonempty"] += 1
                    d["chars"] += len(t)

    print(f"rows carrying raw_json: {total}\n")
    print(f"{'provider':<12}{'model':<30}{'rows':>6}{'field':>8}{'nonempty':>10}{'avgchars':>10}  verdict")
    print("-" * 92)
    for key in sorted(arms, key=lambda k: (k[0], k[1])):
        v = arms[key]
        avg = int(v["chars"] / v["nonempty"]) if v["nonempty"] else 0
        if v["nonempty"]:
            verdict = "RESCORABLE"
        elif v["field_present"]:
            verdict = "field present but always blank"
        else:
            verdict = "NO thinking captured -> re-run or mark not-measurable"
        print(f"{key[0]:<12}{key[1]:<30}{v['rows']:>6}{v['field_present']:>8}"
              f"{v['nonempty']:>10}{avg:>10}  {verdict}")

    if no_raw_col:
        print(f"\nfiles with no raw_json column (already-rescored derivatives, not sources):")
        for k, n in sorted(no_raw_col.items()):
            print(f"  {k}  ({n} rows)")


if __name__ == "__main__":
    main()
