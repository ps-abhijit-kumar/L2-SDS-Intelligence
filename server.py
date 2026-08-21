import os
import sys
import re
import json
import uuid
import shutil
import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Set

import dotenv
from fastapi import FastAPI, HTTPException, Query, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import pandas as pd
import openpyxl

dotenv.load_dotenv()

from src.workflow import create_sds_graph
from src.mcp_client import SDSMCPClient

app = FastAPI(
    title='L2 SDS Intelligence Platform API',
    description='Production API layer connecting frontend command center to the LangGraph SDS Retrieval Agent and MCP Excel Server',
    version='2.0.0'
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

TRACE_FILE = os.path.join('logs', 'agent_trace.jsonl')
DEFAULT_EXCEL_FILE = os.getenv('EXCEL_FILE_PATH', 'sample_requests_eval.xlsx')
UPLOAD_DIR = 'uploads'

os.makedirs('logs', exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Active batch configuration
active_excel_file = DEFAULT_EXCEL_FILE
active_column_mapping: Dict[str, Optional[str]] = {}
active_selected_sheets: Optional[List[str]] = None

# Global in-memory batch processing telemetry
batch_state = {
    'batch_id': None,
    'status': 'idle',  # 'idle' | 'running' | 'completed' | 'error'
    'file_name': os.path.basename(DEFAULT_EXCEL_FILE),
    'file_path': DEFAULT_EXCEL_FILE,
    'total_requests': 0,
    'completed_requests': 0,
    'current_index': 0,
    'current_sheet': '',
    'current_product': '',
    'current_company': '',
    'current_stage': 'Idle',
    'started_at': None,
    'completed_at': None,
    'error': None,
    'results': []
}

class SDSSearchRequest(BaseModel):
    product_name: str = Field(..., min_length=1, description='Target chemical product name')
    company_name: Optional[str] = Field('', description='Manufacturer / company name')
    country: Optional[str] = Field('', description='Target jurisdiction / country')
    language: Optional[str] = Field('', description='Target SDS document language')

class ColumnMappingRequest(BaseModel):
    product: Optional[str] = None
    company: Optional[str] = None
    part_number: Optional[str] = None
    language: Optional[str] = None
    country: Optional[str] = None
    selected_sheets: Optional[List[str]] = None

class SDSSearchResponse(BaseModel):
    id: str
    product_name: str
    company_name: str
    country: str
    language: str
    status: str
    confidence: int
    final_url: str
    detailed_reasoning: str
    timestamp: str
    trace: List[Dict[str, Any]] = []

class HealthResponse(BaseModel):
    status: str
    backend: str
    groq_configured: bool
    groq_model: str
    mcp_server_available: bool
    excel_file_available: bool
    active_file: str
    batch_status: str
    timestamp: str

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

def inspect_workbook(
    file_path: str,
    custom_mapping: Optional[Dict[str, Optional[str]]] = None,
    custom_selected_sheets: Optional[List[str]] = None
) -> Dict[str, Any]:
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f'Excel file not found at: {file_path}')

    try:
        excel_file = pd.ExcelFile(file_path)
        sheet_names = excel_file.sheet_names
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Failed to open Excel workbook: {str(e)}')

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
            global_mapping = sheet_mapping
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
        
        # Determine selection: use custom_selected_sheets if provided, else auto-select SDS_REQUESTS
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
        # Backwards-compatible aliases
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

def load_all_traces() -> List[Dict[str, Any]]:
    traces = []
    if os.path.exists(TRACE_FILE):
        with open(TRACE_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    traces.append(json.loads(line))
                except Exception:
                    continue
    return traces

def normalize_trace_item(item: Dict[str, Any], idx: int) -> Dict[str, Any]:
    req = item.get('request', {})
    item_id = item.get('id') or f'trace_{idx}'
    timestamp = item.get('timestamp')
    if not timestamp:
        timestamp = datetime.now(timezone.utc).isoformat()
        
    return {
        'id': str(item_id),
        'sheet_name': item.get('sheet_name') or req.get('_sheet_name') or '',
        'excel_row': item.get('excel_row') or req.get('_excel_row') or 0,
        'product_name': str(req.get('Product Name') or req.get('Product') or 'Unknown Product'),
        'company_name': str(req.get('Product Company Name') or req.get('Company') or ''),
        'part_number': str(req.get('Part Number') or ''),
        'country': str(req.get('Country') or ''),
        'language': str(req.get('Language') or ''),
        'status': str(item.get('final_status', 'ERROR')),
        'confidence': int(item.get('confidence', 0) if item.get('confidence') is not None else 0),
        'final_url': str(item.get('final_url', '')),
        'detailed_reasoning': str(item.get('detailed_reasoning', '')),
        'timestamp': timestamp,
        'messages': item.get('messages', [])
    }

# ==============================================================================
# Health & General Telemetry
# ==============================================================================

@app.get('/api/health', response_model=HealthResponse)
async def get_health():
    groq_key = os.getenv('GROQ_API_KEY', '')
    groq_configured = bool(groq_key and groq_key.strip() != 'your_groq_api_key_here')
    groq_model = os.getenv('GROQ_MODEL', 'openai/gpt-oss-120b')
    mcp_available = os.path.exists(os.path.join('src', 'mcp_server.py'))
    excel_available = os.path.exists(active_excel_file)
    
    return HealthResponse(
        status='healthy',
        backend='operational',
        groq_configured=groq_configured,
        groq_model=groq_model,
        mcp_server_available=mcp_available,
        excel_file_available=excel_available,
        active_file=os.path.basename(active_excel_file),
        batch_status=batch_state['status'],
        timestamp=datetime.now(timezone.utc).isoformat()
    )

# ==============================================================================
# Batch Processing Endpoints (PRIMARY WORKFLOW: Multi-Sheet Excel -> MCP -> LangGraph)
# ==============================================================================

@app.get('/api/batch/preview')
async def get_batch_preview(file_path: Optional[str] = None):
    target = file_path or active_excel_file
    return inspect_workbook(
        target,
        custom_mapping=active_column_mapping,
        custom_selected_sheets=active_selected_sheets
    )

@app.post('/api/batch/upload')
async def upload_batch_file(file: UploadFile = File(...)):
    global active_excel_file, active_column_mapping, active_selected_sheets
    
    filename = file.filename or 'uploaded_workbook.xlsx'
    
    if not filename.lower().endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file format: '{filename}'. Please upload a Microsoft Excel (.xlsx) file."
        )

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_id = str(uuid.uuid4())[:8]
    sanitized_name = f'{file_id}_{os.path.basename(filename)}'
    target_path = os.path.join(UPLOAD_DIR, sanitized_name)

    try:
        contents = await file.read()
        if not contents or len(contents) == 0:
            raise HTTPException(status_code=400, detail="The uploaded Excel file is empty (0 bytes).")
            
        with open(target_path, 'wb') as buffer:
            buffer.write(contents)
    except HTTPException:
        raise
    except Exception as io_err:
        raise HTTPException(status_code=500, detail=f'Failed to save uploaded file: {str(io_err)}')

    try:
        preview = inspect_workbook(target_path)
        
        if preview['workbook_physical_rows'] == 0:
            if os.path.exists(target_path):
                os.remove(target_path)
            raise HTTPException(status_code=400, detail='The uploaded Excel workbook contains no data rows.')

        active_excel_file = target_path
        active_column_mapping = preview['column_mapping']
        active_selected_sheets = preview['selected_sheets']
        
        batch_state['file_name'] = filename
        batch_state['file_path'] = target_path
        batch_state['status'] = 'idle'
        batch_state['results'] = []
        batch_state['error'] = None
        
        return preview
    except HTTPException:
        raise
    except Exception as parse_err:
        if os.path.exists(target_path):
            os.remove(target_path)
        raise HTTPException(status_code=400, detail=f'Failed to parse uploaded Excel file: {str(parse_err)}')

@app.post('/api/batch/confirm-mapping')
async def confirm_column_mapping(mapping: ColumnMappingRequest):
    global active_column_mapping, active_selected_sheets
    
    new_mapping = {
        'product': mapping.product,
        'company': mapping.company,
        'part_number': mapping.part_number,
        'language': mapping.language,
        'country': mapping.country
    }
    active_column_mapping = new_mapping
    if mapping.selected_sheets is not None:
        active_selected_sheets = mapping.selected_sheets

    return inspect_workbook(
        active_excel_file,
        custom_mapping=active_column_mapping,
        custom_selected_sheets=active_selected_sheets
    )

@app.post('/api/batch/select-default')
async def select_default_batch_file():
    global active_excel_file, active_column_mapping, active_selected_sheets
    active_excel_file = DEFAULT_EXCEL_FILE
    active_column_mapping = {}
    active_selected_sheets = None
    batch_state['file_name'] = os.path.basename(DEFAULT_EXCEL_FILE)
    batch_state['file_path'] = DEFAULT_EXCEL_FILE
    batch_state['status'] = 'idle'
    batch_state['results'] = []
    batch_state['error'] = None
    return inspect_workbook(DEFAULT_EXCEL_FILE)

async def run_batch_worker(
    target_file: str,
    column_mapping: Optional[Dict[str, Optional[str]]] = None,
    selected_sheets: Optional[List[str]] = None
):
    global batch_state
    
    batch_id = str(uuid.uuid4())
    batch_state['batch_id'] = batch_id
    batch_state['status'] = 'running'
    batch_state['started_at'] = datetime.now(timezone.utc).isoformat()
    batch_state['completed_at'] = None
    batch_state['error'] = None
    batch_state['results'] = []
    batch_state['current_stage'] = 'Connecting to FastMCP Excel Server...'

    mcp_client = SDSMCPClient(excel_file_path=target_file)
    
    try:
        await mcp_client.connect()
        batch_state['current_stage'] = 'Extracting valid SDS requests from selected sheets...'
        
        clean_mapping = {k: v for k, v in (column_mapping or {}).items() if v}
        pending_json = await mcp_client.get_pending_requests(
            column_mapping=clean_mapping,
            selected_sheets=selected_sheets
        )
        requests = json.loads(pending_json)
        
        # Batch total requests is STRICTLY the count of valid pending requests
        batch_state['total_requests'] = len(requests)
        batch_state['completed_requests'] = 0

        if not requests:
            batch_state['status'] = 'completed'
            batch_state['current_stage'] = 'All selected SDS requests already completed.'
            batch_state['completed_at'] = datetime.now(timezone.utc).isoformat()
            await mcp_client.disconnect()
            return

        graph = create_sds_graph()
        
        for i, req in enumerate(requests):
            sheet_name = req.get('_sheet_name', '')
            excel_row = req.get('_excel_row', 0)
            row_idx = req.get('_row_index', i)
            
            product_name = req.get('Product Name') or req.get('Product') or 'Chemical Item'
            company_name = req.get('Product Company Name') or req.get('Company') or ''
            
            batch_state['current_index'] = i + 1
            batch_state['current_sheet'] = sheet_name
            batch_state['current_product'] = str(product_name)
            batch_state['current_company'] = str(company_name)
            batch_state['current_stage'] = f'[{sheet_name} row {excel_row}] Searching SDS candidates for {product_name}...'

            req_id = str(uuid.uuid4())
            req_timestamp = datetime.now(timezone.utc).isoformat()

            initial_state = {
                'messages': [],
                'row_data': req,
                'final_status': 'ERROR',
                'final_url': '',
                'confidence': 0,
                'detailed_reasoning': ''
            }

            try:
                batch_state['current_stage'] = f'[{sheet_name} row {excel_row}] Executing LangGraph ReAct cycles for {product_name}...'
                config = {'recursion_limit': 15}
                final_state = await graph.ainvoke(initial_state, config)
                
                status = final_state.get('final_status', 'NEEDS REVIEW')
                url = final_state.get('final_url', '')
                confidence = int(final_state.get('confidence', 0) if final_state.get('confidence') is not None else 0)
                reasoning = final_state.get('detailed_reasoning', 'No reasoning provided.')

                raw_messages = final_state.get('messages', [])
                serialized_messages = []
                for m in raw_messages:
                    serialized_messages.append({
                        'type': type(m).__name__,
                        'content': str(getattr(m, 'content', '')),
                        'tool_calls': getattr(m, 'tool_calls', [])
                    })

                # Write verified result to exact original sheet and row in-place
                batch_state['current_stage'] = f'Writing verified verdict to {sheet_name} row {excel_row} via FastMCP...'
                await mcp_client.update_request_status(
                    row_index=row_idx,
                    final_url=url,
                    status=status,
                    confidence=confidence,
                    reasoning=reasoning,
                    sheet_name=sheet_name,
                    excel_row=excel_row
                )

                # Append execution trace to agent_trace.jsonl
                trace_entry = {
                    'id': req_id,
                    'timestamp': req_timestamp,
                    'sheet_name': sheet_name,
                    'excel_row': excel_row,
                    'request': req,
                    'final_status': status,
                    'final_url': url,
                    'confidence': confidence,
                    'detailed_reasoning': reasoning,
                    'messages': serialized_messages
                }
                with open(TRACE_FILE, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(trace_entry) + '\n')

                result_row = {
                    '_sheet_name': sheet_name,
                    '_excel_row': excel_row,
                    '_row_index': row_idx,
                    'S.No.': req.get('S.No.', i + 1),
                    'Product': req.get('Product', ''),
                    'Product Name': req.get('Product Name', ''),
                    'Product Company Name': company_name,
                    'Part Number': req.get('Part Number', ''),
                    'Language': req.get('Language', 'English'),
                    'Country': req.get('Country', ''),
                    'Found URL': url,
                    'Status': status,
                    'Confidence': confidence,
                    'Reasoning': reasoning,
                    'timestamp': req_timestamp
                }
                batch_state['results'].append(result_row)

            except Exception as row_err:
                status = 'ERROR'
                url = ''
                confidence = 0
                reasoning = f'Row execution failed: {str(row_err)}'

                try:
                    await mcp_client.update_request_status(
                        row_index=row_idx,
                        final_url=url,
                        status=status,
                        confidence=confidence,
                        reasoning=reasoning,
                        sheet_name=sheet_name,
                        excel_row=excel_row
                    )
                except Exception:
                    pass

                batch_state['results'].append({
                    '_sheet_name': sheet_name,
                    '_excel_row': excel_row,
                    '_row_index': row_idx,
                    'S.No.': req.get('S.No.', i + 1),
                    'Product': req.get('Product', ''),
                    'Product Name': req.get('Product Name', ''),
                    'Product Company Name': company_name,
                    'Part Number': req.get('Part Number', ''),
                    'Language': req.get('Language', 'English'),
                    'Country': req.get('Country', ''),
                    'Found URL': '',
                    'Status': 'ERROR',
                    'Confidence': 0,
                    'Reasoning': reasoning,
                    'timestamp': req_timestamp
                })

            batch_state['completed_requests'] = i + 1
            # Respect rate limits for DuckDuckGo and Groq
            await asyncio.sleep(2)

        batch_state['status'] = 'completed'
        batch_state['current_stage'] = f'Batch complete. {len(requests)} valid SDS requests resolved.'
        batch_state['completed_at'] = datetime.now(timezone.utc).isoformat()

    except Exception as batch_err:
        batch_state['status'] = 'error'
        batch_state['error'] = str(batch_err)
        batch_state['current_stage'] = f'Batch encountered fatal error: {str(batch_err)}'
    finally:
        try:
            await mcp_client.disconnect()
        except Exception:
            pass

@app.post('/api/batch/start')
async def start_batch_processing(background_tasks: BackgroundTasks):
    global batch_state, active_column_mapping, active_selected_sheets
    
    if batch_state['status'] == 'running':
        return {
            'status': 'already_running',
            'message': 'A batch execution is already actively in progress.',
            'batch_state': batch_state
        }

    groq_key = os.getenv('GROQ_API_KEY', '')
    if not groq_key or groq_key.strip() == 'your_groq_api_key_here':
        raise HTTPException(
            status_code=503,
            detail='GROQ_API_KEY is not configured on the backend. Please add a valid API key in .env.'
        )

    if not os.path.exists(active_excel_file):
        raise HTTPException(
            status_code=404,
            detail=f'Active Excel file {active_excel_file} not found on server.'
        )

    # Launch background worker
    asyncio.create_task(run_batch_worker(
        active_excel_file,
        column_mapping=active_column_mapping,
        selected_sheets=active_selected_sheets
    ))
    
    return {
        'status': 'started',
        'file_name': os.path.basename(active_excel_file),
        'message': 'Batch execution started via LangGraph agent and FastMCP.'
    }

@app.get('/api/batch/status')
async def get_batch_status():
    return batch_state

@app.post('/api/batch/reset')
async def reset_batch_results():
    global batch_state
    if batch_state['status'] == 'running':
        raise HTTPException(status_code=400, detail='Cannot reset while batch processing is actively running.')

    if not os.path.exists(active_excel_file):
        raise HTTPException(status_code=404, detail='Active Excel file not found.')

    try:
        wb = openpyxl.load_workbook(active_excel_file)
        
        # Clear output columns across ALL sheets
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            headers = {cell.value: idx + 1 for idx, cell in enumerate(ws[1]) if cell.value}
            for col_name in ['Found URL', 'Status', 'Confidence', 'Reasoning']:
                if col_name in headers:
                    col_idx = headers[col_name]
                    for r in range(2, ws.max_row + 1):
                        ws.cell(row=r, column=col_idx, value=None)
                        
        wb.save(active_excel_file)
        
        batch_state['status'] = 'idle'
        batch_state['completed_requests'] = 0
        batch_state['current_index'] = 0
        batch_state['current_sheet'] = ''
        batch_state['current_product'] = ''
        batch_state['current_stage'] = 'Reset complete. Ready for evaluation.'
        batch_state['results'] = []
        batch_state['error'] = None
        
        return inspect_workbook(
            active_excel_file,
            custom_mapping=active_column_mapping,
            custom_selected_sheets=active_selected_sheets
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to reset Excel file: {str(e)}')

@app.get('/api/batch/export')
async def export_batch_excel():
    if not os.path.exists(active_excel_file):
        raise HTTPException(status_code=404, detail='Active Excel file not found for export.')

    base_name = os.path.basename(active_excel_file)
    export_name = f'sds_verified_{base_name}'
    
    return FileResponse(
        active_excel_file,
        filename=export_name,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

# ==============================================================================
# Single SDS Search Endpoint (Secondary entry point into LangGraph)
# ==============================================================================

@app.post('/api/sds/search', response_model=SDSSearchResponse)
async def search_sds(req: SDSSearchRequest):
    groq_key = os.getenv('GROQ_API_KEY', '')
    if not groq_key or groq_key.strip() == 'your_groq_api_key_here':
        raise HTTPException(
            status_code=503,
            detail='GROQ_API_KEY is not configured on the backend. Please add a valid API key in .env.'
        )

    req_id = str(uuid.uuid4())
    req_timestamp = datetime.now(timezone.utc).isoformat()

    row_data = {
        'Product Name': req.product_name.strip(),
        'Product Company Name': req.company_name.strip() if req.company_name else '',
        'Country': req.country.strip() if req.country else '',
        'Language': req.language.strip() if req.language else ''
    }

    initial_state = {
        'messages': [],
        'row_data': row_data,
        'final_status': 'ERROR',
        'final_url': '',
        'confidence': 0,
        'detailed_reasoning': ''
    }

    try:
        graph = create_sds_graph()
        config = {'recursion_limit': 15}
        final_state = await graph.ainvoke(initial_state, config)
    except Exception as e:
        error_msg = str(e)
        status = 'ERROR'
        url = ''
        confidence = 0
        reasoning = f'Execution failed: {error_msg}'
        serialized_messages = []
        
        trace_entry = {
            'id': req_id,
            'timestamp': req_timestamp,
            'request': row_data,
            'final_status': status,
            'final_url': url,
            'confidence': confidence,
            'detailed_reasoning': reasoning,
            'messages': serialized_messages
        }
        with open(TRACE_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(trace_entry) + '\n')
            
        return SDSSearchResponse(
            id=req_id,
            product_name=req.product_name,
            company_name=req.company_name or '',
            country=req.country or '',
            language=req.language or '',
            status=status,
            confidence=confidence,
            final_url=url,
            detailed_reasoning=reasoning,
            timestamp=req_timestamp,
            trace=[]
        )

    status = final_state.get('final_status', 'NEEDS REVIEW')
    url = final_state.get('final_url', '')
    confidence = int(final_state.get('confidence', 0) if final_state.get('confidence') is not None else 0)
    reasoning = final_state.get('detailed_reasoning', 'No reasoning provided.')

    raw_messages = final_state.get('messages', [])
    serialized_messages = []
    for m in raw_messages:
        serialized_messages.append({
            'type': type(m).__name__,
            'content': str(getattr(m, 'content', '')),
            'tool_calls': getattr(m, 'tool_calls', [])
        })

    trace_entry = {
        'id': req_id,
        'timestamp': req_timestamp,
        'request': row_data,
        'final_status': status,
        'final_url': url,
        'confidence': confidence,
        'detailed_reasoning': reasoning,
        'messages': serialized_messages
    }
    with open(TRACE_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(trace_entry) + '\n')

    return SDSSearchResponse(
        id=req_id,
        product_name=req.product_name,
        company_name=req.company_name or '',
        country=req.country or '',
        language=req.language or '',
        status=status,
        confidence=confidence,
        final_url=url,
        detailed_reasoning=reasoning,
        timestamp=req_timestamp,
        trace=serialized_messages
    )

# ==============================================================================
# History, Metrics, Review & Trace Endpoints
# ==============================================================================

@app.get('/api/history')
async def get_history(
    status: Optional[str] = Query(None, description='Filter by status'),
    query: Optional[str] = Query(None, description='Search query'),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    raw_traces = load_all_traces()
    records = []
    for idx, item in enumerate(raw_traces):
        rec = normalize_trace_item(item, idx)
        records.append(rec)

    if not records and os.path.exists(active_excel_file):
        try:
            preview = inspect_workbook(
                active_excel_file,
                custom_mapping=active_column_mapping,
                custom_selected_sheets=active_selected_sheets
            )
            for r in preview['rows']:
                if r['Status'] and r['Status'] != 'PENDING':
                    records.append({
                        'id': f"excel_{r.get('_sheet_name', 'sheet')}_{r['_row_index']}",
                        'sheet_name': r.get('_sheet_name', ''),
                        'excel_row': r.get('_excel_row', 0),
                        'product_name': r['Product Name'] or r['Product'],
                        'company_name': r['Product Company Name'],
                        'part_number': r.get('Part Number', ''),
                        'country': r['Country'],
                        'language': r['Language'],
                        'status': r['Status'],
                        'confidence': r['Confidence'],
                        'final_url': r['Found URL'],
                        'detailed_reasoning': r['Reasoning'],
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'messages': []
                    })
        except Exception:
            pass

    records.reverse()

    if status and status.upper() != 'ALL':
        records = [r for r in records if r['status'].upper() == status.upper()]

    if query and query.strip():
        q = query.strip().lower()
        records = [r for r in records if q in r['product_name'].lower() or q in r['company_name'].lower() or q in r['id'].lower() or (r.get('sheet_name') and q in r['sheet_name'].lower())]

    total = len(records)
    paginated = records[offset:offset + limit]

    return {
        'items': paginated,
        'total': total,
        'limit': limit,
        'offset': offset
    }

@app.get('/api/history/{id}')
async def get_history_detail(id: str):
    raw_traces = load_all_traces()
    for idx, item in enumerate(raw_traces):
        rec = normalize_trace_item(item, idx)
        if rec['id'] == id:
            return rec
            
    raise HTTPException(status_code=404, detail='History record not found')

@app.get('/api/stats')
async def get_stats():
    raw_traces = load_all_traces()
    records = [normalize_trace_item(item, idx) for idx, item in enumerate(raw_traces)]
    
    if not records and os.path.exists(active_excel_file):
        try:
            preview = inspect_workbook(
                active_excel_file,
                custom_mapping=active_column_mapping,
                custom_selected_sheets=active_selected_sheets
            )
            for r in preview['rows']:
                if r['Status'] and r['Status'] != 'PENDING':
                    records.append({
                        'id': f"excel_{r.get('_sheet_name', 'sheet')}_{r['_row_index']}",
                        'sheet_name': r.get('_sheet_name', ''),
                        'excel_row': r.get('_excel_row', 0),
                        'product_name': r['Product Name'] or r['Product'],
                        'company_name': r['Product Company Name'],
                        'status': r['Status'],
                        'confidence': r['Confidence'],
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                    })
        except Exception:
            pass

    total = len(records)
    if total == 0:
        return {
            'total_searches': 0,
            'exact_matches': 0,
            'best_available': 0,
            'needs_review': 0,
            'errors': 0,
            'avg_confidence': 0.0,
            'resolution_rate': 0.0,
            'recent_searches': []
        }

    exact_matches = sum(1 for r in records if r['status'] == 'EXACT MATCH')
    best_available = sum(1 for r in records if r['status'] == 'BEST AVAILABLE')
    needs_review = sum(1 for r in records if r['status'] == 'NEEDS REVIEW')
    errors = sum(1 for r in records if r['status'] == 'ERROR')
    
    confidences = [r['confidence'] for r in records if r.get('confidence') is not None and r['confidence'] > 0]
    avg_confidence = round(sum(confidences) / len(confidences), 1) if confidences else 0.0
    resolution_rate = round(((exact_matches + best_available) / total) * 100, 1) if total > 0 else 0.0

    recent_searches = sorted(records, key=lambda x: x.get('timestamp', ''), reverse=True)[:5]

    return {
        'total_searches': total,
        'exact_matches': exact_matches,
        'best_available': best_available,
        'needs_review': needs_review,
        'errors': errors,
        'avg_confidence': avg_confidence,
        'resolution_rate': resolution_rate,
        'recent_searches': recent_searches
    }

@app.get('/api/review')
async def get_review_queue():
    raw_traces = load_all_traces()
    records = [normalize_trace_item(item, idx) for idx, item in enumerate(raw_traces)]
    
    if not records and os.path.exists(active_excel_file):
        try:
            preview = inspect_workbook(
                active_excel_file,
                custom_mapping=active_column_mapping,
                custom_selected_sheets=active_selected_sheets
            )
            for r in preview['rows']:
                if r['Status'] == 'NEEDS REVIEW':
                    records.append({
                        'id': f"excel_{r.get('_sheet_name', 'sheet')}_{r['_row_index']}",
                        'sheet_name': r.get('_sheet_name', ''),
                        'excel_row': r.get('_excel_row', 0),
                        'product_name': r['Product Name'] or r['Product'],
                        'company_name': r['Product Company Name'],
                        'part_number': r.get('Part Number', ''),
                        'country': r['Country'],
                        'language': r['Language'],
                        'status': r['Status'],
                        'confidence': r['Confidence'],
                        'final_url': r['Found URL'],
                        'detailed_reasoning': r['Reasoning'],
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'messages': []
                    })
        except Exception:
            pass

    flagged = [r for r in records if r['status'] == 'NEEDS REVIEW']
    flagged.reverse()
    return {
        'items': flagged,
        'total': len(flagged)
    }

@app.get('/api/trace/latest')
async def get_latest_trace():
    raw_traces = load_all_traces()
    if not raw_traces:
        return {'trace': None}
    
    latest_item = raw_traces[-1]
    normalized = normalize_trace_item(latest_item, len(raw_traces) - 1)
    return {'trace': normalized}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run('server:app', host='127.0.0.1', port=8000, reload=True)