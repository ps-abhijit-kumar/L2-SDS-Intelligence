import os
import sys

# Ensure project root is on sys.path for subprocess invocations
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import json
import openpyxl
import pandas as pd
from typing import Optional, Dict, Any, List, Set
from mcp.server.fastmcp import FastMCP

from src.workbook_utils import (
    COLUMN_SYNONYMS,
    INVALID_PRODUCT_VALUES,
    is_valid_product_value,
    detect_column_mapping,
    classify_sheet,
    inspect_workbook
)

mcp = FastMCP("ExcelMCP")

# Target file configuration
EXCEL_FILE = os.getenv("EXCEL_FILE_PATH", "sample_requests_eval.xlsx")

@mcp.tool()
def get_pending_requests(column_mapping_json: str = "", selected_sheets_json: str = "") -> str:
    """Reads all valid pending SDS request rows from the eligible/selected sheets."""
    target_path = os.getenv("EXCEL_FILE_PATH", EXCEL_FILE)
    if not os.path.exists(target_path):
        return "[]"

    custom_mapping = {}
    if column_mapping_json:
        try:
            custom_mapping = json.loads(column_mapping_json)
        except Exception:
            pass

    selected_sheets: Optional[Set[str]] = None
    if selected_sheets_json:
        try:
            parsed_sheets = json.loads(selected_sheets_json)
            if isinstance(parsed_sheets, list) and len(parsed_sheets) > 0:
                selected_sheets = set(parsed_sheets)
        except Exception:
            pass

    try:
        excel_file = pd.ExcelFile(target_path)
        sheet_names = excel_file.sheet_names
    except Exception:
        sheet_names = ["Sheet1"]

    requests = []
    global_idx = 0

    for sheet_name in sheet_names:
        if selected_sheets is not None and sheet_name not in selected_sheets:
            continue

        try:
            df = pd.read_excel(target_path, sheet_name=sheet_name)
        except Exception:
            continue

        if len(df) == 0:
            continue

        mapping = dict(custom_mapping) if custom_mapping else detect_column_mapping(list(df.columns))
        product_col = mapping.get('product')

        if not product_col or product_col not in df.columns:
            sheet_mapping = detect_column_mapping(list(df.columns))
            product_col = sheet_mapping.get('product')
            if not product_col or product_col not in df.columns:
                continue
            mapping = sheet_mapping

        company_col = mapping.get('company')
        part_num_col = mapping.get('part_number')
        lang_col = mapping.get('language')
        country_col = mapping.get('country')

        # Auto-classify if selected_sheets wasn't explicitly given
        if selected_sheets is None:
            valid_prod_count = sum(1 for _, r in df.iterrows() if is_valid_product_value(r.get(product_col), str(product_col)))
            classification = classify_sheet(sheet_name, list(df.columns), valid_prod_count, len(df))
            if classification not in ['SDS_REQUESTS', 'UNKNOWN']:
                continue

        has_status = 'Status' in df.columns

        for idx, row in df.iterrows():
            raw_prod = row.get(product_col)
            if not is_valid_product_value(raw_prod, str(product_col)):
                continue

            if has_status and pd.notna(row.get('Status')):
                status_str = str(row['Status']).strip().upper()
                if status_str == 'EXACT MATCH':
                    continue

            prod_val = str(raw_prod).strip()
            comp_val = str(row[company_col]).strip() if company_col and company_col in df.columns and pd.notna(row.get(company_col)) else ''
            part_val = str(row[part_num_col]).strip() if part_num_col and part_num_col in df.columns and pd.notna(row.get(part_num_col)) else ''
            lang_val = str(row[lang_col]).strip() if lang_col and lang_col in df.columns and pd.notna(row.get(lang_col)) else 'English'
            country_val = str(row[country_col]).strip() if country_col and country_col in df.columns and pd.notna(row.get(country_col)) else ''

            row_dict = row.to_dict()
            # Standardized fields for the LangGraph agent
            row_dict['Product'] = prod_val
            row_dict['Product Name'] = prod_val
            row_dict['Product Company Name'] = comp_val
            row_dict['Part Number'] = part_val
            row_dict['Language'] = lang_val or 'English'
            row_dict['Country'] = country_val
            row_dict['_sheet_name'] = sheet_name
            row_dict['_excel_row'] = idx + 2  # 1-indexed in Excel (row 1 is header)
            row_dict['_row_index'] = global_idx

            requests.append(row_dict)
            global_idx += 1

    return json.dumps(requests)

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

if __name__ == "__main__":
    mcp.run()
