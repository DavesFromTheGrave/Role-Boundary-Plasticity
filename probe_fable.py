"""Characterise Claude Fable 5's API-level refusal behaviour on this experiment.

Fable ships elevated cyber safeguards; its classifiers can decline a request
outright (HTTP 200, stop_reason='refusal', empty content). That is NOT the model
resisting an injection -- the request never ran -- so it cannot be scored on the
same axis as the other arms. This probe establishes whether the refusal is
universal or specific to the injected conditions.
"""
import os
import sys

import harness
from payloads import WEATHER, intensity_variants

key = os.environ["ANTHROPIC_API_KEY"]
levels = sys.argv[1:] or [
    "control", "L1", "L2", "L3", "L3_notags",
    "forged_generic", "forged_chatml", "forged_plain_label",
]

for lv in levels:
    sysmsg, msgs = harness.build_anthropic_tool_result(
        WEATHER, intensity_variants(WEATHER["clean_result"], lv)[0]
    )
    try:
        r = harness.call_model("anthropic", "claude-fable-5", msgs, None, None, key, system=sysmsg)
    except Exception as e:
        print(f"{lv:22s} ERROR {type(e).__name__}: {e}")
        continue
    text, _ = harness.extract_reply(r, "anthropic")
    stop = r.get("stop_reason")
    det = r.get("stop_details") or {}
    print(f"{lv:22s} stop={str(stop):9s} cat={det.get('category')} len={len(text):4d} {text[:70]!r}")
