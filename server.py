import json
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Query  # noqa: E402
from fastapi.responses import StreamingResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from graph import build_graph  # noqa: E402
from langgraph.types import Command  # noqa: E402

app = FastAPI(title="Wire Desk")
graph = build_graph()


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def run_stream(graph_input, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    yield sse("session", {"thread_id": thread_id})
    try:
        for chunk in graph.stream(graph_input, config=config, stream_mode="updates"):
            if "__interrupt__" in chunk:
                payload = chunk["__interrupt__"][0].value
                yield sse("interrupt", payload)
                return
            for node_name, partial_state in chunk.items():
    