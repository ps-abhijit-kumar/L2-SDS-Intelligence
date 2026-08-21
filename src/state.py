from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage

class SDSState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    # We can pass row_data as a separate dict to give the agent context easily
    row_data: dict
    # Final outputs will be extracted from the last message or structured output
    final_status: str
    final_url: str
    confidence: int
    detailed_reasoning: str
