import json
from fastapi import FastAPI

app = FastAPI(title="Wire Desk")

def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
