import os
import re
from typing import Optional, Dict, Any, List, Set
import pandas as pd
import openpyxl

COLUMN_SYNONYMS: Dict[str, List[str]] = {
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

INVALID_PRODUCT_VALUES: Set[str] = {
    '', 'nan', 'none', 'null', 'n/a', 'na', 'total', 'grand total',
    'subtotal', 'summary', 'unknown', 'undefined', 'nil', '-'
}

def is_valid_product_value(val: Any, col_name: str = '') -> bool:
    """Checks if a cell value represents a genuine chemical/product name."""
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
    """Deterministically identifies the best matching column for standard SDS fields."""
    mapping: Dict[str, Optional[str]] = {}
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
    """Classifies an Excel worksheet into SDS_REQUESTS, SUPPORTING_DATA, SUMMARY, or UNKNOWN."""
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

def inspect_workbook(
    file_path: str,
    custom_mapping: Optional[Dict[str, Optional[str]]] = None,
    custom_selected_sheets: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Parses workbook structure, auto-detects sheets, column mappings, and extracts valid requests."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Excel file not found at: {file_path}")

    try:
        excel_file = pd.ExcelFile(file_path)
        sheet_names = excel_file.sheet_names
    except Exception as e:
        raise ValueError(f"Failed to open Excel workbook: {str(e)}")

    workbook_physical_rows = 0
    sheets_summary = []
    global_mapping: Dict[str, Optional[str]] = {}
    all_columns_set = set()

    # Pass 1: Analyze each sheet independently
    for sheet_name in sheet_names:
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        except Exception:
            continue

        sheet_physical_rows = len(df)
        workbook_physical_rows += sheet_physical_rows
        sheet_cols = list(df.columns)
        for c in sheet_cols:
            all_columns_set.add(str(c))

        if sheet_physical_rows == 0:
            sheets_summary.append({
                'sheet_name': sheet_name,
                'classification': 'SUMMARY',
                'is_selected': False,
                'physical_rows': 0,
                'valid_requests': 0,
                'pending_requests': 0,
                'completed_requests': 0,
                'reason': 'Sheet is empty',
                'columns': sheet_cols,
                'mapping': {}
            })
            continue

        sheet_mapping = detect_column_mapping(sheet_cols)
        if custom_mapping:
            for k, v in custom_mapping.items():
                if v and v in sheet_cols:
                    sheet_mapping[k] = v

        if not global_mapping:
            global_mapping = dict(sheet_mapping)
        else:
            for k, v in sheet_mapping.items():
                if not global_mapping.get(k) and v:
                    global_mapping[k] = v

        prod_col = sheet_mapping.get('product')
        has_status = 'Status' in df.columns

        valid_requests = 0
        sheet_pending = 0
        sheet_completed = 0

        if prod_col and prod_col in df.columns:
            for _, r in df.iterrows():
                raw_prod = r.get(prod_col)
                if is_valid_product_value(raw_prod, str(prod_col)):
                    valid_requests += 1
                    status_val = str(r.get('Status', '')).strip().upper() if has_status and pd.notna(r.get('Status')) else ''
                    if not status_val or status_val == 'PENDING':
                        sheet_pending += 1
                    elif status_val in ['EXACT MATCH', 'BEST AVAILABLE', 'NEEDS REVIEW', 'ERROR']:
                        sheet_completed += 1
                    else:
                        sheet_pending += 1

        classification = classify_sheet(sheet_name, sheet_cols, valid_requests, sheet_physical_rows)

        if custom_selected_sheets is not None:
            is_selected = sheet_name in custom_selected_sheets
        else:
            is_selected = (classification == 'SDS_REQUESTS' and valid_requests > 0) or (classification == 'UNKNOWN' and valid_requests > 0)

        sheets_summary.append({
            'sheet_name': sheet_name,
            'classification': classification,
            'is_selected': is_selected,
            'physical_rows': sheet_physical_rows,
            'valid_requests': valid_requests,
            'pending_requests': sheet_pending,
            'completed_requests': sheet_completed,
            'reason': None if valid_requests > 0 else 'No valid chemical product rows detected',
            'columns': sheet_cols,
            'mapping': sheet_mapping
        })

    # Pass 2: Extract rows ONLY from selected sheets
    selected_sheet_names = [s['sheet_name'] for s in sheets_summary if s['is_selected']]
    sds_sheets_count = len(selected_sheet_names)

    valid_sds_rows = []
    exact_matches = 0
    best_available = 0
    needs_review = 0
    errors = 0
    pending_requests_count = 0
    completed_requests_count = 0

    for sheet_name in selected_sheet_names:
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        except Exception:
            continue

        sheet_info = next((s for s in sheets_summary if s['sheet_name'] == sheet_name), None)
        mapping = sheet_info['mapping'] if sheet_info else global_mapping
        prod_col = mapping.get('product')
        comp_col = mapping.get('company')
        part_col = mapping.get('part_number')
        lang_col = mapping.get('language')
        country_col = mapping.get('country')

        has_status = 'Status' in df.columns

        for r_idx, r in df.iterrows():
            raw_prod = r.get(prod_col) if prod_col else None
            if not is_valid_product_value(raw_prod, str(prod_col) if prod_col else ''):
                continue

            status_val = str(r.get('Status', '')).strip().upper() if has_status and pd.notna(r.get('Status')) else ''
            if not status_val or status_val == 'PENDING':
                norm_status = 'PENDING'
                pending_requests_count += 1
            else:
                norm_status = status_val
                completed_requests_count += 1
                if norm_status == 'EXACT MATCH':
                    exact_matches += 1
                elif norm_status == 'BEST AVAILABLE':
                    best_available += 1
                elif norm_status == 'NEEDS REVIEW':
                    needs_review += 1
                elif norm_status == 'ERROR':
                    errors += 1
                else:
                    norm_status = 'PENDING'
                    pending_requests_count += 1
                    completed_requests_count -= 1

            confidence_val = 0
            if 'Confidence' in df.columns and pd.notna(r.get('Confidence')):
                try:
                    confidence_val = int(r.get('Confidence'))
                except (ValueError, TypeError):
                    confidence_val = 0

            s_no = r.get('S.No.') or r.get('SNo') or r.get('ID') or (r_idx + 1)
            try:
                s_no_int = int(s_no)
            except (ValueError, TypeError):
                s_no_int = r_idx + 1

            prod_val = str(raw_prod).strip()
            comp_val = str(r.get(comp_col, '')).strip() if comp_col and comp_col in df.columns and pd.notna(r.get(comp_col)) else ''
            part_val = str(r.get(part_col, '')).strip() if part_col and part_col in df.columns and pd.notna(r.get(part_col)) else ''
            lang_val = str(r.get(lang_col, 'English')).strip() if lang_col and lang_col in df.columns and pd.notna(r.get(lang_col)) else 'English'
            country_val = str(r.get(country_col, '')).strip() if country_col and country_col in df.columns and pd.notna(r.get(country_col)) else ''

            found_url_val = str(r.get('Found URL', '')).strip() if 'Found URL' in df.columns and pd.notna(r.get('Found URL')) else ''
            reasoning_val = str(r.get('Reasoning', '')).strip() if 'Reasoning' in df.columns and pd.notna(r.get('Reasoning')) else ''

            row_dict = {
                '_sheet_name': sheet_name,
                '_excel_row': r_idx + 2,
                '_row_index': len(valid_sds_rows),
                'S.No.': s_no_int,
                'Product': prod_val,
                'Product Name': prod_val,
                'Product Company Name': comp_val,
                'Part Number': part_val,
                'Language': lang_val or 'English',
                'Country': country_val,
                'Found URL': found_url_val,
                'Status': norm_status,
                'Confidence': confidence_val,
                'Reasoning': reasoning_val
            }
            valid_sds_rows.append(row_dict)

    sds_requests_count = len(valid_sds_rows)

    all_columns = []
    for s in sheets_summary:
        for c in s['columns']:
            if c not in all_columns:
                all_columns.append(c)

    return {
        'file_name': os.path.basename(file_path),
        'file_path': file_path,
        'workbook_sheets_count': len(sheet_names),
        'workbook_physical_rows': workbook_physical_rows,
        'sds_sheets_count': sds_sheets_count,
        'sds_requests_count': sds_requests_count,
        'pending_requests_count': pending_requests_count,
        'completed_requests_count': completed_requests_count,
        'exact_matches_count': exact_matches,
        'best_available_count': best_available,
        'needs_review_count': needs_review,
        'errors_count': errors,
        'selected_sheets': selected_sheet_names,
        'sheets_summary': sheets_summary,
        'column_mapping': global_mapping,
        'all_columns': all_columns,
        'rows': valid_sds_rows,
        'total_rows': sds_requests_count,
        'pending_rows': pending_requests_count,
        'completed_rows': completed_requests_count,
        'exact_matches': exact_matches,
        'best_available': best_available,
        'needs_review': needs_review,
        'errors': errors,
        'total_sheets': len(sheet_names),
        'eligible_sheets': sds_sheets_count,
        'skipped_sheets': len(sheet_names) - sds_sheets_count,
        'sheet_names': sheet_names
    }
