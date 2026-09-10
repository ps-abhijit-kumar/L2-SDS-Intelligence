"""
Excel Workbook Inspection & Multi-Sheet Processing
==================================================
Architecture Role:
    Provides automated inspection, semantic column mapping, header offset detection,
    and multi-sheet dataset classification for Excel workbooks ingested by the SDS platform.

Key Capabilities:
    1. Multi-Sheet Classification (classify_sheet):
       Inspects worksheet column structures and valid chemical row counts to classify sheets into:
       - 'SDS_REQUESTS': Authentic chemical request datasets containing product and manufacturer records.
       - 'SUPPORTING_DATA': Operational reference sheets (e.g., team allocations, vendor contacts).
       - 'SUMMARY': Aggregated KPI, pivot, or summary metric tables.
       - 'UNKNOWN': Worksheets with no identifiable chemical or operational schema.
    2. Dynamic Header Offset Discovery (extract_table_from_dataframe):
       Scans the initial rows (up to 8 rows) of each worksheet to identify genuine table header rows,
       enabling seamless handling of spreadsheets with decorative top titles, disclaimers, or empty spacer rows.
    3. Semantic Column Mapping (detect_column_mapping):
       Maps arbitrary user spreadsheet headers to canonical SDS request fields (product, company,
       part_number, language, country, status, found_url, confidence, reasoning) using normalized
       fuzzy and synonym dictionaries.
    4. Row Filtering & Cell Validation (is_valid_product_value, is_valid_manufacturer_value):
       Guards against parsing totals, summary footers, NaN values, or trivial placeholders as chemical requests.
    5. Four-Checkpoint Request Completeness:
       Identifies requests missing mandatory language or destination country specifications and
       flags them with clear diagnostic reasoning as NEEDS REVIEW before search execution.
"""

import os
import re
from typing import Optional, Dict, Any, List, Set, Tuple
import pandas as pd
import openpyxl

COLUMN_SYNONYMS: Dict[str, List[str]] = {
    'product': [
        'product product name', 'product name', 'product_name', 'productname',
        'chemical name', 'chemical_name', 'chemical', 'substance name', 'substance',
        'item name', 'item', 'material name', 'material', 'trade name', 'article name',
        'product description', 'chemical description', 'product'
    ],
    'company': [
        'product company name', 'company name', 'product company', 'company',
        'manufacturer name', 'manufacturer', 'product manufacturer',
        'supplier name', 'supplier', 'vendor name', 'vendor', 'brand owner',
        'brand', 'producer', 'mfg name', 'mfg'
    ],
    'part_number': [
        'part numbers', 'part number', 'part_number', 'part no', 'part_no',
        'product number', 'product no', 'product id', 'product_id',
        'catalog number', 'catalog no', 'cas number', 'cas no', 'cas',
        'material number', 'client product id', 'item code', 'sku', 'product code'
    ],
    'language': [
        'sds language', 'document language', 'doc language', 'target language', 'language', 'lang'
    ],
    'country': [
        'destination country', 'country name', 'country code', 'sds country', 'jurisdiction',
        'market', 'region', 'target country', 'country'
    ],
    'status': [
        'status', 'sds status', 'verification status', 'verdict'
    ],
    'found_url': [
        'found url', 'sds url', 'document url', 'pdf url', 'url', 'link', 'sds link'
    ],
    'confidence': [
        'confidence', 'confidence score', 'score'
    ],
    'reasoning': [
        'reasoning', 'detailed reasoning', 'notes', 'comments', 'remarks'
    ]
}

INVALID_CELL_VALUES: Set[str] = {
    '', 'nan', 'none', 'null', 'n/a', 'na', 'total', 'grand total',
    'subtotal', 'summary', 'unknown', 'undefined', 'nil', '-', '--', 'n.a.', 'n/d'
}

INVALID_PRODUCT_VALUES: Set[str] = INVALID_CELL_VALUES
INVALID_MANUFACTURER_VALUES: Set[str] = INVALID_CELL_VALUES

def is_valid_text_cell(val: Any, col_name: str = '') -> bool:
    """Checks if a cell contains genuine, actionable text content."""
    if val is None or pd.isna(val):
        return False
    s = str(val).strip()
    if len(s) < 2:
        return False
    s_lower = s.lower()
    if s_lower in INVALID_CELL_VALUES:
        return False
    if col_name and s_lower == col_name.strip().lower():
        return False
    if s_lower.startswith(('total', 'grand total', 'summary', 'subtotal', 'unnamed:')):
        return False
    return True

def is_valid_product_value(val: Any, col_name: str = '') -> bool:
    """Checks if a cell represents a genuine chemical/product name."""
    return is_valid_text_cell(val, col_name)

def is_valid_manufacturer_value(val: Any, col_name: str = '') -> bool:
    """Checks if a cell represents a genuine manufacturer/company name."""
    return is_valid_text_cell(val, col_name)

def detect_column_mapping(columns: List[str]) -> Dict[str, Optional[str]]:
    """Semantically maps arbitrary Excel column headers to normalized SDS fields."""
    mapping: Dict[str, Optional[str]] = {}
    normalized_cols = {col: re.sub(r'[^a-z0-9]', ' ', str(col).lower()).strip() for col in columns}

    for field in ['product', 'company', 'part_number', 'language', 'country', 'status', 'found_url', 'confidence', 'reasoning']:
        synonyms = COLUMN_SYNONYMS.get(field, [])
        matched_col = None

        # 1. Exact normalized match
        for syn in synonyms:
            for original_col, norm in normalized_cols.items():
                if norm == syn:
                    matched_col = original_col
                    break
            if matched_col:
                break

        # 2. Semantic substring match
        if not matched_col:
            for syn in synonyms:
                for original_col, norm in normalized_cols.items():
                    if original_col in mapping.values():
                        continue
                    if field == 'product':
                        if any(x in norm for x in ['company', 'manufacturer', 'supplier', 'id', 'number', 'state', 'date', 'comment', 'link', 'url', 'status']):
                            continue
                        if 'product' in norm or 'chemical' in norm or 'substance' in norm or 'item' in norm or 'material' in norm:
                            matched_col = original_col
                            break
                    elif field == 'company':
                        if 'company' in norm or 'manufacturer' in norm or 'supplier' in norm or 'vendor' in norm or 'brand' in norm or 'producer' in norm:
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
                    elif field == 'status':
                        if 'status' in norm or 'verdict' in norm:
                            matched_col = original_col
                            break
                    elif field == 'found_url':
                        if 'url' in norm or 'link' in norm or 'pdf' in norm:
                            matched_col = original_col
                            break
                if matched_col:
                    break

        mapping[field] = matched_col
    return mapping

def extract_table_from_dataframe(df_raw: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Optional[str]], int]:
    """Detects header row offset and extracts clean structured table with semantic column mapping."""
    if len(df_raw) == 0:
        return df_raw, {}, 0

    # 1. Test top row as header
    mapping = detect_column_mapping(list(df_raw.columns))
    if mapping.get('product') and mapping.get('company'):
        return df_raw, mapping, 0

    # 2. Search first 8 rows for table header definitions
    max_scan = min(8, len(df_raw))
    for header_idx in range(max_scan):
        row_vals = [str(v).strip() for v in df_raw.iloc[header_idx].values if pd.notna(v)]
        row_mapping = detect_column_mapping(row_vals)
        if row_mapping.get('product') and row_mapping.get('company'):
            # Promote row_idx as column headers
            header_row = df_raw.iloc[header_idx].values
            new_cols = [str(v).strip() if pd.notna(v) and str(v).strip() != '' else f'Col_{i}' for i, v in enumerate(header_row)]
            new_df = df_raw.iloc[header_idx + 1:].copy().reset_index(drop=True)
            new_df.columns = new_cols
            new_mapping = detect_column_mapping(new_cols)
            return new_df, new_mapping, header_idx + 1

    # Fallback to original
    return df_raw, mapping, 0

def classify_sheet(sheet_name: str, columns: List[str], valid_product_rows_count: int, total_physical_rows: int) -> str:
    """
    Classifies an Excel worksheet into SDS_REQUESTS, SUPPORTING_DATA, SUMMARY, or UNKNOWN
    strictly based on the worksheet's column structure, content, and valid product records.
    Sheet names are NOT used to force request dataset status.
    """
    cols_norm = ' '.join([re.sub(r'[^a-z0-9]', ' ', str(c).lower()) for c in columns])

    # 1. Structural check for Summary / KPI datasets
    has_summary_cols = any(k in cols_norm for k in ['metric', 'total value', 'sum', 'kpi', 'grand total', 'subtotal'])
    if has_summary_cols and valid_product_rows_count == 0:
        return 'SUMMARY'

    # 2. Structural check for genuine SDS chemical request records
    has_product_col = any(k in cols_norm for k in ['product', 'chemical', 'substance', 'item', 'material'])
    has_company_col = any(k in cols_norm for k in ['company', 'manufacturer', 'supplier', 'vendor', 'producer', 'brand'])

    if has_product_col and has_company_col and valid_product_rows_count > 0:
        return 'SDS_REQUESTS'

    # 3. Structural check for Supporting / Operational data (squads, allocations, reference tables)
    if valid_product_rows_count == 0:
        if total_physical_rows > 0:
            norm_name = re.sub(r'[^a-z0-9]', '', sheet_name.lower())
            if any(k in norm_name for k in ['summary', 'pivot', 'total', 'kpi', 'report']):
                return 'SUMMARY'
            return 'SUPPORTING_DATA'
        return 'UNKNOWN'

    return 'SUPPORTING_DATA' if total_physical_rows > 30 else 'UNKNOWN'

def inspect_workbook(
    file_path: str,
    custom_mapping: Optional[Dict[str, Optional[str]]] = None,
    custom_selected_sheets: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Semantically identifies the SDS request dataset in an Excel workbook,
    filters out supporting/summary sheets, and extracts normalized request records
    based strictly on the four required fields: Product Name, Manufacturer, Language, Country.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Excel file not found at: {file_path}")

    try:
        excel_file = pd.ExcelFile(file_path)
        sheet_names = excel_file.sheet_names
    except Exception as e:
        raise ValueError(f"Failed to open Excel workbook: {str(e)}")

    # Pass 1: Analyze structure, map semantic headers, and classify all worksheets
    sheet_data: Dict[str, Dict[str, Any]] = {}
    for sheet_name in sheet_names:
        try:
            df_raw = pd.read_excel(file_path, sheet_name=sheet_name)
        except Exception:
            continue

        sheet_physical_rows = len(df_raw)
        df, sheet_mapping, header_offset = extract_table_from_dataframe(df_raw)

        if custom_mapping:
            for k, v in custom_mapping.items():
                if v and v in df.columns:
                    sheet_mapping[k] = v

        prod_col = sheet_mapping.get('product')
        comp_col = sheet_mapping.get('company')
        lang_col = sheet_mapping.get('language')
        country_col = sheet_mapping.get('country')
        has_lang_col = bool(lang_col and lang_col in df.columns)
        has_country_col = bool(country_col and country_col in df.columns)

        valid_product_rows = 0
        if prod_col and prod_col in df.columns and comp_col and comp_col in df.columns:
            for _, r in df.iterrows():
                raw_prod = r.get(prod_col)
                raw_comp = r.get(comp_col)
                if not is_valid_product_value(raw_prod, str(prod_col)) or not is_valid_manufacturer_value(raw_comp, str(comp_col)):
                    continue
                if str(raw_prod).strip().lower() == str(raw_comp).strip().lower():
                    continue
                if not has_lang_col and not has_country_col:
                    continue
                valid_product_rows += 1

        classification = classify_sheet(sheet_name, list(df.columns), valid_product_rows, sheet_physical_rows)
        sheet_data[sheet_name] = {
            'df': df,
            'mapping': sheet_mapping,
            'header_offset': header_offset,
            'physical_rows': sheet_physical_rows,
            'valid_rows': valid_product_rows,
            'classification': classification
        }

    # Determine candidate SDS request sheets
    candidate_sds_sheets = [
        s for s, info in sheet_data.items()
        if info['classification'] == 'SDS_REQUESTS' and info['valid_rows'] > 0
    ]

    # Determine active SDS request sheets
    if custom_selected_sheets is not None:
        active_sheet_names = set(custom_selected_sheets)
    elif len(candidate_sds_sheets) == 1:
        active_sheet_names = set(candidate_sds_sheets)
    else:
        # When multiple request datasets exist, do not merge them. User selects ONE request set.
        active_sheet_names = set()

    # Pass 2: Extract aligned SDS requests strictly from active SDS request datasets
    workbook_physical_rows = 0
    sheets_analysis = []
    global_mapping: Dict[str, Optional[str]] = {}
    all_columns_set = set()
    normalized_requests = []

    exact_matches = 0
    best_available = 0
    needs_review = 0
    errors = 0
    pending_requests_count = 0
    completed_requests_count = 0

    for sheet_name in sheet_names:
        if sheet_name not in sheet_data:
            continue

        info = sheet_data[sheet_name]
        df = info['df']
        sheet_mapping = info['mapping']
        header_offset = info['header_offset']
        sheet_physical_rows = info['physical_rows']
        classification = info['classification']
        workbook_physical_rows += sheet_physical_rows

        for c in df.columns:
            all_columns_set.add(str(c))

        if not global_mapping and sheet_mapping.get('product') and sheet_mapping.get('company'):
            global_mapping = dict(sheet_mapping)

        prod_col = sheet_mapping.get('product')
        comp_col = sheet_mapping.get('company')
        lang_col = sheet_mapping.get('language')
        country_col = sheet_mapping.get('country')
        part_col = sheet_mapping.get('part_number')
        status_col = sheet_mapping.get('status')
        found_url_col = sheet_mapping.get('found_url')
        confidence_col = sheet_mapping.get('confidence')
        reasoning_col = sheet_mapping.get('reasoning')

        has_status = bool(status_col and status_col in df.columns)
        has_lang_col = bool(lang_col and lang_col in df.columns)
        has_country_col = bool(country_col and country_col in df.columns)

        sheet_valid_requests = 0
        sheet_pending = 0
        sheet_completed = 0
        sheet_is_active = sheet_name in active_sheet_names

        if prod_col and prod_col in df.columns and comp_col and comp_col in df.columns:
            for r_idx, r in df.iterrows():
                raw_prod = r.get(prod_col)
                raw_comp = r.get(comp_col)
                raw_lang = r.get(lang_col) if has_lang_col else None
                raw_country = r.get(country_col) if has_country_col else None

                # Validate genuine chemical product name and manufacturer
                if not is_valid_product_value(raw_prod, str(prod_col)) or not is_valid_manufacturer_value(raw_comp, str(comp_col)):
                    continue

                prod_val = str(raw_prod).strip()
                comp_val = str(raw_comp).strip()
                if prod_val.lower() == comp_val.lower():
                    continue

                # Validate language and country
                has_valid_lang = is_valid_text_cell(raw_lang, str(lang_col) if lang_col else '')
                has_valid_country = is_valid_text_cell(raw_country, str(country_col) if country_col else '')

                if not has_lang_col and not has_country_col:
                    continue

                lang_val = str(raw_lang).strip() if has_valid_lang else ""
                country_val = str(raw_country).strip() if has_valid_country else ""
                part_val = str(r.get(part_col, '')).strip() if part_col and part_col in df.columns and pd.notna(r.get(part_col)) else ""

                status_val = str(r.get(status_col, '')).strip().upper() if has_status and pd.notna(r.get(status_col)) else ""
                found_url_val = str(r.get(found_url_col, '')).strip() if found_url_col and found_url_col in df.columns and pd.notna(r.get(found_url_col)) else ""
                reasoning_val = str(r.get(reasoning_col, '')).strip() if reasoning_col and reasoning_col in df.columns and pd.notna(r.get(reasoning_col)) else ""

                confidence_val = 0
                if confidence_col and confidence_col in df.columns and pd.notna(r.get(confidence_col)):
                    try:
                        confidence_val = int(r.get(confidence_col))
                    except (ValueError, TypeError):
                        confidence_val = 0

                # Determine status based on the 4 required fields
                if not has_valid_lang or not has_valid_country:
                    missing = []
                    if not has_valid_lang:
                        missing.append("Language")
                    if not has_valid_country:
                        missing.append("Country/Jurisdiction")
                    norm_status = "NEEDS REVIEW"
                    confidence_val = 0
                    found_url_val = ""
                    reasoning_val = f"Incomplete SDS search identity: missing required {', '.join(missing)} specification in source workbook."
                    if sheet_is_active:
                        needs_review += 1
                        completed_requests_count += 1
                    sheet_completed += 1
                elif status_val in ['EXACT MATCH', 'BEST AVAILABLE', 'NEEDS REVIEW', 'ERROR']:
                    norm_status = status_val
                    if sheet_is_active:
                        completed_requests_count += 1
                        if norm_status == 'EXACT MATCH':
                            exact_matches += 1
                        elif norm_status == 'BEST AVAILABLE':
                            best_available += 1
                        elif norm_status == 'NEEDS REVIEW':
                            needs_review += 1
                        elif norm_status == 'ERROR':
                            errors += 1
                    sheet_completed += 1
                else:
                    norm_status = "PENDING"
                    if sheet_is_active:
                        pending_requests_count += 1
                        sheet_pending += 1

                sheet_valid_requests += 1
                s_no = len(normalized_requests) + 1
                excel_row_num = r_idx + header_offset + 2

                if sheet_is_active:
                    normalized_row = {
                        '_sheet_name': sheet_name,
                        '_excel_row': excel_row_num,
                        '_row_index': len(normalized_requests),
                        'S.No.': s_no,
                        'Product': prod_val,
                        'Product Name': prod_val,
                        'Product Company Name': comp_val,
                        'Company': comp_val,
                        'Part Number': part_val,
                        'Language': lang_val,
                        'Country': country_val,
                        'Found URL': found_url_val,
                        'Status': norm_status,
                        'Confidence': confidence_val,
                        'Reasoning': reasoning_val,
                        'product_name': prod_val,
                        'manufacturer': comp_val,
                        'language': lang_val,
                        'jurisdiction': country_val,
                        'country': country_val,
                        'part_number': part_val
                    }
                    normalized_requests.append(normalized_row)

        is_selected = sheet_is_active and (sheet_valid_requests > 0)

        sheets_analysis.append({
            'sheet_name': sheet_name,
            'classification': classification,
            'is_selected': is_selected,
            'physical_rows': sheet_physical_rows,
            'valid_requests': sheet_valid_requests,
            'pending_requests': sheet_pending,
            'completed_requests': sheet_completed,
            'columns': list(df.columns),
            'mapping': sheet_mapping
        })

    if not global_mapping and sheet_names and sheet_names[0] in sheet_data:
        global_mapping = dict(sheet_data[sheet_names[0]]['mapping'])

    total_requests_count = len(normalized_requests)
    selected_sheet_names = [s['sheet_name'] for s in sheets_analysis if s['is_selected']]

    return {
        'file_name': os.path.basename(file_path),
        'file_path': file_path,
        'workbook_sheets_count': len(sheet_names),
        'workbook_physical_rows': workbook_physical_rows,
        'sds_sheets_count': len(selected_sheet_names),
        'sds_requests_count': total_requests_count,
        'pending_requests_count': pending_requests_count,
        'completed_requests_count': completed_requests_count,
        'exact_matches_count': exact_matches,
        'best_available_count': best_available,
        'needs_review_count': needs_review,
        'errors_count': errors,
        'selected_sheets': selected_sheet_names,
        'sheets_summary': sheets_analysis,
        'column_mapping': global_mapping,
        'all_columns': list(all_columns_set),
        'rows': normalized_requests,
        'total_rows': total_requests_count,
        'pending_rows': pending_requests_count,
        'completed_rows': completed_requests_count,
        'exact_matches': exact_matches,
        'best_available': best_available,
        'needs_review': needs_review,
        'errors': errors,
        'total_sheets': len(sheet_names),
        'eligible_sheets': len(selected_sheet_names),
        'skipped_sheets': len(sheet_names) - len(selected_sheet_names),
        'sheet_names': sheet_names
    }
