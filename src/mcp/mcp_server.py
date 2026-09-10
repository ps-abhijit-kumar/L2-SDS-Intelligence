"""
FastMCP Excel & Document Inspection Server
==========================================
Architecture Role:
    Implements a Model Context Protocol (MCP) server using FastMCP to provide
    isolated, protocol-governed tool access for Excel file operations and safe document inspection.

Subsystem Isolation & Protocol Governance:
    - Runs as an independent subprocess communicating over standard input/output (stdio).
    - Prevents Excel file locking contention, openpyxl memory accumulation, and unhandled
      retrieval crashes from destabilizing the main FastAPI or agent processes.
    - Path depth calculation (depth 3: src/mcp/mcp_server.py -> src/mcp -> src -> project root)
      ensures seamless import resolution regardless of subprocess invocation directory.

Exposed MCP Tools:
    1. get_pending_requests:
       Inspects the active Excel workbook using semantic column mapping and sheet classification,
       returning a JSON serialized array of pending chemical SDS requests.
    2. update_request_status:
       Applies atomic, in-place updates to the target worksheet, recording Found URL,
       Status, Confidence, and Reasoning columns.
    3. inspect_sds_document:
       Safely downloads and extracts structured chemical evidence (GHS sections, CAS numbers,
       product identity) behind the SSRF protection boundary.
"""

import os
import sys

# Ensure project root is on sys.path for subprocess invocations (depth 3: src/mcp/mcp_server.py -> src/mcp -> src -> project root)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import json
import openpyxl
import pandas as pd
from typing import Optional, Dict, Any, List, Set
from mcp.server.fastmcp import FastMCP

from src.excel.workbook_utils import (
    COLUMN_SYNONYMS,
    INVALID_PRODUCT_VALUES,
    is_valid_product_value,
    detect_column_mapping,
    classify_sheet,
    inspect_workbook
)
from src.core.security import safe_fetch_document, SecurityError
from src.retrieval.sds_parser import parse_sds_document

mcp = FastMCP("ExcelMCP")

# Target file configuration
EXCEL_FILE = os.getenv("EXCEL_FILE_PATH", "sample_requests_eval.xlsx")

@mcp.tool()
def get_pending_requests(column_mapping_json: str = "", selected_sheets_json: str = "") -> str:
    """Reads all semantically normalized pending SDS request records from the active workbook."""
    target_path = os.getenv("EXCEL_FILE_PATH", EXCEL_FILE)
    if not os.path.exists(target_path):
        return "[]"

    custom_mapping = None
    if column_mapping_json:
        try:
            custom_mapping = json.loads(column_mapping_json)
        except Exception:
            pass

    custom_selected_sheets = None
    if selected_sheets_json:
        try:
            parsed_sheets = json.loads(selected_sheets_json)
            if isinstance(parsed_sheets, list) and len(parsed_sheets) > 0:
                custom_selected_sheets = parsed_sheets
        except Exception:
            pass

    try:
        preview = inspect_workbook(
            target_path,
            custom_mapping=custom_mapping,
            custom_selected_sheets=custom_selected_sheets
        )
        all_rows = preview.get("rows", [])
        pending = [r for r in all_rows if str(r.get("Status", "")).upper() != "EXACT MATCH"]
        return json.dumps(pending)
    except Exception as e:
        return "[]"

@mcp.tool()
def update_request_status(
    row_index: int = 0,
    final_url: str = "",
    status: str = "",
    confidence: int = 0,
    reasoning: str = "",
    sheet_name: str = "",
    excel_row: int = 0
) -> str:
    """Updates the specified row in the specified Excel sheet with the results."""
    target_path = os.getenv("EXCEL_FILE_PATH", EXCEL_FILE)
    if not os.path.exists(target_path):
        return "Error: File not found."

    wb = openpyxl.load_workbook(target_path)

    if sheet_name and sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
    else:
        ws = wb.active

    headers = {cell.value: idx + 1 for idx, cell in enumerate(ws[1]) if cell.value}

    for col_name in ["Found URL", "Status", "Confidence", "Reasoning"]:
        if col_name not in headers:
            col_num = ws.max_column + 1
            ws.cell(row=1, column=col_num, value=col_name)
            headers[col_name] = col_num

    if excel_row > 0:
        target_row = excel_row
    else:
        target_row = row_index + 2

    ws.cell(row=target_row, column=headers["Found URL"], value=final_url)
    ws.cell(row=target_row, column=headers["Status"], value=status)
    ws.cell(row=target_row, column=headers["Confidence"], value=confidence)
    ws.cell(row=target_row, column=headers["Reasoning"], value=reasoning)

    wb.save(target_path)
    return "Success"

@mcp.tool()
def inspect_sds_document(url: str) -> str:
    """
    Safely retrieves and parses a candidate SDS document (PDF or HTML) behind the MCP boundary.
    Enforces SSRF protection, bounded streaming, content-type verification, and multi-page section extraction.
    Returns structured JSON evidence containing product identity, manufacturer, GHS sections, CAS numbers, and document type.
    """
    if not url or not isinstance(url, str):
        return json.dumps({
            "url": str(url),
            "fetched_successfully": False,
            "error": "Invalid or empty URL"
        })
    try:
        data, content_type, final_url = safe_fetch_document(url, timeout=12.0)
        evidence = parse_sds_document(data, content_type, final_url)
        return json.dumps(evidence.model_dump())
    except SecurityError as sec_err:
        return json.dumps({
            "url": url,
            "fetched_successfully": False,
            "error": f"Security Error (SSRF policy): {str(sec_err)}"
        })
    except Exception as e:
        return json.dumps({
            "url": url,
            "fetched_successfully": False,
            "error": f"Document inspection failed: {str(e)}"
        })

if __name__ == "__main__":
    mcp.run()
