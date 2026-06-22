import requests

while True:
    prompt = input("GEAI> ")

    if prompt.lower() == "exit":
        break

    r = requests.get(
        "http://localhost:8000/ask",
        params={"prompt": prompt}
    )

    print(r.json())