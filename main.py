import asyncio
import json
import time
import os
import uuid
from datetime import datetime, timezone
import dotenv

from src.workflow import create_sds_graph
from src.mcp_client import SDSMCPClient
from src.schema import SDSValidationResult

dotenv.load_dotenv()

async def run_batch():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        print("Note: GROQ_API_KEY not set. Using deterministic rule-based verification agent.")

    print("Initializing MCP Client and connecting to Excel Server...")
    mcp_client = SDSMCPClient()
    await mcp_client.connect()

    try:
        pending_json = await mcp_client.get_pending_requests()
        requests = json.loads(pending_json)

        if not requests:
            print("No pending requests found.")
            return

        print(f"Discovered {len(requests)} pending SDS requests to process.")
        graph = create_sds_graph()

        os.makedirs("logs", exist_ok=True)
        trace_file = "logs/agent_trace.jsonl"

        for req in requests:
            try:
                row_idx = req.get("_row_index")
                sheet_name = req.get("_sheet_name", "")
                excel_row = req.get("_excel_row", 0)
                product_name = req.get('Product Name') or req.get('Product')
                print(f"\nProcessing request for: {product_name} ({sheet_name} row {excel_row})...")

                initial_state = {
                    "messages": [],
                    "row_data": req,
                    "discovered_candidates": [],
                    "ranked_candidates": [],
                    "fetched_urls": [],
                    "successful_fetches": {},
                    "failed_fetches": {},
                    "current_candidate_url": "",
                    "action_history": [],
                    "next_action": None,
                    "iteration_count": 0,
                    "retry_count": 0,
                    "draft_decision": None,
                    "verification_result": None,
                    "final_status": "ERROR",
                    "final_url": "",
                    "confidence": 0,
                    "detailed_reasoning": "",
                    "provenance": None
                }

                config = {"recursion_limit": 20}
                final_state = await graph.ainvoke(initial_state, config)

                status = final_state.get("final_status", "NEEDS REVIEW")
                url = final_state.get("final_url", "")
                confidence = final_state.get("confidence", 0)
                reasoning = final_state.get("detailed_reasoning", "No reasoning provided.")

                try:
                    val = SDSValidationResult(
                        status=status,
                        confidence=confidence,
                        detailed_reasoning=reasoning,
                        final_url=url,
                        provenance=final_state.get("provenance")
                    )
                    status = val.status
                    confidence = val.confidence
                    reasoning = val.detailed_reasoning
                    url = val.final_url
                except Exception:
                    pass

                print(f"Result -> Status: {status}, Confidence: {confidence}%, URL: {url}")

                if row_idx is not None:
                    await mcp_client.update_request_status(
                        row_index=row_idx,
                        final_url=url,
                        status=status,
                        confidence=confidence,
                        reasoning=reasoning,
                        sheet_name=sheet_name,
                        excel_row=excel_row
                    )

                raw_messages = final_state.get("messages", [])
                serialized_messages = [
                    {
                        "type": type(m).__name__,
                        "content": str(getattr(m, "content", "")),
                        "tool_calls": getattr(m, "tool_calls", [])
                    }
                    for m in raw_messages
                ]

                trace_entry = {
                    "id": str(uuid.uuid4()),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "sheet_name": sheet_name,
                    "excel_row": excel_row,
                    "request": req,
                    "final_status": status,
                    "final_url": url,
                    "confidence": confidence,
                    "detailed_reasoning": reasoning,
                    "verification_result": final_state.get("verification_result"),
                    "provenance": final_state.get("provenance"),
                    "messages": serialized_messages
                }

                with open(trace_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(trace_entry) + "\n")

                await asyncio.sleep(0.5)

            except Exception as e:
                print(f"Row error: {e}")
                await asyncio.sleep(1)

    finally:
        await mcp_client.disconnect()
        print("\nBatch complete! Check logs/agent_trace.jsonl for execution traces.")

if __name__ == "__main__":
    asyncio.run(run_batch())
