from typing import Annotated, List, Optional, TypedDict
import operator


class ResearchState(TypedDict):
    """Shared state that flows through every node in the graph.

    LangGraph merges each node's return dict into this state. Most keys are
    simply overwritten by whichever node returns them. `research_notes` uses
    the `operator.add` reducer instead, so returning a list from a node
    appends to the existing list rather than replacing it.
    """

    topic: str
    plan: List[str]
    research_notes: Annotated[List[dict], operator.add]
    draft: str
    critique: str
    approved: bool
    revision_count: int
    human_feedback: Optional[str]
