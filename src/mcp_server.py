import os
import re
import json
import openpyxl
import pandas as pd
from typing import Optional, Dict, Any, List, Set
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ExcelMCP")

# Target file configuration
EXCEL_FILE = os.getenv("EXCEL_FILE_PATH", "sample_requests_eval.xlsx")

COLUMN_SYNONYMS = {
    'product': [
        'product product name', 'product name', 'product_name', 'productname',
        'chemical name', 'chemical_name', 'chemical', 'substance name', 'substance',
        'item name', 'item', 'material name', 'material', 'trade name', 'product'
    ],
    'company': [
        'product company name', 'company name', 'product company',
        'manufacturer name', 'manufacturer', 'supplier name', 'supplier',
        'vendor name', 'vendor', 'brand owner', 'brand', 'product manufacturer', 'company'
    ],
    'part_number': [
        'part numbers', 'part number', 'part_number', 'part no', 'part_no',
        'product number', 'product no', 'product id', 'product_id',
        'catalog number', 'catalog no', 'cas number', 'cas no', 'cas',
        'material number', 'client product id', 'item code', 'sku'
    ],
    'language': [
        'sds language', 'document language', 'language', 'lang'
    ],
    'country': [
        'destination country', 'country name', 'jurisdiction', 'market', 'region', 'country'
    ]
}

INVALID_PRODUCT_VALUES = {
    '', 'nan', 'none', 'null', 'n/a', 'na', 'total', 'grand total',
    'subtotal', 'summary', 'unknown', 'undefined', 'nil', '-'
}

def is_valid_product_value(val: Any, col_name: str = '') -> bool:
    if val is None or pd.isna(val):
        return False
    s = str(val).strip()
    if len(s) < 2:
        return False
    s_lower = s.lower()
    if s_lower in INVALID_PRODUCT_VALUES:
        return False
    if col_name and s_lower == col_name.strip().lower():
        return False
    if s_lower.startswith(('total', 'grand total', 'summary', 'subtotal')):
        return False
    return True

def detect_column_mapping(columns: List[str]) -> Dict[str, Optional[str]]:
    mapping = {}
    normalized_cols = {col: re.sub(r'[^a-z0-9]', ' ', str(col).lower()).strip() for col in columns}
    
    for field in ['product', 'company', 'part_number', 'language', 'country']:
        synonyms = COLUMN_SYNONYMS[field]
        matched_col = None
        
        # 1. Exact match on normalized string
        for syn in synonyms:
            for original_col, norm in normalized_cols.items():
                if norm == syn:
                    matched_col = original_col
                    break
            if matched_col:
                break
                
        # 2. Heuristic word-boundary / substring match
        if not matched_col:
            for syn in synonyms:
                for original_col, norm in normalized_cols.items():
                    if original_col in mapping.values():
                        continue
                    if field == 'product':
                        if any(x in norm for x in ['company', 'manufacturer', 'supplier', 'id', 'number', 'state', 'date', 'comment', 'link']):
                            continue
                        if 'product' in norm or 'chemical' in norm or 'substance' in norm or 'item' in norm or 'material' in norm:
                            matched_col = original_col
                            break
                    elif field == 'company':
                        if 'company' in norm or 'manufacturer' in norm or 'supplier' in norm or 'vendor' in norm or 'brand' in norm:
                            if 'id' in norm and any('name' in k for k in normalized_cols.values()):
                                continue
                            matched_col = original_col
                            break
                    elif field == 'part_number':
                        if any(x in norm for x in ['part', 'catalog', 'cas', 'sku']) or (('product' in norm or 'item' in norm) and any(y in norm for y in ['no', 'number', 'id', 'code'])):
                            matched_col = original_col
                            break
                    elif field == 'language':
                        if 'lang' in norm:
                            matched_col = original_col
                            break
                    elif field == 'country':
                        if any(x in norm for x in ['country', 'jurisdiction', 'market', 'region']):
                            matched_col = original_col
                            break
                if matched_col:
                    break
                    
        mapping[field] = matched_col
    return mapping

def classify_sheet(sheet_name: str, columns: List[str], valid_product_rows_count: int, total_physical_rows: int) -> str:
    norm_name = re.sub(r'[^a-z0-9]', '', sheet_name.lower())
    
    # 1. Obvious summary
    if any(k in norm_name for k in ['summary', 'pivot', 'total', 'kpi', 'dashboard', 'overview']):
        return 'SUMMARY'
        
    # 2. Obvious supporting data
    if any(k in norm_name for k in ['allocation', 'lookup', 'xref', 'matrix', 'reference', 'config', 'log', 'mapping']):
        return 'SUPPORTING_DATA'
        
    # 3. If no valid product rows found
    if valid_product_rows_count == 0:
        return 'SUPPORTING_DATA' if total_physical_rows > 50 else 'UNKNOWN'
        
    # 4. Check for SDS Request sheet indicators
    cols_norm = ' '.join([re.sub(r'[^a-z0-9]', ' ', str(c).lower()) for c in columns])
    has_company = any(k in cols_norm for k in ['company', 'manufacturer', 'supplier', 'vendor'])
    has_sds_keywords = any(k in cols_norm for k in ['sds', 'language', 'country', 'jurisdiction', 'part number', 'request'])
    
    if (has_company or has_sds_keywords) and valid_product_rows_count > 0:
        return 'SDS_REQUESTS'
        
    if 'part' in norm_name or norm_name == 'sheet1':
        return 'SDS_REQUESTS'
        
    return 'UNKNOWN'

@mcp.tool()
def get_pending_requests(column_mapping_json: str = "", selected_sheets_json: str = "") -> str:
    """Reads all valid pending SDS request rows from the eligible/selected sheets."""
    if not os.path.exists(EXCEL_FILE):
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
        excel_file = pd.ExcelFile(EXCEL_FILE)
        sheet_names = excel_file.sheet_names
    except Exception:
        sheet_names = ["Sheet1"]

    requests = []
    global_idx = 0

    for sheet_name in sheet_names:
        if selected_sheets is not None and sheet_name not in selected_sheets:
            continue

        try:
            df = pd.read_excel(EXCEL_FILE, sheet_name=sheet_name)
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
    if not os.path.exists(EXCEL_FILE):
        return "Error: File not found."

    wb = openpyxl.load_workbook(EXCEL_FILE)
    
    if sheet_name and sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
    else:
        ws = wb.active
    
    # Identify header columns
    headers = {cell.value: idx + 1 for idx, cell in enumerate(ws[1]) if cell.value}
    
    # Ensure our output columns exist
    for col_name in ["Found URL", "Status", "Confidence", "Reasoning"]:
        if col_name not in headers:
            col_num = ws.max_column + 1
            ws.cell(row=1, column=col_num, value=col_name)
            headers[col_name] = col_num
            
    # Determine target Excel row
    if excel_row > 0:
        target_row = excel_row
    else:
        target_row = row_index + 2
        
    ws.cell(row=target_row, column=headers["Found URL"], value=final_url)
    ws.cell(row=target_row, column=headers["Status"], value=status)
    ws.cell(row=target_row, column=headers["Confidence"], value=confidence)
    ws.cell(row=target_row, column=headers["Reasoning"], value=reasoning)
    
    wb.save(EXCEL_FILE)
    return "Success"

if __name__ == "__main__":
    mcp.run()
