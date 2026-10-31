"""Try the whole flow against a running server (uses your real Gemini and Groq keys).

    python scripts/smoke_ask.py                      # asks one question
    python scripts/smoke_ask.py "Will I change jobs?" http://localhost:8000
"""
import json
import sys
import uuid

import httpx

question = sys.argv[1] if len(sys.argv) > 1 else "How will my career go?"
base = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8000"

with httpx.Client(base_url=base, timeout=60) as api:
    user_id = api.post("/users", json={"name": "Smoke Test"}).json()["user_id"]
    api.put(f"/users/{user_id}/chart", json={"date": "2000-04-15", "time": "12:00:00", "city": "Nagpur"}).raise_for_status()

    print(f"Question: {question}\n")
    with api.stream("POST", f"/users/{user_id}/ask", json={"question": question, "request_id": str(uuid.uuid4())}) as res:
        if res.status_code != 200:
            print("HTTP", res.status_code, res.read().decode())
            raise SystemExit(1)
        event = None
        for line in res.iter_lines():
            if line.startswith("event: "):
                event = line[7:]
            elif line.startswith("data: "):
                data = json.loads(line[6:])
                if event == "token":
                    print(data["text"], end="", flush=True)
                elif event in ("done", "failed", "reset"):
                    print(f"\n\n[{event}] {json.dumps(data)}")
