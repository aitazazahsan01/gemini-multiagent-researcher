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
        console.print(Markdown(payload["draft"]))
        console.print(f"\n[dim]Critic verdict: {payload['critic_verdict']}[/dim]")
        if payload["critic_feedback"]:
            console.print(f"[dim]Critic feedback: {payload['critic_feedback']}[/dim]")
    console.print(f"\n[italic]{payload['instructions']}[/italic]")
    return Prompt.ask("Your response")


def run() -> None:
    app = build_graph()
    topic = Prompt.ask("[bold cyan]Research topic")
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    graph_input = {
        "topic": topic,
        "plan": [],
        "research_notes": [],
        "draft": "",
        "critique": "",
        "approved": False,
        "revision_count": 0,
        "human_feedback": None,
    }

    while True:
        result = app.invoke(graph_input, config=config)
        interru