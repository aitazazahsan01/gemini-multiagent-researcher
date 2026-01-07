import os
import re
import time
from typing import Any, List

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.types import interrupt
from pydantic import BaseModel, Field

from state import ResearchState
from tools import web_search

MODEL_NAME = os.getenv("GOOGLE_MODEL", "gemini-3.5-flash")


def get_llm(temperature: float = 0.3) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=temperature)


def invoke_with_retry(runnable, prompt: str, retries: int = 4, default_delay: int = 10) -> Any:
    """Gemini's free tier returns 429 RESOURCE_EXHAUSTED under normal pipeline
    load (this project makes 7+ calls per run). Retry with the delay Google
    suggests in the error body, falling back to `default_delay`."""
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            return runnable.invoke(prompt)
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            if "RESOURCE_EXHAUSTED" not in msg and "429" not in msg:
                raise
            last_error = e
            if attempt < retries - 1:
                match = re.search(r"retryDelay['\"]?:\s*['\"]?(\d+)", msg)
                delay = int(match.group(1)) + 1 if match else default_delay
                time.sleep(delay)
    raise last_error


# ---------------------------------------------------------------------------
# 1. Planner
# ---------------------------------------------------------------------------

class PlanOutput(BaseModel):
    sub_questions: List[str] = Field(
        description="3 to 5 focused, non-overlapping sub-questions that together cover the topic"
    )


def planner_node(state: ResearchState) -> dict:
    llm = get_llm(temperature=0.2).with_structured_output(PlanOutput)
    prompt = (
        "You are a research planner. Break the following topic into 3-5 focused, "
        "non-overlapping sub-questions that, if answered well, would let a writer "
        "produce a thorough report.\n\n"
        f"Topic: {state['topic']}"
    )
    result: PlanOutput = invoke_with_retry(llm, prompt)
    return {"plan": result.sub_questions}


# ---------------------------------------------------------------------------
# 2. Human-in-the-loop: review the plan before spending time researching it
# ---------------------------------------------------------------------------

def human_plan_review_node(state: ResearchState) -> dict:
    decision = interrupt(
        {
            "reason": "review_plan",
            "topic": state["topic"],
            "plan": state["plan"],
            "instructions": (
                "Reply 'approve' to continue, or type replacement sub-questions "
                "separated by ';' to override the plan."
            ),
        }
    )
    if isinstance(decision, str) and decision.strip().lower() != "approve":
        new_p