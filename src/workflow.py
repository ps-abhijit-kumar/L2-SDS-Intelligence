from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_groq import ChatGroq
import os
import json
import dotenv

from src.state import SDSState
from src.tools import search_duckduckgo, rank_sds_candidates, fetch_document_text
from src.schema import SDSValidationResult

dotenv.load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
groq_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

llm = ChatGroq(
    temperature=0, 
    groq_api_key=groq_api_key, 
    model_name=groq_model
)

# We bind the tools to the LLM, plus the final structured output as a tool
tools = [search_duckduckgo, rank_sds_candidates, fetch_document_text]
llm_with_tools = llm.bind_tools(tools + [SDSValidationResult])

def agent_node(state: SDSState):
    messages = list(state["messages"])
    
    if len(messages) == 0:
        row = state["row_data"]
        sys_msg = SystemMessage(content=(
            "You are an SDS Retrieval Agent. Your goal is to find, rank, and rigorously validate the correct Safety Data Sheet.\n"
            "You MUST follow this exact loop:\n"
            "1. Call `search_duckduckgo` with broad and targeted queries.\n"
            "2. Call `rank_sds_candidates` on the search results to sort them.\n"
            "3. Take the top ranked URL and call `fetch_document_text` to read the actual document.\n"
            "4. REFLECT on the text: Check if the Product Name, Manufacturer, Country, and Language match the request. VERIFY that the text is actually a Safety Data Sheet (SDS) and not just a homepage or 404 error page.\n"
            "5. Finally, call the `SDSValidationResult` tool to submit your final verdict. NEVER call `SDSValidationResult` at the same time as other tools.\n"
            "CRITICAL: DO NOT invent or hallucinate URLs. The final URL MUST be chosen directly from the `search_duckduckgo` results. "
            "If you cannot find a valid exact match, or if the text is just a generic homepage, or if you have tried checking 3 different URLs without success, you MUST give up. "
            "Set the status to 'NEEDS REVIEW', leave the URL empty, and call the final tool immediately. DO NOT output text, just call the final tool."
        ))
        human_msg = HumanMessage(content=(
            f"Please find the SDS for this request:\n"
            f"Product: {row.get('Product Name', '')}\n"
            f"Company: {row.get('Product Company Name', '')}\n"
            f"Country: {row.get('Country', '')}\n"
            f"Language: {row.get('Language', '')}"
        ))
        messages = [sys_msg, human_msg]
        response = llm_with_tools.invoke(messages)
        return {"messages": [sys_msg, human_msg, response]}
        
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

def should_continue(state: SDSState):
    messages = state["messages"]
    last_message = messages[-1]
    
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return "extract_final"
        
    has_final = any(tc.get("name") == "SDSValidationResult" for tc in last_message.tool_calls)
    if has_final:
        return "extract_final"
            
    return "tools"

def extract_final_node(state: SDSState):
    messages = state["messages"]
    last_message = messages[-1]
    
    final_args = {}
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        for tc in last_message.tool_calls:
            if tc.get("name") == "SDSValidationResult":
                final_args = tc.get("args", {})
                break
                
    if not final_args and hasattr(last_message, "content") and last_message.content:
        content = str(last_message.content).strip()
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            parsed = json.loads(content)
            if isinstance(parsed, dict) and "status" in parsed:
                final_args = parsed
        except Exception:
            pass

    final_status = final_args.get("status", "NEEDS REVIEW")
    confidence = final_args.get("confidence", 0)
    detailed_reasoning = final_args.get("detailed_reasoning", str(getattr(last_message, "content", "")) or "No reasoning provided.")
    final_url = final_args.get("final_url", "")
    
    # URL Sanity Check
    if final_status == "EXACT MATCH":
        lower_url = final_url.lower()
        if not final_url or "example.com" in lower_url or "example.org" in lower_url or "wikipedia.org" in lower_url:
            final_status = "NEEDS REVIEW"
            final_url = ""
            detailed_reasoning += " (Downgraded: Rejected placeholder/invalid URL)"
        elif confidence < 50:
            final_status = "NEEDS REVIEW"
            detailed_reasoning += " (Downgraded: Low confidence)"
            
    return {
        "final_status": final_status,
        "confidence": confidence,
        "detailed_reasoning": detailed_reasoning,
        "final_url": final_url
    }

def create_sds_graph():
    workflow = StateGraph(SDSState)
    
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(tools))
    workflow.add_node("extract_final", extract_final_node)
    
    workflow.set_entry_point("agent")
    
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "extract_final": "extract_final",
            END: END
        }
    )
    
    workflow.add_edge("tools", "agent")
    workflow.add_edge("extract_final", END)
    
    return workflow.compile()
