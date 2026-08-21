import os
import sys
import json
import asyncio
from typing import Optional, Dict, Any, List
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class SDSMCPClient:
    def __init__(self, excel_file_path: Optional[str] = None):
        server_script = os.path.join(os.path.dirname(__file__), "mcp_server.py")
        env_vars = dict(os.environ)
        if excel_file_path:
            env_vars["EXCEL_FILE_PATH"] = excel_file_path

        self.server_parameters = StdioServerParameters(
            command=sys.executable, 
            args=[server_script],
            env=env_vars
        )
        self._session = None
        self._exit_stack = None

    async def connect(self):
        import contextlib
        self._exit_stack = contextlib.AsyncExitStack()
        read, write = await self._exit_stack.enter_async_context(stdio_client(self.server_parameters))
        self._session = await self._exit_stack.enter_async_context(ClientSession(read, write))
        await self._session.initialize()

    async def disconnect(self):
        if self._exit_stack:
            await self._exit_stack.aclose()
            
    async def get_pending_requests(
        self,
        column_mapping: Optional[Dict[str, str]] = None,
        selected_sheets: Optional[List[str]] = None
    ):
        if not self._session:
            raise RuntimeError("Not connected to MCP server")
        
        args = {}
        if column_mapping:
            args["column_mapping_json"] = json.dumps(column_mapping)
        if selected_sheets:
            args["selected_sheets_json"] = json.dumps(selected_sheets)

        result = await self._session.call_tool("get_pending_requests", arguments=args)
        return result.content[0].text if result.content else "[]"

    async def update_request_status(
        self,
        row_index: int = 0,
        final_url: str = "",
        status: str = "",
        confidence: int = 0,
        reasoning: str = "",
        sheet_name: str = "",
        excel_row: int = 0
    ):
        if not self._session:
            raise RuntimeError("Not connected to MCP server")
        arguments = {
            "row_index": row_index,
            "final_url": final_url,
            "status": status,
            "confidence": confidence,
            "reasoning": reasoning,
            "sheet_name": sheet_name,
            "excel_row": excel_row
        }
        result = await self._session.call_tool("update_request_status", arguments=arguments)
        return result.content[0].text if result.content else ""
