import pytest
import asyncio
from src.mcp_client import SDSMCPClient
import json
import os

@pytest.mark.asyncio
async def test_mcp_client_roundtrip():
    # Setup
    client = SDSMCPClient()
    
    # Check if the server is available
    if not os.path.exists("src/mcp_server.py"):
        pytest.skip("mcp_server.py not found")
        
    try:
        await client.connect()
        
        # Test pending requests
        pending_json = await client.get_pending_requests()
        requests = json.loads(pending_json)
        
        assert isinstance(requests, list)
        
        # Test update (just test the method executes without error on a dummy index or the first if available)
        if len(requests) > 0:
            row_idx = requests[0].get("_row_index")
            if row_idx is not None:
                await client.update_request_status(
                    row_index=row_idx,
                    final_url="https://test.com",
                    status="NEEDS REVIEW",
                    confidence=0,
                    reasoning="Test reasoning"
                )
    finally:
        await client.disconnect()
