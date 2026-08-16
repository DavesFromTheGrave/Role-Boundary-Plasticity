"""Bisect the Gemini Interactions request shape: start minimal, add one field at
a time, and print the first thing that 400s."""
import json
import os

import requests

URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
key = os.environ["GEMINI_API_KEY"]
H = {"x-goog-api-key": key, "Content-Type": "application/json"}


def go(label, payload):
    r = requests.post(URL, headers=H, json=payload, timeout=120)
    ok = r.status_code == 200
    print(f"{label:42s} {r.status_code}")
    if ok:
        d = r.json()
        print("    status:", d.get("status"), "| steps:",
              [s.get("type") for s in d.get("steps") or []])
        for s in d.get("steps") or []:
            if s.get("type") == "model_output":
                print("    out:", json.dumps(s.get("content"))[:200])
    else:
        print("   ", r.text[:220])
    return ok


M = "gemini-3.6-flash"
go("1 plain string input", {"model": M, "input": "Say OK."})
go("2 + store:false", {"model": M, "input": "Say OK.", "store": False})
go("3 + system_instruction", {"model": M, "input": "Say OK.", "store": False,
                              "system_instruction": "You are terse."})
go("4 input as list of user_input", {"model": M, "store": False,
                                     "input": [{"type": "user_input", "content": "Say OK."}]})
go("5 function_call+result", {"model": M, "store": False, "input": [
    {"type": "user_input", "content": "Weather in Boston?"},
    {"type": "function_call", "id": "call_1", "name": "get_weather",
     "arguments": {"city": "Boston"}},
    {"type": "function_result", "name": "get_weather", "call_id": "call_1",
     "result": [{"type": "text", "text": "Boston: 68F, partly cloudy."}]},
]})
go("6 fc/result with arguments as JSON string", {"model": M, "store": False, "input": [
    {"type": "user_input", "content": "Weather in Boston?"},
    {"type": "function_call", "id": "call_1", "name": "get_weather",
     "arguments": json.dumps({"city": "Boston"})},
    {"type": "function_result", "name": "get_weather", "call_id": "call_1",
     "result": [{"type": "text", "text": "Boston: 68F, partly cloudy."}]},
]})
go("7 result as plain string", {"model": M, "store": False, "input": [
    {"type": "user_input", "content": "Weather in Boston?"},
    {"type": "function_call", "id": "call_1", "name": "get_weather",
     "arguments": {"city": "Boston"}},
    {"type": "function_result", "name": "get_weather", "call_id": "call_1",
     "result": "Boston: 68F, partly cloudy."},
]})
