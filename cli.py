import os

import requests


BASE_URL = os.getenv("GEAI_URL", "http://127.0.0.1:8000")
API_KEY = os.getenv("GEAI_API_KEY", "").strip()

if not API_KEY:
    raise SystemExit("GEAI_API_KEY is required. Set it before starting the CLI.")


while True:
    prompt = input("GEAI> ")

    if prompt.lower() == "exit":
        break

    try:
        response = requests.get(
            f"{BASE_URL}/ask",
            params={"prompt": prompt},
            headers={"X-GEAI-API-Key": API_KEY},
            timeout=120,
        )
        response.raise_for_status()
        print(response.json())
    except requests.RequestException as exc:
        print(f"Request failed: {exc}")
