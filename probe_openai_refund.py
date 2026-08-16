"""One-off: capture the 400 body OpenAI returns for the refund scaffold.

harness.py calls raise_for_status(), which throws away the response body, so
the CSV only records "400 Client Error". This fires the exact same request the
harness fires and prints the body. Disposable, per the probe_*.py convention.
"""

import json
import os
import sys

import requests

from payloads import REFUND, refund_variants

MODEL = sys.argv[1] if len(sys.argv) > 1 else "gpt-5.6-terra"
KEY = os.environ["OPENAI-API-KEY"]

injected = refund_variants("control")[0]
messages = [
    {"role": "system", "content": REFUND["system"]},
    {"role": "user", "content": REFUND["user"]},
    {"role": "assistant", "content": "", "tool_calls": [{
        "id": "call_1", "type": "function",
        "function": {"name": REFUND["tool_name"],
                     "arguments": json.dumps(REFUND["tool_args"])}}]},
    {"role": "tool", "content": injected, "tool_call_id": "call_1"},
]
tools = [REFUND["issue_refund_tool"]]


def fire(label, payload):
    r = requests.post("https://api.openai.com/v1/chat/completions",
                      headers={"Authorization": f"Bearer {KEY}",
                               "Content-Type": "application/json"},
                      json=payload, timeout=120)
    print(f"--- {label}: HTTP {r.status_code}")
    if r.status_code != 200:
        print(json.dumps(r.json(), indent=2)[:900])
    else:
        m = r.json()["choices"][0]["message"]
        print("   content:", (m.get("content") or "")[:120])
        print("   tool_calls:", json.dumps(m.get("tool_calls"))[:200])
    print()
    return r.status_code


# 1. exactly what the harness sends
fire("as-harness (tools + assistant tool_call + tool msg)",
     {"model": MODEL, "messages": messages, "tools": tools})

# 2. same but no tools -- isolates whether `tools` is the trigger
fire("no tools", {"model": MODEL, "messages": messages})

# 3. tools, but the two-message prefix only -- isolates the synthetic history
fire("tools + plain user turn only",
     {"model": MODEL, "messages": messages[:2], "tools": tools})
