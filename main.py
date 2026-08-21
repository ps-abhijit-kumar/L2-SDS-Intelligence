import asyncio
import json
import time
import os
import dotenv
from src.workflow import create_sds_graph
from src.mcp_client import SDSMCPClient

dotenv.load_dotenv()

async def run_batch():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        print("ERROR: GROQ_API_KEY is not set or contains the default placeholder.")
        print("Please set your GROQ_API_KEY in .env before running the agent pipeline.")
        return

    print("Initializing MCP Client and connecting to Excel Server...")
    mcp_client = SDSMCPClient()
    await mcp_client.connect()
    
    try:
        # Get pending requests via MCP (bypasses direct Excel I/O)
        pending_json = await mcp_client.get_pending_requests()
        requests = json.loads(pending_json)
        
        if not requests:
            print("No pending requests found.")
            return

        graph = create_sds_graph()
        
        # Setup trace log directory
        os.makedirs("logs", exist_ok=True)
        trace_file = "logs/agent_trace.jsonl"
        
        for req in requests:
            try:
                row_idx = req.get("_row_index")
                product_name = req.get('Product Name') or req.get('Product')
                print(f"\nProcessing request for: {product_name}...")
                
                initial_state = {
                    "messages": [],
                    "row_data": req,
                    "final_status": "ERROR",
                    "final_url": "",
                    "confidence": 0,
                    "detailed_reasoning": ""
                }
                
                # Invoke LangGraph Agent with strict recursion limit
                config = {"recursion_limit": 15}
                final_state = await graph.ainvoke(initial_state, config)
                
                # Extract results
                status = final_state.get("final_status", "ERROR")
                url = final_state.get("final_url", "")
                confidence = final_state.get("confidence", 0)
                reasoning = final_state.get("detailed_reasoning", "No reasoning provided.")
                
                print(f"Result -> Status: {status}, URL: {url}")
                
                # Update Excel via MCP
                if row_idx is not None:
                    await mcp_client.update_request_status(
                        row_index=row_idx,
                        final_url=url,
                        status=status,
                        confidence=confidence,
                        reasoning=reasoning
                    )
                    
                # Save Trace Log for Reproducibility
                trace_entry = {
                    "request": req,
                    "final_status": status,
                    "final_url": url,
                    "messages": [{"type": type(m).__name__, "content": str(m.content), "tool_calls": getattr(m, "tool_calls", [])} for m in final_state.get("messages", [])]
                }
                with open(trace_file, "a") as f:
                    f.write(json.dumps(trace_entry) + "\n")
                    
                # Respect rate limits for DuckDuckGo and Groq
                await asyncio.sleep(5)
                
            except Exception as e:
                print(f"Row error: {e}")
                # We can sleep a bit longer if we hit a rate limit
                if "rate_limit_exceeded" in str(e):
                    print("Rate limit hit, cooling down for 10 seconds...")
                    await asyncio.sleep(10)
                else:
                    await asyncio.sleep(2)
                    
    finally:
        await mcp_client.disconnect()
        print("\nBatch complete! Check logs/agent_trace.jsonl for reproducible execution traces.")

if __name__ == "__main__":
    asyncio.run(run_batch())
