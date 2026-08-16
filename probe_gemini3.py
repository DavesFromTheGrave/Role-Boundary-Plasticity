"""Isolate the correct function_result step shape for the Gemini Interactions API.

Bisect established: function_call with `arguments` as an object validates fine;
the 400 comes from the function_result step. This tries the plausible field
spellings one at a time.
"""
import json
import os

import requests

URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
H = {"x-goog-api-key": os.environ["GEMINI_API_KEY"], "Content-Type": "application/json"}
M = "gemini-3.6-flash"

CALL = {"type": "function_call", "id": "call_1", "name": "get_weather",
        "arguments": {"city": "Boston"}}
USER = {"type": "user_input", "content": "Weather in Boston?"}
TEXT = "Boston: 68F, partly cloudy."


def go(label, result_step, extra=None):
    payload = {"model": M, "store": False, "input": [USER, CALL, result_step]}
    if extra:
        payload.update(extra)
    r = requests.post(URL, headers=H, json=payload, timeout=120)
    print(f"{label:52s} {r.status_code}")
    if r.status_code == 200:
        d = r.json()
        for s in d.get("steps") or []:
            if s.get("type") == "model_output":
                print("    OUT:", json.dumps(s.get("content"))[:180])
    else:
        print("   ", r.text[:200])
    return r.status_code == 200


go("A result[] + call_id + name",
   {"type": "function_result", "name": "get_weather", "call_id": "call_1",
    "result": [{"type": "text", "text": TEXT}]})
go("B result[] + id instead of call_id",
   {"type": "function_result", "name": "get_weather", "id": "call_1",
    "result": [{"type": "text", "text": TEXT}]})
go("C output instead of result",
   {"type": "function_result", "name": "get_weather", "call_id": "call_1",
    "output": [{"type": "text", "text": TEXT}]})
go("D response object",
   {"type": "function_result", "name": "get_weather", "call_id": "call_1",
    "response": {"result": TEXT}})
go("E result as object",
   {"type": "function_result", "name": "get_weather", "call_id": "call_1",
    "result": {"text": TEXT}})
go("F no name field",
   {"type": "function_result", "call_id": "call_1",
    "result": [{"type": "text", "text": TEXT}]})
go("G function_response type",
   {"type": "function_response", "name": "get_weather", "call_id": "call_1",
    "response": {"result": TEXT}})
go("H result[] w/ output_text type",
   {"type": "function_result", "name": "get_weather", "call_id": "call_1",
    "result": [{"type": "output_text", "text": TEXT}]})
