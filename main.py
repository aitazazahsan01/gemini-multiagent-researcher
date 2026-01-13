import uuid

from dotenv import load_dotenv

load_dotenv()

from langgraph.types import Command  # noqa: E402  (must load .env before importing agents)
from rich.console import Console  # noqa: E402
from rich.markdown import Markdown  # noqa: E402
from rich.prompt import Prompt  # noqa: E402

from graph import build_graph  # noqa: E402

console = Console()


def handle_interrupt(payload: dict) -> str:
    console.rule(f"[yellow]Human review: {payload['reason']}")
    if payload["reason"] == "review_plan":
        console.print(f"Topic: {payload['topic']}\n")
        console.print("Proposed research plan:")
        for i, q in enumerate(payload["plan"], 1):
            console.print(f"  {i}. {q}")
    elif payload["reason"] == "review_final":
        console.print(Markdown(payload["draft"])