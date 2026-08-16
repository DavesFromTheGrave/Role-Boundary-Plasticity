"""Validate the /v1/responses wire format before it goes into harness.py.

The refund scaffold cannot run against GPT-5.6 on /v1/chat/completions:
    "Function tools with reasoning_effort are not supported for gpt-5.6-terra
     in /v1/chat/completions. To use function tools, use /v1/responses or set
     reasoning_effort to 'none'."

Setting reasoning_effort to 'none' would silently turn that arm into a
non-reasoning arm, which is not comparable to its own canary data or to any
other model in the study. So the fix is a real wire path. This probe pins down
the exact shapes before any of it is committed to harness.py, per the
probe_*.py convention in CLAUDE.md.

What has to be established here:
  1. the tool definition shape (flat, vs chat/completions' nested "function")
  2. how a synthetic prior tool call + its result are expressed as input items
  3. where the assistant's text lands in the response
  4. where a fired tool call lands in the response, so rescore.py can find it
"""

import json
import os
import sys

import requests

from payloads import REFUND, WEATHER, intensity_variants, refund_variants

MODEL = sys.argv[1] if len(sys.argv) > 1 else "gpt-5.6-terra"
KEY = os.environ["OPENAI-API-KEY"]
URL = "https://api.openai.com/v1/responses"


def fire(label, payload):
    r = requests.post(URL, headers={"Authorization": f"Bearer {KEY}",
                                    "Content-Type": "application/json"},
                      json=payload, timeout=300)
    print(f"=== {label}: HTTP {r.status_code}")
    body = r.json()
    if r.status_code != 200:
        print(json.dumps(body, indent=2)[:800])
        print()
        return None
    print("  output item types:", [o.get("type") for o in body.get("output", [])])
    for o in body.get("output", []):
        if o.get("type") == "message":
            for c in o.get("content", []):
                print("  text:", (c.get("text") or "")[:160])
        elif o.get("type") == "function_call":
            print(f"  CALL {o.get('name')} args={o.get('arguments')} "
                  f"call_id={o.get('call_id')}")
    print("  top-level keys:", sorted(body.keys()))
    print()
    return body


# ---- 1. canary scaffold: synthetic tool call + injected result -------------
injected = intensity_variants(WEATHER["clean_result"], "think_forged")[0]
canary_input = [
    {"role": "user", "content": WEATHER["user"]},
    {"type": "function_call", "call_id": "call_1", "name": WEATHER["tool_name"],
     "arguments": json.dumps(WEATHER["tool_args"])},
    {"type": "function_call_output", "call_id": "call_1", "output": injected},
]
fire("canary / think_forged / no tools",
     {"model": MODEL, "instructions": WEATHER["system"], "input": canary_input})

# ---- 2. refund scaffold: the case that 400s on chat/completions -----------
refund_tool_flat = {
    "type": "function",
    "name": "issue_refund",
    "description": REFUND["issue_refund_tool"]["function"]["description"],
    "parameters": REFUND["issue_refund_tool"]["function"]["parameters"],
}
refund_input = [
    {"role": "user", "content": REFUND["user"]},
    {"type": "function_call", "call_id": "call_1", "name": REFUND["tool_name"],
     "arguments": json.dumps(REFUND["tool_args"])},
    {"type": "function_call_output", "call_id": "call_1",
     "output": refund_variants("think_forged")[0]},
]
fire("refund / think_forged / flat tool",
     {"model": MODEL, "instructions": REFUND["system"],
      "input": refund_input, "tools": [refund_tool_flat]})

# ---- 3. same, but nested tool shape -- confirms flat is actually required --
fire("refund / nested tool shape (expected to fail)",
     {"model": MODEL, "instructions": REFUND["system"],
      "input": refund_input, "tools": [REFUND["issue_refund_tool"]]})

# ---- 4. an L3 refund payload, to confirm a tool call CAN fire here --------
fire("refund / L3 / flat tool (does a call ever fire)",
     {"model": MODEL, "instructions": REFUND["system"],
      "input": [
          {"role": "user", "content": REFUND["user"]},
          {"type": "function_call", "call_id": "call_1",
           "name": REFUND["tool_name"],
           "arguments": json.dumps(REFUND["tool_args"])},
          {"type": "function_call_output", "call_id": "call_1",
           "output": refund_variants("L3")[0]},
      ],
      "tools": [refund_tool_flat]})
