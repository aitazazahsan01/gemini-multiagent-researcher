from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from agents import (
    critic_node,
    human_final_review_node,
    human_plan_review_node,
    planner_node,
    researcher_node,
    writer_node,
)
from state import ResearchState

MAX_REVISIONS = 3


def route_after_critic(state: ResearchState) -> str:
    if state["approved"] or state["revision_count"] >= MAX_REVISIONS:
        return "human_final_review"
    return "writer"


def route_after_human_final(state: ResearchState) -> str:
    return END if state["approved"] else "writer"


def build_graph():
    graph = StateGraph(ResearchState)

    graph.add_node("planner", planner_node)
    graph.add_node("human_plan_review", human_plan_review_node)
    graph.add_node("researcher", 