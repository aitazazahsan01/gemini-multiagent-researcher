from typing import Annotated, List, TypedDict
import operator

class ResearchState(TypedDict):
    topic: str
    plan: List[str]
    research_notes: Annotated[List[dict], operator.add]
    draft: str
    critique: str
    approved: bool
    revision_count: int
