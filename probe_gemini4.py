"""Extract the full list of supported step types from the API's own error."""
import os
import requests

URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
H = {"x-goog-api-key": os.environ["GEMINI_API_KEY"], "Content-Type": "application/json"}

payload = {"model": "gemini-3.6-flash", "store": False, "input": [
    {"type": "user_input", "content": "hi"},
    {"type": "__invalid__", "name": "x"},
]}
r = requests.post(URL, headers=H, json=payload, timeout=120)
print(r.status_code)
print(r.text)
