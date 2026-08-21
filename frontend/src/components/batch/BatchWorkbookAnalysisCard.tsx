import React, { useState, useEffect } from 'react';
import { Layers, CheckCircle2, AlertCircle, FileSpreadsheet, ArrowRight, Settings2, Sliders, CheckSquare, Square } from 'lucide-react';
import { Card, CardHeader, CardTitle } from '../common/Card';
import { Button } from '../common/Button';
import { BatchPreviewResponse, ColumnMapping, SheetSummary } from '../../types/sds';

interface BatchWorkbookAnalysisCardProps {
  preview?: BatchPreviewResponse;
  onConfirmMapping: (mapping: ColumnMapping) => void;
  isConfirming?: boolean;
}

export const BatchWorkbookAnalysisCard: React.FC<BatchWorkbookAnalysisCardProps> = ({
  preview,
  onConfirmMapping,
  isConfirming = false,
}) => {
  const [productCol, setProductCol] = useState<string>('');
  const [companyCol, setCompanyCol] = useState<string>('');
  const [partNumCol, setPartNumCol] = useState<string>('');
  const [langCol, setLangCol] = useState<string>('');
  const [countryCol, setCountryCol] = useState<string>('');
  const [selectedSheets, setSelectedSheets] = useState<string[]>([]);

  useEffect(() => {
    if (preview) {
      if (preview.column_mapping) {
        setProductCol(preview.column_mapping.product || '');
        setCompanyCol(preview.column_mapping.company || '');
        setPartNumCol(preview.column_mapping.part_number || '');
        setLangCol(preview.column_mapping.language || '');
        setCountryCol(preview.column_mapping.country || '');
      }
      if (preview.selected_sheets) {
        setSelectedSheets(preview.selected_sheets);
      } else if (preview.sheets_summary) {
        setSelectedSheets(
          preview.sheets_summary.filter((s) => s.is_selected).map((s) => s.sheet_name)
        );
      }
    }
  }, [preview]);

  if (!preview) return null;

  const allColumns = preview.all_columns || [];
  const sheets = preview.sheets_summary || [];
  const totalWorkbookSheets = preview.workbook_sheets_count ?? preview.total_sheets ?? 1;
  const totalPhysicalRows = preview.workbook_physical_rows ?? 0;
  const sdsSheetsCount = selectedSheets.length;
  
  // Calculate valid requests in selected sheets
  const validRequestsCount = sheets
    .filter((s) => selectedSheets.includes(s.sheet_name))
    .reduce((acc, s) => acc + s.valid_requests, 0);

  const toggleSheet = (sheetName: string) => {
    if (selectedSheets.includes(sheetName)) {
      setSelectedSheets(selectedSheets.filter((s) => s !== sheetName));
    } else {
      setSelectedSheets([...selectedSheets, sheetName]);
    }
  };

  const selectOnlySDS = () => {
    const sdsOnly = sheets
      .filter((s) => s.classification === 'SDS_REQUESTS' || s.valid_requests > 0)
      .map((s) => s.sheet_name);
    setSelectedSheets(sdsOnly);
  };

  const selectAll = () => {
    setSelectedSheets(sheets.map((s) => s.sheet_name));
  };

  const handleSave = () => {
    onConfirmMapping({
      product: productCol || null,
      company: companyCol || null,
      part_number: partNumCol || null,
      language: langCol || null,
      country: countryCol || null,
      selected_sheets: selectedSheets,
    });
  };

  const hasProduct = Boolean(productCol);
  const hasSelectedSheets = selectedSheets.length > 0;

  return (
    <Card variant="elevated" className="border-cyan-500/30 shadow-xl shadow-black/50 space-y-6">
      <CardHeader>
        <CardTitle>
          <Sliders className="w-4 h-4 text-cyan-400" />
          <span>Workbook Ingestion & Request Set Verification</span>
        </CardTitle>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-slate-400 bg-[#0B1020] px-2.5 py-0.5 rounded-full border border-white/[0.08]">
            Workbook: {totalWorkbookSheets} Sheets • {totalPhysicalRows.toLocaleString()} Physical Rows
          </span>
          <span className="text-[10px] font-mono font-bold text-cyan-300 bg-cyan-950/80 px-2.5 py-0.5 rounded-full border border-cyan-500/30">
            SDS Requests: {sdsSheetsCount} Sheets • {validRequestsCount} Valid Requests
          </span>
        </div>
      </CardHeader>

      {/* 1. Worksheet Classification & Selection Matrix */}
      <div className="space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
          <div>
            <span className="font-mono text-slate-300 uppercase text-[11px] font-bold tracking-wider">
              1. Select Active SDS Request Worksheets
            </span>
            <p className="text-[10px] text-slate-400">
              Only checked worksheets will contribute to the active SDS discovery batch. Supporting and summary sheets are excluded by default.
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={selectOnlySDS}
              className="text-[10px] font-mono text-cyan-400 hover:text-cyan-300 bg-cyan-950/60 hover:bg-cyan-900/60 px-2.5 py-1 rounded-lg border border-cyan-500/30 cursor-pointer"
            >
              Select Request Sheets Only
            </button>
            <button
              type="button"
              onClick={selectAll}
              className="text-[10px] font-mono text-slate-400 hover:text-slate-200 bg-white/[0.04] hover:bg-white/[0.08] px-2.5 py-1 rounded-lg border border-white/[0.08] cursor-pointer"
            >
              Select All
            </button>
          </div>
        </div>

        {/* Sheets Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
          {sheets.map((s, idx) => {
            const isChecked = selectedSheets.includes(s.sheet_name);
            const isSDS = s.classification === 'SDS_REQUESTS';
            const isSupporting = s.classification === 'SUPPORTING_DATA';
            const isSummary = s.classification === 'SUMMARY';

            let badgeColor = 'bg-slate-800 text-slate-400 border-slate-700';
            let badgeText = 'SUPPORTING';
            if (isSDS) {
              badgeColor = 'bg-emerald-950/80 text-emerald-300 border-emerald-500/30';
              badgeText = 'SDS REQUESTS';
            } else if (isSummary) {
              badgeColor = 'bg-purple-950/80 text-purple-300 border-purple-500/30';
              badgeText = 'SUMMARY';
            } else if (isSupporting) {
              badgeColor = 'bg-slate-900 text-slate-400 border-slate-700/60';
              badgeText = 'SUPPORTING DATA';
            } else {
              badgeColor = 'bg-amber-950/80 text-amber-300 border-amber-500/30';
              badgeText = 'UNKNOWN';
            }

            return (
              <div
                key={idx}
                onClick={() => toggleSheet(s.sheet_name)}
                className={`p-3 rounded-xl border text-xs font-mono transition-all cursor-pointer flex flex-col justify-between gap-2 ${
                  isChecked
                    ? 'bg-[#0B1020] border-cyan-500/40 shadow-sm shadow-cyan-950/40'
                    : 'bg-[#070A12]/60 border-white/[0.06] opacity-60 hover:opacity-100'
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    {isChecked ? (
                      <CheckSquare className="w-4 h-4 text-cyan-400 shrink-0" />
                    ) : (
                      <Square className="w-4 h-4 text-slate-500 shrink-0" />
                    )}
                    <span className="font-bold text-slate-200 truncate">{s.sheet_name}</span>
                  </div>

                  <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded border shrink-0 ${badgeColor}`}>
                    {badgeText}
                  </span>
                </div>

                <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1 border-t border-white/[0.04]">
                  <span>{s.physical_rows.toLocaleString()} physical rows</span>
                  <span className={`font-bold ${s.valid_requests > 0 ? 'text-emerald-400' : 'text-slate-500'}`}>
                    {s.valid_requests} valid requests
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 2. Semantic Column Mapping Controls */}
      <div className="p-4 bg-[#070A12] rounded-2xl border border-white/[0.06] space-y-4">
        <div className="flex items-center justify-between border-b border-white/[0.06] pb-2.5">
          <div>
            <span className="text-xs font-bold text-slate-200 uppercase font-mono tracking-wider flex items-center gap-2">
              <Settings2 className="w-3.5 h-3.5 text-cyan-400" />
              2. Semantic Column Alignment
            </span>
            <p className="text-[10px] text-slate-400 mt-0.5">
              Automatically recognized based on chemical SDS semantics. Modify alignments if required.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
          {/* Product (Required) */}
          <div className="space-y-1.5">
            <label className="flex items-center justify-between font-mono text-[11px] font-bold text-slate-300">
              <span className="flex items-center gap-1">
                <span className="text-cyan-400">●</span> Chemical Product
              </span>
              <span className="text-[9px] text-cyan-400 uppercase font-bold bg-cyan-950/80 px-1.5 py-0.2 rounded border border-cyan-500/30">
                Required
              </span>
            </label>
            <select
              value={productCol}
              onChange={(e) => setProductCol(e.target.value)}
              className="w-full bg-[#0B1020] border border-cyan-500/40 text-slate-100 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-cyan-400 cursor-pointer shadow-sm"
            >
              <option value="">-- Select Product Column --</option>
              {allColumns.map((c, i) => (
                <option key={i} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          {/* Manufacturer (Highly Recommended) */}
          <div className="space-y-1.5">
            <label className="flex items-center justify-between font-mono text-[11px] font-bold text-slate-300">
              <span>Manufacturer / Company</span>
              <span className="text-[9px] text-emerald-400 uppercase font-bold bg-emerald-950/80 px-1.5 py-0.2 rounded border border-emerald-500/30">
                Recommended
              </span>
            </label>
            <select
              value={companyCol}
              onChange={(e) => setCompanyCol(e.target.value)}
              className="w-full bg-[#0B1020] border border-white/[0.1] text-slate-200 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-cyan-400 cursor-pointer"
            >
              <option value="">-- None / Auto-extract --</option>
              {allColumns.map((c, i) => (
                <option key={i} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          {/* Part Number / ID */}
          <div className="space-y-1.5">
            <label className="flex items-center justify-between font-mono text-[11px] font-bold text-slate-300">
              <span>Part / Catalog / CAS No</span>
              <span className="text-[9px] text-slate-400 uppercase font-bold bg-white/[0.04] px-1.5 py-0.2 rounded border border-white/[0.06]">
                Optional
              </span>
            </label>
            <select
              value={partNumCol}
              onChange={(e) => setPartNumCol(e.target.value)}
              className="w-full bg-[#0B1020] border border-white/[0.1] text-slate-200 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-cyan-400 cursor-pointer"
            >
              <option value="">-- None / Optional --</option>
              {allColumns.map((c, i) => (
                <option key={i} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          {/* Language */}
          <div className="space-y-1.5">
            <label className="flex items-center justify-between font-mono text-[11px] font-bold text-slate-300">
              <span>Document Language</span>
              <span className="text-[9px] text-slate-400 uppercase font-bold bg-white/[0.04] px-1.5 py-0.2 rounded border border-white/[0.06]">
                Default: English
              </span>
            </label>
            <select
              value={langCol}
              onChange={(e) => setLangCol(e.target.value)}
              className="w-full bg-[#0B1020] border border-white/[0.1] text-slate-200 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-cyan-400 cursor-pointer"
            >
              <option value="">-- None (Default: English) --</option>
              {allColumns.map((c, i) => (
                <option key={i} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          {/* Country / Jurisdiction */}
          <div className="space-y-1.5">
            <label className="flex items-center justify-between font-mono text-[11px] font-bold text-slate-300">
              <span>Country / Jurisdiction</span>
              <span className="text-[9px] text-slate-400 uppercase font-bold bg-white/[0.04] px-1.5 py-0.2 rounded border border-white/[0.06]">
                Optional
              </span>
            </label>
            <select
              value={countryCol}
              onChange={(e) => setCountryCol(e.target.value)}
              className="w-full bg-[#0B1020] border border-white/[0.1] text-slate-200 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-cyan-400 cursor-pointer"
            >
              <option value="">-- None / Global --</option>
              {allColumns.map((c, i) => (
                <option key={i} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          {/* Confirm Button */}
          <div className="flex flex-col justify-end">
            <Button
              variant="primary"
              size="md"
              onClick={handleSave}
              isLoading={isConfirming}
              disabled={!hasProduct || !hasSelectedSheets || validRequestsCount === 0}
              rightIcon={<ArrowRight className="w-4 h-4" />}
              className="w-full shadow-glow-cyan"
            >
              Confirm Request Set ({validRequestsCount} Requests)
            </Button>
          </div>
        </div>
      </div>
    </Card>
  );
};
