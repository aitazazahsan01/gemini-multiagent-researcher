from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from agents import planner_node, human_plan_review_node, researcher_node, writer_node, critic_node, human_final_review_node
from state import ResearchState

def build_graph():
    builder = StateGraph(ResearchState)
    builder.add_node("planner", planner_node)
    builder.add_node("human_plan_review", human_plan_review_node)
    builder.add_node("researcher", researcher_node)
    builder.add_node("writer", writer_node)
    builder.add_node("critic", critic_node)
    builder.add_node("human_final_review", human_final_review_node)
    builder.add_edge(START, "planner")
    builder.add_edge("planner", "human_plan_review")
    builder.add_edge("human_plan_review", "researcher")
    builder.add_edge("researcher", "writer")
    builder.add_edge("writer", "critic")
    memory = MemorySaver()
    return builder.compile(checkpointer=memory)
