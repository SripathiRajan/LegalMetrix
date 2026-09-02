import React, { useState } from 'react';
import { 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  FileText, 
  Download, 
  ArrowLeft, 
  Scale, 
  BookOpen, 
  Eye, 
  Sparkles,
  FileSpreadsheet,
  FileCode2,
  RefreshCw,
  Package,
  ShoppingBag,
  Info,
  ChevronDown,
  ChevronUp,
  PlusCircle,
  Layers,
  HelpCircle,
  Shield,
  Zap,
  CheckCheck
} from 'lucide-react';
import type { AnalyzeScanResponse, ExtractedFeature, MissingField } from '../types/api';
import { scanApi } from '../services/api';
import { FONT_SIZE_DISCLAIMER } from '../constants';

interface LiveResultsViewProps {
  result: AnalyzeScanResponse;
  originalImageSrc: string;
  onReset: () => void;
  onOpenChat?: () => void;
}

export const LiveResultsView: React.FC<LiveResultsViewProps> = ({
  result,
  originalImageSrc,
  onReset,
  onOpenChat,
}) => {
  const [selectedFilter, setSelectedFilter] = useState<'ALL' | 'FAIL' | 'WARNING' | 'PASS'>('ALL');
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);
  const [selectedPanelIndex, setSelectedPanelIndex] = useState<number>(0);
  const [showTechnicalRules, setShowTechnicalRules] = useState<boolean>(false);

  const { compliance_result, visual_evidence, authenticity_result, scan_id, ocr_summary, extraction_insight } = result;

  const filteredResults = compliance_result.results.filter((rule) => {
    if (selectedFilter === 'ALL') return true;
    return rule.status === selectedFilter;
  });

  const passCount = compliance_result.results.filter(r => r.status === 'PASS').length;
  const failCount = compliance_result.results.filter(r => r.status === 'FAIL').length;
  const warnCount = compliance_result.results.filter(r => r.status === 'WARNING').length;

  const isCompliant = compliance_result.overall_status === 'COMPLIANT';
  const isWarning = compliance_result.overall_status === 'POTENTIALLY_NON_COMPLIANT';

  const downloadFile = (blob: Blob, filename: string) => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  };

  const handleDownloadPdf = async () => {
    if (!scan_id) { alert('PDF Report is available for saved scans. Scan ID was not generated.'); return; }
    try {
      setActionInProgress('pdf');
      const blob = await scanApi.downloadPdfBlob(scan_id);
      downloadFile(blob, `LegalMetrology_Compliance_Report_Scan_${scan_id}.pdf`);
    } catch { alert('Failed to download PDF report. Ensure backend PDF generator is running.'); }
    finally { setActionInProgress(null); }
  };

  const handleDownloadExcel = async () => {
    if (!scan_id) { alert('Excel export is available for saved scans.'); return; }
    try {
      setActionInProgress('xlsx');
      const blob = await scanApi.downloadXlsxBlob(scan_id);
      downloadFile(blob, `LegalMetrology_Compliance_Audit_Scan_${scan_id}.xlsx`);
    } catch { alert('Failed to download Excel report.'); }
    finally { setActionInProgress(null); }
  };

  const handleDownloadCsv = async () => {
    if (!scan_id) { alert('CSV export is available for saved scans.'); return; }
    try {
      setActionInProgress('csv');
      const blob = await scanApi.downloadCsvBlob(scan_id);
      downloadFile(blob, `LegalMetrology_Scan_${scan_id}_Export.csv`);
    } catch { alert('Failed to download CSV export.'); }
    finally { setActionInProgress(null); }
  };

  const handleDownloadDocx = async () => {
    if (!scan_id) { alert('Show-Cause Draft is available for saved scans.'); return; }
    try {
      setActionInProgress('docx');
      const blob = await scanApi.downloadDocxBlob(scan_id);
      downloadFile(blob, `Show_Cause_Notice_Draft_Scan_${scan_id}.docx`);
    } catch { alert('Failed to generate Show-Cause notice draft.'); }
    finally { setActionInProgress(null); }
  };

  const formatImageSrc = (src?: string) => {
    if (!src) return '';
    if (src.startsWith('data:') || src.startsWith('http://') || src.startsWith('https://') || src.startsWith('blob:')) return src;
    return `data:image/jpeg;base64,${src}`;
  };

  const rawImages: string[] = [];
  if (result.annotated_images && result.annotated_images.length > 0) {
    rawImages.push(...result.annotated_images);
  } else if (result.annotated_image) {
    rawImages.push(result.annotated_image);
  } else if (visual_evidence?.annotated_image_base64) {
    rawImages.push(visual_evidence.annotated_image_base64);
  } else if (originalImageSrc) {
    rawImages.push(originalImageSrc);
  }

  const availableImages = rawImages.map(formatImageSrc).filter(Boolean);
  const displayImage = availableImages[selectedPanelIndex] || availableImages[0] || originalImageSrc;

  const foundFeatures: ExtractedFeature[] = extraction_insight?.found_features || [];
  const missingFields: MissingField[] = extraction_insight?.missing_fields || [];
  const panelsAnalyzed = extraction_insight?.panels_analyzed || (result.images_processed || 1);
  const coverageNote = extraction_insight?.coverage_note || `${foundFeatures.length} declarations extracted across ${panelsAnalyzed} panel image(s).`;

  const complianceScore = compliance_result.compliance_score ?? 0;

  return (
    <div className="w-full max-w-6xl mx-auto space-y-6 animate-fade-in pb-12">

      {/* ── Top Action Bar ── */}
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 pb-5 border-b border-white/5">
        <div className="flex items-center gap-2">
          <button
            onClick={onReset}
            className="btn-ghost"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>New Inspection Scan</span>
          </button>
          {onOpenChat && (
            <button
              onClick={onOpenChat}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-sky-500/10 hover:bg-sky-500/20 text-sky-300 border border-sky-500/20 text-xs font-semibold transition-all active:scale-95"
            >
              <Sparkles className="w-3.5 h-3.5 text-sky-400" />
              <span>Ask AI About Package</span>
            </button>
          )}
        </div>

        {scan_id && (
          <div className="flex flex-wrap items-center gap-2 w-full lg:w-auto justify-start lg:justify-end">
            <button onClick={handleDownloadCsv} disabled={actionInProgress === 'csv'}
              className="btn-ghost !text-xs disabled:opacity-50">
              {actionInProgress === 'csv' ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <FileCode2 className="w-3.5 h-3.5 text-indigo-400" />}
              <span>CSV</span>
            </button>
            <button onClick={handleDownloadExcel} disabled={actionInProgress === 'xlsx'}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-blue-500/10 hover:bg-blue-500/15 text-blue-300 border border-blue-500/20 text-xs font-semibold transition-all active:scale-95 disabled:opacity-50">
              {actionInProgress === 'xlsx' ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <FileSpreadsheet className="w-3.5 h-3.5" />}
              <span>Excel</span>
            </button>
            <button onClick={handleDownloadPdf} disabled={actionInProgress === 'pdf'}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-white text-xs font-semibold transition-all active:scale-95 disabled:opacity-50 shadow"
              style={{ background: 'linear-gradient(135deg, #0171c7, #4f46e5)', boxShadow: '0 4px 15px rgba(14,165,233,0.25)' }}>
              {actionInProgress === 'pdf' ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
              <span>Download PDF</span>
            </button>
            <button onClick={handleDownloadDocx} disabled={actionInProgress === 'docx'}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-white font-bold text-xs transition-all active:scale-95 disabled:opacity-50 shadow-lg"
              style={{ background: 'linear-gradient(135deg, #dc2626, #d97706)', boxShadow: '0 4px 15px rgba(220,38,38,0.25)' }}>
              {actionInProgress === 'docx' ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <FileText className="w-3.5 h-3.5" />}
              <span>Show-Cause Draft</span>
            </button>
          </div>
        )}
      </div>

      {/* ── Verdict Hero Banner ── */}
      <div className={`relative overflow-hidden rounded-2xl border p-6 sm:p-7 ${
        isCompliant
          ? 'bg-emerald-950/20 border-emerald-500/25'
          : isWarning
          ? 'bg-amber-950/20 border-amber-500/25'
          : 'bg-rose-950/20 border-rose-500/25'
      }`}>
        {/* BG Orb */}
        <div className={`absolute -top-12 -right-12 w-40 h-40 rounded-full blur-3xl opacity-10 ${
          isCompliant ? 'bg-emerald-400' : isWarning ? 'bg-amber-400' : 'bg-rose-400'
        }`} />

        <div className="relative flex flex-col sm:flex-row sm:items-center gap-5">
          {/* Left: Product Info */}
          <div className="flex-1 space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border ${
                isCompliant ? 'badge-pass' : isWarning ? 'badge-warn' : 'badge-fail'
              }`}>
                {isCompliant ? <CheckCircle2 className="w-3.5 h-3.5" /> : isWarning ? <AlertTriangle className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
                {compliance_result.overall_status?.replace(/_/g, ' ')}
              </span>

              {compliance_result.input_type === 'ecommerce_listing' ? (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-500/10 text-amber-300 border border-amber-500/30">
                  <ShoppingBag className="w-3 h-3" /> E-Commerce Mode
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-white/5 text-slate-300 border border-white/10">
                  <Package className="w-3 h-3 text-sky-400" /> Physical Package
                </span>
              )}

              {panelsAnalyzed > 1 && (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-sky-500/10 text-sky-300 border border-sky-500/20">
                  <Layers className="w-3 h-3" /> {panelsAnalyzed} Panels
                </span>
              )}

              {scan_id && (
                <span className="text-xs text-slate-500 font-mono">Scan #{ scan_id}</span>
              )}
            </div>

            <h2 className="text-2xl sm:text-3xl font-extrabold text-white font-display tracking-tight">
              {compliance_result.product_name || 'Standard Pre-Packaged Commodity'}
            </h2>
            <p className="text-sm text-slate-400 max-w-xl leading-relaxed">{coverageNote}</p>
          </div>

          {/* Right: Score Radial + Stats */}
          <div className="flex items-center gap-4 sm:gap-6 flex-shrink-0">
            {/* Circular Progress Score */}
            <div className="relative flex-shrink-0">
              <svg width="80" height="80" viewBox="0 0 80 80">
                <circle cx="40" cy="40" r="34" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="7" />
                <circle
                  cx="40" cy="40" r="34"
                  fill="none"
                  stroke={isCompliant ? '#10b981' : isWarning ? '#f59e0b' : '#ef4444'}
                  strokeWidth="7"
                  strokeLinecap="round"
                  strokeDasharray={`${(complianceScore / 100) * 213.6} 213.6`}
                  transform="rotate(-90 40 40)"
                  style={{ transition: 'stroke-dasharray 0.8s ease' }}
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className={`text-lg font-extrabold font-display ${isCompliant ? 'text-emerald-300' : isWarning ? 'text-amber-300' : 'text-rose-300'}`}>
                  {complianceScore.toFixed(0)}%
                </span>
                <span className="text-[9px] text-slate-500 font-semibold uppercase tracking-wider">Score</span>
              </div>
            </div>

            {/* Mini stats */}
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-emerald-400" />
                <span className="text-xs text-slate-400">{passCount} Passed</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-amber-400" />
                <span className="text-xs text-slate-400">{warnCount} Warnings</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-rose-400" />
                <span className="text-xs text-slate-400">{failCount} Failed</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Main Content Grid ── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">

        {/* Left: Evidence Viewer */}
        <div className="lg:col-span-5 glass rounded-2xl border border-white/5 p-4 flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-white/5 pb-3">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center">
                <Eye className="w-3.5 h-3.5 text-sky-400" />
              </div>
              <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">Package Evidence</h3>
            </div>
            {availableImages.length > 1 && (
              <span className="text-[11px] font-mono text-slate-500">{availableImages.length} panels</span>
            )}
          </div>

          {/* Panel Selector */}
          {availableImages.length > 1 && (
            <div className="flex items-center gap-2 overflow-x-auto pb-1">
              {availableImages.map((_, idx) => (
                <button key={idx} onClick={() => setSelectedPanelIndex(idx)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex-shrink-0 ${
                    selectedPanelIndex === idx
                      ? 'text-white border-sky-500/40'
                      : 'bg-white/4 border border-white/5 text-slate-400 hover:text-slate-200'
                  }`}
                  style={selectedPanelIndex === idx ? { background: 'linear-gradient(135deg, rgba(1,113,199,0.4), rgba(79,70,229,0.4))', border: '1px solid rgba(14,165,233,0.4)' } : {}}
                >
                  Panel #{idx + 1}
                </button>
              ))}
            </div>
          )}

          {/* Image Viewer */}
          <div className="relative w-full h-[320px] rounded-xl overflow-hidden border border-white/5 bg-black flex items-center justify-center">
            <img src={displayImage} alt="Annotated Package Evidence" className="w-full h-full object-contain" />
          </div>

          {/* Brand Authenticity */}
          {authenticity_result && (
            <div className={`p-3.5 rounded-xl border space-y-2 ${
              authenticity_result.verdict === 'GENUINE_LIKELY'
                ? 'bg-emerald-950/20 border-emerald-500/20'
                : authenticity_result.verdict === 'SUSPICIOUS'
                ? 'bg-rose-950/20 border-rose-500/20'
                : 'border-white/5'
            }`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-xs font-bold text-slate-200">
                  <Sparkles className="w-3.5 h-3.5 text-sky-400" />
                  Brand Authenticity
                </div>
                <span className={`px-2.5 py-0.5 rounded-md text-[10px] font-bold ${
                  authenticity_result.verdict === 'GENUINE_LIKELY'
                    ? 'badge-pass'
                    : authenticity_result.verdict === 'SUSPICIOUS'
                    ? 'badge-fail'
                    : 'bg-white/5 text-slate-400 border border-white/10'
                }`}>
                  {authenticity_result.verdict.replace(/_/g, ' ')}
                </span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">{authenticity_result.notes}</p>
            </div>
          )}

          {ocr_summary && ocr_summary.strategy_used && (
            <div className="p-3 rounded-xl border border-white/5 bg-white/2 flex items-center justify-between text-[11px]">
              <span className="text-slate-500">OCR: <strong className="text-slate-300">{ocr_summary.strategy_used}</strong></span>
              <span className="text-sky-400 font-semibold flex items-center gap-1">
                <Zap className="w-3 h-3" /> Multi-Pass
              </span>
            </div>
          )}

          {/* Disclaimer */}
          <div className="p-3.5 rounded-xl border border-white/5 bg-sky-500/4 space-y-1.5">
            <div className="flex items-center gap-1.5 text-sky-300 font-semibold text-[11px]">
              <Info className="w-3.5 h-3.5 flex-shrink-0" />
              Measurement Disclaimer
            </div>
            <p className="text-slate-500 text-[10.5px] leading-relaxed">{FONT_SIZE_DISCLAIMER}</p>
          </div>
        </div>

        {/* Right: Extracted Features + Missing */}
        <div className="lg:col-span-7 space-y-5">
          
          {/* Found Features */}
          <div className="glass rounded-2xl border border-white/5 p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-white/5">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                  <CheckCheck className="w-3.5 h-3.5 text-emerald-400" />
                </div>
                <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                  Extracted Declarations ({foundFeatures.length})
                </h3>
              </div>
              <span className="text-[11px] text-slate-500 flex items-center gap-1">
                <Zap className="w-3 h-3 text-sky-400" /> From OCR
              </span>
            </div>

            {foundFeatures.length === 0 ? (
              <div className="py-10 text-center rounded-xl border border-white/5 bg-white/2">
                <Eye className="w-8 h-8 text-slate-700 mx-auto mb-2" />
                <p className="text-slate-600 text-xs">No declarations clearly identified from the current image.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[360px] overflow-y-auto pr-1">
                {foundFeatures.map((feat) => (
                  <div key={feat.field_key}
                    className="p-3.5 rounded-xl border border-white/5 bg-white/2 hover:border-sky-500/20 hover:bg-sky-500/4 transition-all flex flex-col gap-2"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <span className="text-[11px] font-bold text-slate-300">{feat.label}</span>
                      {feat.confidence > 0 && (
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/15 flex-shrink-0">
                          {(feat.confidence * 100).toFixed(0)}%
                        </span>
                      )}
                    </div>
                    <p className="text-xs font-semibold text-emerald-300 font-mono p-2 rounded-lg border border-white/5 bg-black/30 break-words">
                      {feat.value}
                    </p>
                    <div className="flex items-center justify-between text-[10px] text-slate-600 border-t border-white/4 pt-1.5">
                      <span>{feat.legal_ref}</span>
                      {feat.panel_index !== undefined && availableImages.length > 1 && (
                        <span className="text-sky-500">Panel #{feat.panel_index + 1}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Missing Fields */}
          {missingFields.length > 0 && (
            <div className="glass rounded-2xl border border-amber-500/20 bg-amber-950/10 p-5 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-amber-500/15">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                  </div>
                  <h3 className="text-xs font-bold text-amber-200 uppercase tracking-wider">
                    Uncaptured Declarations ({missingFields.length})
                  </h3>
                </div>
                <span className="text-[11px] text-amber-500">Required by Regulations</span>
              </div>

              <p className="text-xs text-slate-400 leading-relaxed">
                These declarations were not visible in the uploaded panel image(s). Upload the corresponding panel to complete the full audit.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {missingFields.map((field) => (
                  <div key={field.field_key}
                    className="p-3.5 rounded-xl border border-amber-500/15 bg-amber-950/15 space-y-1.5"
                  >
                    <span className="text-xs font-bold text-amber-300">{field.label}</span>
                    <p className="text-[11px] text-slate-400">{field.why_required}</p>
                    <div className="flex items-center gap-1.5 text-[10px] text-slate-500 bg-white/4 px-2 py-1 rounded-lg border border-white/5">
                      <HelpCircle className="w-3 h-3 text-amber-500" />
                      Usually on: <strong className="text-slate-300 ml-1">{field.usually_on}</strong>
                    </div>
                  </div>
                ))}
              </div>

              <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-4 rounded-xl border border-amber-500/20 bg-amber-950/20">
                <div>
                  <h4 className="text-xs font-bold text-white">Need to add another panel image?</h4>
                  <p className="text-[11px] text-slate-400 mt-0.5">Upload the Front Display or Back Information Panel to fuse extractions.</p>
                </div>
                <button onClick={onReset}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs shadow-lg transition-all active:scale-95 flex-shrink-0">
                  <PlusCircle className="w-4 h-4" /> Upload Panel
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Technical Rule Engine (Collapsible) ── */}
      <div className="glass rounded-2xl border border-white/5 overflow-hidden">
        <button
          onClick={() => setShowTechnicalRules(!showTechnicalRules)}
          className="w-full flex items-center justify-between p-5 text-left focus:outline-none hover:bg-white/2 transition-colors"
        >
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
              <Scale className="w-4 h-4 text-indigo-400" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-200 font-display">
                Technical Rule Engine Audit
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">{compliance_result.results.length} compliance rules evaluated</p>
            </div>
          </div>
          <div className="flex items-center gap-2.5 text-xs text-slate-400 font-medium">
            <span>{showTechnicalRules ? 'Collapse' : 'Expand Details'}</span>
            {showTechnicalRules ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </div>
        </button>

        {showTechnicalRules && (
          <div className="px-5 pb-5 space-y-4 border-t border-white/5 animate-fade-in pt-4">
            {/* Filter Pills */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <p className="text-xs text-slate-500">Individual rule checks based on detected fields vs required declarations.</p>
              <div className="flex items-center gap-1 glass rounded-xl p-1 border border-white/5">
                {(['ALL', 'FAIL', 'WARNING', 'PASS'] as const).map((filter) => (
                  <button
                    key={filter}
                    onClick={() => setSelectedFilter(filter)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                      selectedFilter === filter
                        ? filter === 'PASS' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/25'
                          : filter === 'FAIL' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/25'
                          : filter === 'WARNING' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/25'
                          : 'bg-sky-500/15 text-sky-300 border border-sky-500/25'
                        : 'text-slate-500 hover:text-slate-300'
                    }`}
                  >
                    {filter}
                    {filter !== 'ALL' && (
                      <span className="ml-1.5 text-[10px]">
                        ({filter === 'PASS' ? passCount : filter === 'FAIL' ? failCount : warnCount})
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* Rules List */}
            <div className="space-y-2.5 max-h-[480px] overflow-y-auto pr-1">
              {filteredResults.length === 0 ? (
                <div className="py-10 text-center text-slate-600 text-xs">No rules match the selected filter.</div>
              ) : (
                filteredResults.map((rule) => (
                  <div key={rule.rule_id}
                    className={`p-4 rounded-xl border transition-all ${
                      rule.status === 'PASS' ? 'bg-emerald-950/15 border-emerald-500/20'
                        : rule.status === 'WARNING' ? 'bg-amber-950/15 border-amber-500/20'
                        : 'bg-rose-950/15 border-rose-500/20'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="space-y-1.5 flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          {rule.status === 'PASS' && <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />}
                          {rule.status === 'FAIL' && <XCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />}
                          {rule.status === 'WARNING' && <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />}
                          <h4 className="text-sm font-bold text-slate-100">{rule.rule_name}</h4>
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/5 text-slate-500 border border-white/8">
                            {rule.rule_id}
                          </span>
                        </div>
                        <p className="text-xs text-slate-300 leading-relaxed">{rule.reason}</p>
                        {rule.detected_value && (
                          <div className="text-[11px] text-slate-400 bg-black/30 p-2 rounded-lg border border-white/5 font-mono">
                            <span className="text-slate-600">Detected:</span> {rule.detected_value}
                          </div>
                        )}
                      </div>
                      <span className={`px-2.5 py-1 rounded-md text-[11px] font-bold flex-shrink-0 ${
                        rule.status === 'PASS' ? 'bg-emerald-500/15 text-emerald-300'
                          : rule.status === 'WARNING' ? 'bg-amber-500/15 text-amber-300'
                          : 'bg-rose-500/15 text-rose-300'
                      }`}>
                        {rule.status}
                      </span>
                    </div>
                    <div className="mt-3 pt-2.5 border-t border-white/5 flex flex-wrap items-center justify-between gap-2 text-[11px]">
                      <div className="flex items-center gap-1.5 text-sky-400">
                        <BookOpen className="w-3.5 h-3.5 text-sky-500" />
                        {rule.official_legal_reference || rule.legal_reference}
                      </div>
                      {rule.source_pdf && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-[10px] font-mono">
                          <FileText className="w-2.5 h-2.5" /> Ref: {rule.source_pdf}
                        </span>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-center">
        <div className="inline-flex items-center gap-2.5 px-5 py-2.5 rounded-full glass border border-white/5 text-xs text-slate-500">
          <Shield className="w-3.5 h-3.5 text-sky-600" />
          Powered by LegalMetrix AI · Compliance Verification System
        </div>
      </div>
    </div>
  );
};
