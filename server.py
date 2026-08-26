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
from src.schema import SDSValidationResult
from src.workbook_utils import (
    COLUMN_SYNONYMS,
    INVALID_PRODUCT_VALUES,
    is_valid_product_value,
    detect_column_mapping,
    classify_sheet,
    inspect_workbook
)

app = FastAPI(
    title='L2 SDS Intelligence Platform API',
    description='API layer connecting frontend command center to the LangGraph SDS Retrieval Agent and MCP Excel Server',
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

# ==============================================================================
# Isolated Thread-Safe Batch Job State Manager (Priority 10)
# ==============================================================================

class BatchJobManager:
    """Manages request-scoped, isolated batch execution state with thread-safe locks."""
    def __init__(self):
        self.active_excel_file: Optional[str] = None
        self.active_column_mapping: Dict[str, Optional[str]] = {}
        self.active_selected_sheets: Optional[List[str]] = None
        self._lock = asyncio.Lock()
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.current_job_id: Optional[str] = None
        self._init_default_job()

    def _init_default_job(self):
        job_id = "initial_idle"
        self.jobs[job_id] = {
            'batch_id': None,
            'status': 'idle',
            'file_name': None,
            'file_path': None,
            'total_requests': 0,
            'completed_requests': 0,
            'current_index': 0,
            'current_sheet': '',
            'current_product': '',
            'current_company': '',
            'current_stage': 'No active workbook. Upload an Excel workbook to begin.',
            'started_at': None,
            'completed_at': None,
            'error': None,
            'results': []
        }
        self.current_job_id = job_id
        return self.jobs[job_id]

    def get_current_state(self) -> Dict[str, Any]:
        if self.current_job_id and self.current_job_id in self.jobs:
            return self.jobs[self.current_job_id]
        return self._init_default_job()

    def create_job(self, target_file: str) -> str:
        job_id = str(uuid.uuid4())
        self.jobs[job_id] = {
            'batch_id': job_id,
            'status': 'running',
            'file_name': os.path.basename(target_file),
            'file_path': target_file,
            'total_requests': 0,
            'completed_requests': 0,
            'current_index': 0,
            'current_sheet': '',
            'current_product': '',
            'current_company': '',
            'current_stage': 'Initializing batch job...',
            'started_at': datetime.now(timezone.utc).isoformat(),
            'completed_at': None,
            'error': None,
            'results': []
        }
        self.current_job_id = job_id
        return job_id

job_manager = BatchJobManager()

# ==============================================================================
# Request / Response Schemas
# ==============================================================================

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
    url_type: Optional[str] = "pdf"
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

    url_val = str(item.get('final_url', ''))
    url_type_val = item.get('url_type') or (item.get('provenance', {}).get('url_type') if isinstance(item.get('provenance'), dict) else None)
    if not url_type_val and url_val:
        url_type_val = 'pdf' if url_val.lower().split('?')[0].endswith('.pdf') else 'landing_page'

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
        'final_url': url_val,
        'url_type': url_type_val,
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
    active_file = job_manager.active_excel_file
    excel_available = bool(active_file and os.path.exists(active_file))
    current_state = job_manager.get_current_state()

    return HealthResponse(
        status='healthy',
        backend='operational',
        groq_configured=groq_configured,
        groq_model=groq_model,
        mcp_server_available=mcp_available,
        excel_file_available=excel_available,
        active_file=os.path.basename(active_file) if active_file else 'None',
        batch_status=current_state['status'],
        timestamp=datetime.now(timezone.utc).isoformat()
    )

# ==============================================================================
# Batch Processing Endpoints
# ==============================================================================

@app.get('/api/batch/preview')
async def get_batch_preview(file_path: Optional[str] = None):
    target = file_path or job_manager.active_excel_file
    if not target or not os.path.exists(target):
        return {
            'file_name': None,
            'file_path': None,
            'workbook_sheets_count': 0,
            'workbook_physical_rows': 0,
            'sds_sheets_count': 0,
            'sds_requests_count': 0,
            'pending_requests_count': 0,
            'completed_requests_count': 0,
            'exact_matches_count': 0,
            'best_available_count': 0,
            'needs_review_count': 0,
            'errors_count': 0,
            'selected_sheets': [],
            'sheets_summary': [],
            'column_mapping': {},
            'all_columns': [],
            'rows': [],
            'total_rows': 0,
            'pending_rows': 0,
            'completed_rows': 0,
            'total_sheets': 0,
            'eligible_sheets': 0,
            'skipped_sheets': 0,
            'sheet_names': []
        }
    return inspect_workbook(
        target,
        custom_mapping=job_manager.active_column_mapping,
        custom_selected_sheets=job_manager.active_selected_sheets
    )

@app.post('/api/batch/upload')
async def upload_batch_file(file: UploadFile = File(...)):
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

        job_manager.active_excel_file = target_path
        job_manager.active_column_mapping = preview['column_mapping']
        job_manager.active_selected_sheets = preview['selected_sheets']

        state = job_manager.get_current_state()
        state['file_name'] = filename
        state['file_path'] = target_path
        state['status'] = 'idle'
        state['results'] = []
        state['error'] = None

        return preview
    except HTTPException:
        raise
    except Exception as parse_err:
        if os.path.exists(target_path):
            os.remove(target_path)
        raise HTTPException(status_code=400, detail=f'Failed to parse uploaded Excel file: {str(parse_err)}')

@app.post('/api/batch/confirm-mapping')
async def confirm_column_mapping(mapping: ColumnMappingRequest):
    new_mapping = {
        'product': mapping.product,
        'company': mapping.company,
        'part_number': mapping.part_number,
        'language': mapping.language,
        'country': mapping.country
    }
    job_manager.active_column_mapping = new_mapping
    if mapping.selected_sheets is not None:
        job_manager.active_selected_sheets = mapping.selected_sheets

    return inspect_workbook(
        job_manager.active_excel_file,
        custom_mapping=job_manager.active_column_mapping,
        custom_selected_sheets=job_manager.active_selected_sheets
    )

@app.post('/api/batch/select-default')
async def select_default_batch_file():
    job_manager.active_excel_file = DEFAULT_EXCEL_FILE
    job_manager.active_column_mapping = {}
    job_manager.active_selected_sheets = None
    state = job_manager.get_current_state()
    state['file_name'] = os.path.basename(DEFAULT_EXCEL_FILE)
    state['file_path'] = DEFAULT_EXCEL_FILE
    state['status'] = 'idle'
    state['results'] = []
    state['error'] = None
    return inspect_workbook(DEFAULT_EXCEL_FILE)

async def run_batch_worker(
    target_file: str,
    column_mapping: Optional[Dict[str, Optional[str]]] = None,
    selected_sheets: Optional[List[str]] = None
):
    async with job_manager._lock:
        job_id = job_manager.create_job(target_file)
        job_state = job_manager.jobs[job_id]
        job_state['current_stage'] = 'Connecting to FastMCP Excel Server...'

        mcp_client = SDSMCPClient(excel_file_path=target_file)

        try:
            await mcp_client.connect()
            job_state['current_stage'] = 'Extracting valid SDS requests from selected sheets...'

            clean_mapping = {k: v for k, v in (column_mapping or {}).items() if v}
            pending_json = await mcp_client.get_pending_requests(
                column_mapping=clean_mapping,
                selected_sheets=selected_sheets
            )
            requests = json.loads(pending_json)

            job_state['total_requests'] = len(requests)
            job_state['completed_requests'] = 0

            if not requests:
                job_state['status'] = 'completed'
                job_state['current_stage'] = 'All selected SDS requests already completed.'
                job_state['completed_at'] = datetime.now(timezone.utc).isoformat()
                await mcp_client.disconnect()
                return

            graph = create_sds_graph()

            for i, req in enumerate(requests):
                sheet_name = req.get('_sheet_name', '')
                excel_row = req.get('_excel_row', 0)
                row_idx = req.get('_row_index', i)

                product_name = req.get('Product Name') or req.get('Product') or 'Chemical Item'
                company_name = req.get('Product Company Name') or req.get('Company') or ''

                job_state['current_index'] = i + 1
                job_state['current_sheet'] = sheet_name
                job_state['current_product'] = str(product_name)
                job_state['current_company'] = str(company_name)
                job_state['current_stage'] = f'[{sheet_name} row {excel_row}] Searching SDS candidates for {product_name}...'

                req_id = str(uuid.uuid4())
                req_timestamp = datetime.now(timezone.utc).isoformat()

                initial_state = {
                    'messages': [],
                    'row_data': req,
                    'discovered_candidates': [],
                    'ranked_candidates': [],
                    'fetched_urls': [],
                    'successful_fetches': {},
                    'failed_fetches': {},
                    'current_candidate_url': '',
                    'action_history': [],
                    'next_action': None,
                    'iteration_count': 0,
                    'retry_count': 0,
                    'draft_decision': None,
                    'verification_result': None,
                    'final_status': 'ERROR',
                    'final_url': '',
                    'confidence': 0,
                    'detailed_reasoning': '',
                    'provenance': None,
                    'mcp_client': mcp_client
                }

                try:
                    job_state['current_stage'] = f'[{sheet_name} row {excel_row}] Executing dynamic action cycles for {product_name}...'
                    config = {'recursion_limit': 20}
                    final_state = await graph.ainvoke(initial_state, config)

                    status = final_state.get('final_status', 'NEEDS REVIEW')
                    url = final_state.get('final_url', '')
                    confidence = int(final_state.get('confidence', 0) if final_state.get('confidence') is not None else 0)
                    reasoning = final_state.get('detailed_reasoning', 'No reasoning provided.')

                    try:
                        valid_schema = SDSValidationResult(
                            status=status,
                            confidence=confidence,
                            detailed_reasoning=reasoning,
                            final_url=url,
                            provenance=final_state.get('provenance')
                        )
                        status = valid_schema.status
                        confidence = valid_schema.confidence
                        reasoning = valid_schema.detailed_reasoning
                        url = valid_schema.final_url
                    except Exception:
                        pass

                    raw_messages = final_state.get('messages', [])
                    serialized_messages = []
                    for m in raw_messages:
                        serialized_messages.append({
                            'type': type(m).__name__,
                            'content': str(getattr(m, 'content', '')),
                            'tool_calls': getattr(m, 'tool_calls', [])
                        })

                    job_state['current_stage'] = f'Writing verified verdict to {sheet_name} row {excel_row} via FastMCP...'
                    await mcp_client.update_request_status(
                        row_index=row_idx,
                        final_url=url,
                        status=status,
                        confidence=confidence,
                        reasoning=reasoning,
                        sheet_name=sheet_name,
                        excel_row=excel_row
                    )

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
                        'verification_result': final_state.get('verification_result'),
                        'provenance': final_state.get('provenance'),
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
                    job_state['results'].append(result_row)
                    job_state['completed_requests'] = len(job_state['results'])

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

                    job_state['results'].append({
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
                    job_state['completed_requests'] = len(job_state['results'])

                await asyncio.sleep(0.5)

            job_state['status'] = 'completed'
            job_state['completed_at'] = datetime.now(timezone.utc).isoformat()
            job_state['current_stage'] = 'Batch verification completed successfully.'

        except Exception as batch_err:
            job_state['status'] = 'error'
            job_state['error'] = str(batch_err)
            job_state['current_stage'] = f'Batch process failed: {str(batch_err)}'
            job_state['completed_at'] = datetime.now(timezone.utc).isoformat()
        finally:
            try:
                await mcp_client.disconnect()
            except Exception:
                pass

@app.post('/api/batch/start')
async def start_batch_processing(background_tasks: BackgroundTasks):
    current_state = job_manager.get_current_state()
    if current_state['status'] == 'running':
        raise HTTPException(
            status_code=409,
            detail='A batch operation is already in progress. Please wait for completion.'
        )

    target_file = job_manager.active_excel_file
    if not os.path.exists(target_file):
        raise HTTPException(status_code=404, detail=f'Target Excel file not found: {target_file}')

    background_tasks.add_task(
        run_batch_worker,
        target_file=target_file,
        column_mapping=job_manager.active_column_mapping,
        selected_sheets=job_manager.active_selected_sheets
    )

    return {
        'status': 'started',
        'message': f"Batch processing initiated for '{os.path.basename(target_file)}'.",
        'file_name': os.path.basename(target_file)
    }

@app.get('/api/batch/status')
async def get_batch_status():
    return job_manager.get_current_state()

@app.get('/api/batch/export')
async def export_batch_results():
    target = job_manager.active_excel_file
    if not os.path.exists(target):
        raise HTTPException(status_code=404, detail='No Excel file available for export.')

    return FileResponse(
        path=target,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        filename=os.path.basename(target)
    )

# ==============================================================================
# Single Search Execution Endpoint
# ==============================================================================

@app.post('/api/sds/search', response_model=SDSSearchResponse)
async def search_sds(request: SDSSearchRequest):
    req_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    row_data = {
        'Product': request.product_name,
        'Product Name': request.product_name,
        'Product Company Name': request.company_name or '',
        'Company': request.company_name or '',
        'Country': request.country or '',
        'Language': request.language or 'English'
    }

    initial_state = {
        'messages': [],
        'row_data': row_data,
        'discovered_candidates': [],
        'ranked_candidates': [],
        'fetched_urls': [],
        'successful_fetches': {},
        'failed_fetches': {},
        'current_candidate_url': '',
        'action_history': [],
        'next_action': None,
        'iteration_count': 0,
        'retry_count': 0,
        'draft_decision': None,
        'verification_result': None,
        'final_status': 'ERROR',
        'final_url': '',
        'confidence': 0,
        'detailed_reasoning': '',
        'provenance': None
    }

    try:
        graph = create_sds_graph()
        config = {'recursion_limit': 20}
        final_state = await graph.ainvoke(initial_state, config)

        status = final_state.get('final_status', 'NEEDS REVIEW')
        url = final_state.get('final_url', '')
        confidence = int(final_state.get('confidence', 0) if final_state.get('confidence') is not None else 0)
        reasoning = final_state.get('detailed_reasoning', 'No reasoning provided.')

        try:
            val = SDSValidationResult(
                status=status,
                confidence=confidence,
                detailed_reasoning=reasoning,
                final_url=url,
                provenance=final_state.get('provenance')
            )
            status = val.status
            confidence = val.confidence
            reasoning = val.detailed_reasoning
            url = val.final_url
        except Exception:
            pass

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
            'timestamp': timestamp,
            'sheet_name': 'SingleQuery',
            'excel_row': 1,
            'request': row_data,
            'final_status': status,
            'final_url': url,
            'confidence': confidence,
            'detailed_reasoning': reasoning,
            'verification_result': final_state.get('verification_result'),
            'provenance': final_state.get('provenance'),
            'messages': serialized_messages
        }

        with open(TRACE_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(trace_entry) + '\n')

        return SDSSearchResponse(
            id=req_id,
            product_name=request.product_name,
            company_name=request.company_name or '',
            country=request.country or '',
            language=request.language or 'English',
            status=status,
            confidence=confidence,
            final_url=url,
            url_type=final_state.get('url_type') or ('pdf' if url.lower().split('?')[0].endswith('.pdf') else 'landing_page'),
            detailed_reasoning=reasoning,
            timestamp=timestamp,
            trace=serialized_messages
        )

    except Exception as e:
        error_status = 'ERROR'
        error_confidence = 0
        error_reasoning = f'Pipeline execution encountered an error: {str(e)}'

        return SDSSearchResponse(
            id=req_id,
            product_name=request.product_name,
            company_name=request.company_name or '',
            country=request.country or '',
            language=request.language or 'English',
            status=error_status,
            confidence=error_confidence,
            final_url='',
            detailed_reasoning=error_reasoning,
            timestamp=timestamp,
            trace=[]
        )

# ==============================================================================
# Audit & History Endpoints
# ==============================================================================

@app.get('/api/history')
async def get_history(
    q: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    traces = load_all_traces()
    normalized = [normalize_trace_item(t, i) for i, t in enumerate(traces)]
    normalized.reverse()

    if status and status.upper() != 'ALL':
        normalized = [item for item in normalized if item['status'].upper() == status.upper()]

    if q:
        query_lower = q.lower()
        normalized = [
            item for item in normalized
            if query_lower in item['product_name'].lower()
            or query_lower in item['company_name'].lower()
            or query_lower in item['detailed_reasoning'].lower()
        ]

    total = len(normalized)
    paginated = normalized[offset:offset + limit]

    return {
        'items': paginated,
        'total': total,
        'limit': limit,
        'offset': offset
    }

@app.get('/api/history/{item_id}')
async def get_history_item(item_id: str):
    traces = load_all_traces()
    for idx, trace in enumerate(traces):
        normalized = normalize_trace_item(trace, idx)
        if normalized['id'] == item_id or f'trace_{idx}' == item_id:
            return normalized
    raise HTTPException(status_code=404, detail=f"Trace item '{item_id}' not found.")

@app.get('/api/stats')
async def get_stats():
    traces = load_all_traces()
    normalized = [normalize_trace_item(t, i) for i, t in enumerate(traces)]

    total = len(normalized)
    exact_matches = sum(1 for item in normalized if item['status'] == 'EXACT MATCH')
    best_available = sum(1 for item in normalized if item['status'] == 'BEST AVAILABLE')
    needs_review = sum(1 for item in normalized if item['status'] == 'NEEDS REVIEW')
    errors = sum(1 for item in normalized if item['status'] == 'ERROR')

    confidences = [item['confidence'] for item in normalized if item.get('confidence') is not None]
    avg_confidence = round(sum(confidences) / len(confidences), 1) if confidences else 0

    resolved = exact_matches + best_available
    resolution_rate = round((resolved / total) * 100, 1) if total > 0 else 0.0

    recent = normalized[-5:] if len(normalized) >= 5 else normalized
    recent.reverse()

    return {
        'total_searches': total,
        'exact_matches': exact_matches,
        'best_available': best_available,
        'needs_review': needs_review,
        'errors': errors,
        'avg_confidence': avg_confidence,
        'resolution_rate': resolution_rate,
        'recent_searches': recent
    }

@app.get('/api/review')
async def get_review_queue():
    traces = load_all_traces()
    normalized = [normalize_trace_item(t, i) for i, t in enumerate(traces)]
    needs_review_items = [item for item in normalized if item['status'] == 'NEEDS REVIEW']
    needs_review_items.reverse()

    return {
        'items': needs_review_items,
        'count': len(needs_review_items)
    }

@app.get('/api/trace/latest')
async def get_latest_trace():
    traces = load_all_traces()
    if not traces:
        return {'trace': [], 'message': 'No execution traces logged yet.'}

    latest = traces[-1]
    normalized = normalize_trace_item(latest, len(traces) - 1)
    return normalized

if __name__ == '__main__':
    import uvicorn
    uvicorn.run('server:app', host='0.0.0.0', port=8000, reload=True)
