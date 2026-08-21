export type SDSStatus = 'EXACT MATCH' | 'BEST AVAILABLE' | 'NEEDS REVIEW' | 'ERROR' | 'PENDING';

export type SheetClassification = 'SDS_REQUESTS' | 'SUPPORTING_DATA' | 'SUMMARY' | 'UNKNOWN';

export interface SDSSearchRequest {
  product_name: string;
  company_name?: string;
  country?: string;
  language?: string;
}

export interface ToolCall {
  name: string;
  args: Record<string, any>;
  id?: string;
  type?: string;
}

export interface AgentTraceStep {
  type: string;
  content: string;
  tool_calls?: ToolCall[];
}

export interface SDSSearchResponse {
  id: string;
  product_name: string;
  company_name: string;
  country: string;
  language: string;
  status: SDSStatus | string;
  confidence: number;
  final_url: string;
  detailed_reasoning: string;
  timestamp: string;
  trace: AgentTraceStep[];
}

export interface HistoryItem {
  id: string;
  sheet_name?: string;
  excel_row?: number;
  product_name: string;
  company_name: string;
  part_number?: string;
  country?: string;
  language?: string;
  status: SDSStatus | string;
  confidence: number;
  final_url?: string;
  detailed_reasoning?: string;
  timestamp: string;
  messages?: AgentTraceStep[];
}

export interface HistoryListResponse {
  items: HistoryItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface HealthStatus {
  status: string;
  backend: string;
  groq_configured: boolean;
  groq_model: string;
  mcp_server_available: boolean;
  excel_file_available: boolean;
  active_file?: string;
  batch_status?: string;
  timestamp: string;
}

export interface StatsResponse {
  total_searches: number;
  exact_matches: number;
  best_available: number;
  needs_review: number;
  errors: number;
  avg_confidence: number;
  resolution_rate: number;
  recent_searches: HistoryItem[];
}

export interface ColumnMapping {
  product?: string | null;
  company?: string | null;
  part_number?: string | null;
  language?: string | null;
  country?: string | null;
  selected_sheets?: string[];
}

export interface SheetSummary {
  sheet_name: string;
  classification: SheetClassification;
  is_selected: boolean;
  physical_rows: number;
  valid_requests: number;
  pending_requests: number;
  completed_requests: number;
  reason?: string | null;
  columns: string[];
  mapping: ColumnMapping;
}

export interface BatchRow {
  _sheet_name?: string;
  _excel_row?: number;
  _row_index: number;
  'S.No.': number;
  Product: string;
  'Product Name': string;
  'Product Company Name': string;
  'Part Number'?: string;
  Language: string;
  Country: string;
  'Found URL'?: string;
  Status: SDSStatus | string;
  Confidence?: number;
  Reasoning?: string;
  timestamp?: string;
}

export interface BatchPreviewResponse {
  file_name: string;
  file_path: string;
  workbook_sheets_count: number;
  workbook_physical_rows: number;
  sds_sheets_count: number;
  sds_requests_count: number;
  pending_requests_count: number;
  completed_requests_count: number;
  exact_matches_count: number;
  best_available_count: number;
  needs_review_count: number;
  errors_count: number;
  selected_sheets: string[];
  sheets_summary: SheetSummary[];
  column_mapping: ColumnMapping;
  all_columns: string[];
  rows: BatchRow[];
  total_rows?: number;
  pending_rows?: number;
  completed_rows?: number;
  total_sheets?: number;
  eligible_sheets?: number;
}

export interface BatchStatusResponse {
  batch_id: string | null;
  status: 'idle' | 'running' | 'completed' | 'error';
  file_name: string;
  file_path: string;
  total_requests: number;
  completed_requests: number;
  current_index: number;
  current_sheet?: string;
  current_product: string;
  current_company: string;
  current_stage: string;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
  results: BatchRow[];
}
