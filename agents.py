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
        new_plan = [q.strip() for q in decision.split(";") if q.strip()]
        if new_plan:
            return {"plan": new_plan}
    return {}


# ---------------------------------------------------------------------------
# 3. Researcher
# ---------------------------------------------------------------------------

def researcher_node(state: ResearchState) -> dict:
    llm = get_llm(temperature=0.1)
    notes = []
    for question in state["plan"]:
        results = web_search(question, max_results=4)
        sources_text = "\n\n".join(
            f"[{i + 1}] {r['title']}\n{r['url']}\n{r['snippet']}"
            for i, r in enumerate(results)
        )
        summary_prompt = (
            "Summarize the key facts relevant to this question, based only on the "
            "search results below. Cite sources by their [number]. Be concise "
            "(5-8 sentences).\n\n"
            f"Question: {question}\n\nSearch results:\n{sources_text}"
        )
        summary = invoke_with_retry(llm, summary_prompt).text
        notes.append(
            {
                "question": question,
                "summary": summary,
                "sources": [r["url"] for r in results],
            }
        )
    return {"research_notes": notes}


# ---------------------------------------------------------------------------
# 4. Writer
# ---------------------------------------------------------------------------

def writer_node(state: ResearchState) -> dict:
    llm = get_llm(temperature=0.4)
    notes_text = "\n\n".join(
        f"### {n['question']}\n{n['summary']}\nSources: {', '.join(n['sources'])}"
        for n in state["research_notes"]
    )

    feedback_block = ""
    if state.get("critique"):
        feedback_block += (
            f"\n\nThe previous draft was critiqued as follows. Address every point:\n"
            f"{state['critique']}"
        )
    if state.get("human_feedback"):
        feedback_block += f"\n\nA human reviewer also said:\n{state['human_feedback']}"

    prompt = (
        f"Write a well-structured research report on: {state['topic']}\n\n"
        "Use the research notes below as your source material. Include a short "
        "intro, one section per sub-question, and a conclusion. Keep inline "
        "citations as [n] referencing the source list, and include a 'Sources' "
        f"section at the end listing all URLs.{feedback_block}\n\n"
        f"Research notes:\n{notes_text}"
    )
    draft = invoke_with_retry(llm, prompt).text
    return {"draft": draft, "human_feedback": None}


# ---------------------------------------------------------------------------
# 5. Critic (drives the self-correction loop)
# ---------------------------------------------------------------------------

class CritiqueOutput(BaseModel):
    approved: bool = Field(
        description="True only if the draft is accurate, complete, well-cited, and needs no further changes"
    )
    critique: str = Field(
        description="Specific, actionable feedback for the writer. Empty string if approved."
    )


def critic_node(state: ResearchState) -> dict:
    llm = get_llm(temperature=0.0).with_structured_output(CritiqueOutput)
    notes_text = "\n\