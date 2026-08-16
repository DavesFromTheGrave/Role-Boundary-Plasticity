"""Reproduce the 3 Gemini errors: kb_search / bare_command / tool_result."""
import os, requests
import harness
from payloads import KB_SEARCH, bare_command_variants

key = os.environ["GEMINI_API_KEY"]
for i, bare in enumerate(bare_command_variants()):
    system, steps = harness.build_gemini_steps(KB_SEARCH, bare)
    r = requests.post("https://generativelanguage.googleapis.com/v1beta/interactions",
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        json={"model": "gemini-3.6-flash", "store": False,
              "system_instruction": system, "input": steps}, timeout=120)
    print(f"v{i}: {r.status_code}  {r.text[:220]}")
