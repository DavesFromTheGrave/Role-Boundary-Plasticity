"""Isolate which of the two steps (function_call vs function_result) is rejected."""
import json, os, requests

URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
H = {"x-goog-api-key": os.environ["GEMINI_API_KEY"], "Content-Type": "application/json"}
M = "gemini-3.6-flash"
USER = {"type": "user_input", "content": "Weather in Boston?"}
TEXT = "Boston: 68F, partly cloudy."

def go(label, steps):
    r = requests.post(URL, headers=H, json={"model": M, "store": False, "input": steps}, timeout=120)
    print(f"{label:50s} {r.status_code}  {r.text[:170] if r.status_code!=200 else ''}")
    if r.status_code == 200:
        for s in r.json().get("steps") or []:
            if s.get("type") == "model_output":
                print("    OUT:", json.dumps(s.get("content"))[:160])
    return r.status_code == 200

go("1 user + function_call only",
   [USER, {"type": "function_call", "id": "call_1", "name": "get_weather", "arguments": {"city": "Boston"}}])
go("2 function_call without id",
   [USER, {"type": "function_call", "name": "get_weather", "arguments": {"city": "Boston"}}])
go("3 user + function_result only",
   [USER, {"type": "function_result", "name": "get_weather", "call_id": "call_1",
           "result": [{"type": "text", "text": TEXT}]}])
go("4 fc(id=fc_1) + fr(call_id=fc_1)",
   [USER, {"type": "function_call", "id": "fc_1", "name": "get_weather", "arguments": {"city": "Boston"}},
    {"type": "function_result", "name": "get_weather", "call_id": "fc_1",
     "result": [{"type": "text", "text": TEXT}]}])
go("5 with tools declared",
   [USER, {"type": "function_call", "id": "call_1", "name": "get_weather", "arguments": {"city": "Boston"}},
    {"type": "function_result", "name": "get_weather", "call_id": "call_1",
     "result": [{"type": "text", "text": TEXT}]}])
