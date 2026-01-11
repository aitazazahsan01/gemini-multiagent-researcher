from langgraph.graph import StateGraph
from state import ResearchState

def build_graph():
    builder = StateGraph(ResearchState)
    return builder.compile()
