import os
import sys
import json
import asyncio
from typing import Optional, Dict, Any, List, Set
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class SDSMCPClient:
    """
    Model Context Protocol (MCP) client connecting to the FastMCP server over stdio.
    Implements dynamic MCP protocol tool discovery (list_tools) and verified tool execution.
    """
    def __init__(self, excel_file_path: Optional[str] = None):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        server_script = os.path.join(project_root, "src", "mcp_server.py")
        env_vars = dict(os.environ)
        env_vars["PYTHONPATH"] = project_root
        if excel_file_path:
            env_vars["EXCEL_FILE_PATH"] = excel_file_path

        self.server_parameters = StdioServerParameters(
            command=sys.executable,
            args=[server_script],
            env=env_vars
        )
        self._session: Optional[ClientSession] = None
        self._exit_stack = None
        self.discovered_tools: Dict[str, Dict[str, Any]] = {}

    async def connect(self):
        """Initializes stdio connection to MCP server and performs dynamic tool discovery."""
        import contextlib
        self._exit_stack = contextlib.AsyncExitStack()
        read, write = await self._exit_stack.enter_async_context(stdio_client(self.server_parameters))
        self._session = await self._exit_stack.enter_async_context(ClientSession(read, write))
        await self._session.initialize()
        
        # Dynamic MCP Tool Discovery via protocol
        await self.list_tools()

    async def disconnect(self):
        """Gracefully shuts down the MCP client session and transport stack."""
        if self._exit_stack:
            await self._exit_stack.aclose()
        self.discovered_tools = {}
        self._session = None

    async def list_tools(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Dynamically queries the MCP Server for available tool definitions using MCP protocol list_tools.
        Populates self.discovered_tools and returns structured tool metadata.
        """
        if not self._session:
            raise RuntimeError("Not connected to MCP server")

        if self.discovered_tools and not force_refresh:
            return list(self.discovered_tools.values())

        tools_result = await self._session.list_tools()
        tools_list: List[Dict[str, Any]] = []
        self.discovered_tools = {}

        if tools_result and hasattr(tools_result, "tools"):
            for tool in tools_result.tools:
                tool_dict = {
                    "name": tool.name,
                    "description": tool.description or "",
                    "input_schema": getattr(tool, "inputSchema", getattr(tool, "input_schema", {}))
                }
                self.discovered_tools[tool.name] = tool_dict
                tools_list.append(tool_dict)

        return tools_list

    def is_tool_available(self, tool_name: str) -> bool:
        """Checks if a specified tool was discovered on the connected MCP server."""
        return tool_name in self.discovered_tools

    async def call_tool_safe(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """
        Invokes an MCP tool only after verifying its dynamic presence in discovered tools.
        Raises RuntimeError if the tool is not registered on the MCP server.
        """
        if not self._session:
            raise RuntimeError("Not connected to MCP server")

        if not self.is_tool_available(tool_name):
            # Attempt a refresh in case tools were registered dynamically
            await self.list_tools(force_refresh=True)

        if not self.is_tool_available(tool_name):
            raise RuntimeError(
                f"MCP Tool '{tool_name}' not available on MCP server. "
                f"Available tools: {list(self.discovered_tools.keys())}"
            )

        return await self._session.call_tool(tool_name, arguments=arguments or {})

    async def get_pending_requests(
        self,
        column_mapping: Optional[Dict[str, str]] = None,
        selected_sheets: Optional[List[str]] = None
    ) -> str:
        """Reads pending SDS requests from active workbook via verified MCP tool."""
        args: Dict[str, Any] = {}
        if column_mapping:
            args["column_mapping_json"] = json.dumps(column_mapping)
        if selected_sheets:
            args["selected_sheets_json"] = json.dumps(selected_sheets)

        result = await self.call_tool_safe("get_pending_requests", arguments=args)
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
    ) -> str:
        """Updates request status in workbook via verified MCP tool."""
        arguments = {
            "row_index": row_index,
            "final_url": final_url,
            "status": status,
            "confidence": confidence,
            "reasoning": reasoning,
            "sheet_name": sheet_name,
            "excel_row": excel_row
        }
        result = await self.call_tool_safe("update_request_status", arguments=arguments)
        return result.content[0].text if result.content else ""

    async def inspect_sds_document(self, url: str) -> str:
        """
        Invokes the MCP server tool 'inspect_sds_document' to safely fetch and extract structured SDS evidence.
        Enforces tool discovery verification prior to execution.
        """
        result = await self.call_tool_safe("inspect_sds_document", arguments={"url": url})
        return result.content[0].text if result.content else "{}"
