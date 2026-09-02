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
  HelpCircle
} from 'lucide-react';
import type { AnalyzeScanResponse, ExtractedFeature, MissingField } from '../types/api';
import { scanApi } from '../services/api';
import { FONT_SIZE_DISCLAIMER } from '../constants';

interface LiveResultsViewProps {
  result: AnalyzeScanResponse;
  originalImageSrc: string;
  onReset: () => void;
}

export const LiveResultsView: React.FC<LiveResultsViewProps> = ({
  result,
  originalImageSrc,
  onReset,
}) => {
  const [selectedFilter, setSelectedFilter] = useState<'ALL' | 'FAIL' | 'WARNING' | 'PASS'>('ALL');
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);
  const [selectedPanelIndex, setSelectedPanelIndex] = useState<number>(0);
  const [showTechnicalRules, setShowTechnicalRules] = useState<boolean>(false);

  const { compliance_result, visual_evidence, authenticity_result, scan_id, ocr_summary, extraction_insight } = result;

  // Filtered rules for technical view
  const filteredResults = compliance_result.results.filter((rule) => {
    if (selectedFilter === 'ALL') return true;
    return rule.status === selectedFilter;
  });

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

  // Download Handlers
  const handleDownloadPdf = async () => {
    if (!scan_id) {
      alert('PDF Report is available for saved scans. Scan ID was not generated.');
      return;
    }
    try {
      setActionInProgress('pdf');
      const blob = await scanApi.downloadPdfBlob(scan_id);
      downloadFile(blob, `LegalMetrology_Compliance_Report_Scan_${scan_id}.pdf`);
    } catch {
      alert('Failed to download PDF report. Ensure backend PDF generator is running.');
    } finally {
      setActionInProgress(null);
    }
  };

  const handleDownloadExcel = async () => {
    if (!scan_id) {
      alert('Excel export is available for saved scans.');
      return;
    }
    try {
      setActionInProgress('xlsx');
      const blob = await scanApi.downloadXlsxBlob(scan_id);
      downloadFile(blob, `LegalMetrology_Compliance_Audit_Scan_${scan_id}.xlsx`);
    } catch {
      alert('Failed to download Excel report.');
    } finally {
      setActionInProgress(null);
    }
  };

  const handleDownloadCsv = async () => {
    if (!scan_id) {
      alert('CSV export is available for saved scans.');
      return;
    }
    try {
      setActionInProgress('csv');
      const blob = await scanApi.downloadCsvBlob(scan_id);
      downloadFile(blob, `LegalMetrology_Scan_${scan_id}_Export.csv`);
    } catch {
      alert('Failed to download CSV export.');
    } finally {
      setActionInProgress(null);
    }
  };

  const handleDownloadDocx = async () => {
    if (!scan_id) {
      alert('Show-Cause Draft is available for saved scans.');
      return;
    }
    try {
      setActionInProgress('docx');
      const blob = await scanApi.downloadDocxBlob(scan_id);
      downloadFile(blob, `Show_Cause_Notice_Draft_Scan_${scan_id}.docx`);
    } catch {
      alert('Failed to generate Show-Cause notice draft.');
    } finally {
      setActionInProgress(null);
    }
  };

  // Format base64 image URI safely
  const formatImageSrc = (src?: string) => {
    if (!src) return '';
    if (src.startsWith('data:') || src.startsWith('http://') || src.startsWith('https://') || src.startsWith('blob:')) {
      return src;
    }
    return `data:image/jpeg;base64,${src}`;
  };

  // Collect available images
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

  // Extract features & missing fields from insight or fallback computation
  const foundFeatures: ExtractedFeature[] = extraction_insight?.found_features || [];
  const missingFields: MissingField[] = extraction_insight?.missing_fields || [];
  const panelsAnalyzed = extraction_insight?.panels_analyzed || (result.images_processed || 1);
  const coverageNote = extraction_insight?.coverage_note || `${foundFeatures.length} declarations extracted across ${panelsAnalyzed} panel image(s).`;

  return (
    <div className="w-full max-w-6xl mx-auto space-y-6 animate-fade-in">
      {/* Top Action Bar */}
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <button
          onClick={onReset}
          className="flex items-center space-x-2 text-xs font-semibold text-slate-400 hover:text-slate-100 px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-800 hover:bg-slate-800 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>New Inspection Scan</span>
        </button>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2.5 w-full lg:w-auto justify-start lg:justify-end">
          {scan_id && (
            <>
              <button
                onClick={handleDownloadCsv}
                disabled={actionInProgress === 'csv'}
                className="flex items-center space-x-1.5 px-3 py-2 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 hover:bg-slate-800 text-slate-200 font-semibold text-xs transition-all active:scale-95 disabled:opacity-50"
                title="Download single scan CSV report"
              >
                {actionInProgress === 'csv' ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <FileCode2 className="w-3.5 h-3.5 text-indigo-400" />
                )}
                <span>Download CSV</span>
              </button>

              <button
                onClick={handleDownloadExcel}
                disabled={actionInProgress === 'xlsx'}
                className="flex items-center space-x-1.5 px-3 py-2 rounded-xl bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/30 font-semibold text-xs transition-all active:scale-95 disabled:opacity-50"
                title="Download formatted Excel (.xlsx) report"
              >
                {actionInProgress === 'xlsx' ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <FileSpreadsheet className="w-3.5 h-3.5" />
                )}
                <span>Download Excel</span>
              </button>

              <button
                onClick={handleDownloadPdf}
                disabled={actionInProgress === 'pdf'}
                className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white font-semibold text-xs shadow-glow transition-all active:scale-95 disabled:opacity-50"
                title="Download official PDF report"
              >
                {actionInProgress === 'pdf' ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Download className="w-3.5 h-3.5" />
                )}
                <span>Download PDF</span>
              </button>

              <button
                onClick={handleDownloadDocx}
                disabled={actionInProgress === 'docx'}
                className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-gradient-to-r from-rose-600 to-amber-600 hover:from-rose-500 hover:to-amber-500 text-white font-bold text-xs shadow-lg transition-all active:scale-95 disabled:opacity-50"
                title="Generate official Show-Cause Notice Draft"
              >
                {actionInProgress === 'docx' ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <FileText className="w-3.5 h-3.5" />
                )}
                <span>Generate Show-Cause Draft (DOCX)</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Feature Extraction Overview Banner */}
      <div className="p-6 rounded-2xl glass-panel border border-indigo-500/30 bg-slate-900/80 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="px-3 py-1 rounded-full text-xs font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 flex items-center space-x-1.5">
                <Layers className="w-3.5 h-3.5 text-indigo-400" />
                <span>Feature Extraction Assessment</span>
              </span>

              {compliance_result.input_type === 'ecommerce_listing' ? (
                <span className="px-3 py-1 rounded-full text-xs font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 flex items-center space-x-1.5">
                  <ShoppingBag className="w-3.5 h-3.5" />
                  <span>E-Commerce Listing Mode</span>
                </span>
              ) : (
                <span className="px-3 py-1 rounded-full text-xs font-bold bg-slate-800 text-slate-300 border border-slate-700 flex items-center space-x-1.5">
                  <Package className="w-3.5 h-3.5 text-brand-400" />
                  <span>Physical Package Scan</span>
                </span>
              )}

              {panelsAnalyzed > 1 && (
                <span className="px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  Multi-Panel ({panelsAnalyzed} Images)
                </span>
              )}

              {scan_id && (
                <span className="text-xs text-slate-400 font-mono">
                  Scan ID #{scan_id}
                </span>
              )}
            </div>

            <h2 className="text-2xl font-bold text-white font-display">
              {compliance_result.product_name || 'Standard Pre-Packaged Commodity'}
            </h2>
            <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
              {coverageNote} Essential statutory features have been extracted from the image. Review found declarations below and upload missing panel sides if required.
            </p>
          </div>

          {/* Feature Extraction Metrics Box */}
          <div className="flex-shrink-0 flex items-center space-x-4 bg-slate-950/80 border border-slate-800 p-4 rounded-xl">
            <div className="text-center px-2">
              <span className="block text-2xl font-extrabold text-emerald-400 font-display">
                {foundFeatures.length}
              </span>
              <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                Declarations Found
              </span>
            </div>
            <div className="h-8 w-px bg-slate-800" />
            <div className="text-center px-2">
              <span className="block text-2xl font-extrabold text-amber-400 font-display">
                {missingFields.length}
              </span>
              <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                Missing / Uncaptured
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Feature Extraction Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Visual Annotated Image Viewer */}
        <div className="lg:col-span-5 glass-panel rounded-2xl p-4 flex flex-col space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <div className="flex items-center space-x-2">
              <Eye className="w-4 h-4 text-brand-400" />
              <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                Captured Package Evidence
              </h3>
            </div>
            {availableImages.length > 1 && (
              <span className="text-[11px] font-mono text-slate-400">
                {availableImages.length} Panel Views
              </span>
            )}
          </div>

          {availableImages.length > 1 && (
            <div className="flex items-center space-x-2 overflow-x-auto pb-1">
              {availableImages.map((_, idx) => (
                <button
                  key={idx}
                  onClick={() => setSelectedPanelIndex(idx)}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                    selectedPanelIndex === idx
                      ? 'bg-brand-600 text-white shadow-glow'
                      : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Panel #{idx + 1}
                </button>
              ))}
            </div>
          )}

          <div className="relative w-full h-[380px] rounded-xl overflow-hidden bg-slate-950 border border-slate-800 flex items-center justify-center">
            <img
              src={displayImage}
              alt="Annotated Package Evidence"
              className="w-full h-full object-contain"
            />
          </div>

          {/* DINOv2 Authenticity Widget */}
          {authenticity_result && (
            <div className="p-3 rounded-xl bg-slate-900/90 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-1.5 text-xs font-bold text-slate-200">
                  <Sparkles className="w-3.5 h-3.5 text-brand-400" />
                  <span>Trade Dress Authenticity</span>
                </div>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    authenticity_result.verdict === 'GENUINE_LIKELY'
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                      : authenticity_result.verdict === 'SUSPICIOUS'
                      ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                      : 'bg-slate-800 text-slate-300'
                  }`}
                >
                  {authenticity_result.verdict.replace(/_/g, ' ')}
                </span>
              </div>
              <p className="text-[10.5px] text-slate-400">
                {authenticity_result.notes}
              </p>
            </div>
          )}

          {ocr_summary && ocr_summary.strategy_used && (
            <div className="p-3 rounded-xl bg-slate-900/90 border border-slate-800 text-[10.5px] text-slate-400 flex items-center justify-between">
              <span>OCR Extraction Strategy: <strong className="text-slate-200">{ocr_summary.strategy_used}</strong></span>
              <span className="text-emerald-400 font-medium">Multi-Pass Enabled</span>
            </div>
          )}



          {/* Font Size & Readability Measurement Disclaimer Callout */}
          <div className="p-3 rounded-xl bg-slate-900/90 border border-slate-800/90 space-y-1">
            <div className="flex items-center space-x-1.5 text-brand-300 font-semibold text-[11px]">
              <Info className="w-3.5 h-3.5 text-brand-400 flex-shrink-0" />
              <span>Measurement Disclaimer</span>
            </div>
            <p className="text-slate-400 text-[10.5px] leading-relaxed">
              {FONT_SIZE_DISCLAIMER}
            </p>
          </div>
        </div>

        {/* Right Column: Extracted Features & Missing Fields Prompt */}
        <div className="lg:col-span-7 space-y-6">
          {/* Section 1: What We Found (Extracted Mandatory Features) */}
          <div className="glass-panel rounded-2xl p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                  Extracted Mandatory Features ({foundFeatures.length})
                </h3>
              </div>
              <span className="text-[11px] text-slate-400">
                Verified from Image OCR
              </span>
            </div>

            {foundFeatures.length === 0 ? (
              <div className="text-center py-8 text-slate-500 text-xs bg-slate-950/40 rounded-xl border border-slate-800">
                No statutory declarations were clearly identified from the current image view.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[380px] overflow-y-auto pr-1">
                {foundFeatures.map((feat) => (
                  <div
                    key={feat.field_key}
                    className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800/90 hover:border-slate-700/80 transition-all flex flex-col justify-between space-y-2"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-[11px] font-bold text-slate-300 font-display">
                          {feat.label}
                        </span>
                        {feat.confidence > 0 && (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            {(feat.confidence * 100).toFixed(0)}% conf
                          </span>
                        )}
                      </div>
                      <p className="text-xs font-semibold text-emerald-300 font-mono bg-slate-950 p-2 rounded-lg border border-slate-800/80 break-words">
                        {feat.value}
                      </p>
                    </div>

                    <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1 border-t border-slate-800/60">
                      <span>{feat.legal_ref}</span>
                      {feat.panel_index !== undefined && availableImages.length > 1 && (
                        <span className="text-brand-300">
                          Panel #{feat.panel_index + 1}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Section 2: What's Still Needed & Action Prompt (Missing Fields) */}
          {missingFields.length > 0 && (
            <div className="glass-panel rounded-2xl p-5 border border-amber-500/30 bg-amber-950/10 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-amber-500/20">
                <div className="flex items-center space-x-2">
                  <AlertTriangle className="w-4 h-4 text-amber-400" />
                  <h3 className="text-xs font-bold text-amber-200 uppercase tracking-wider">
                    Uncaptured / Missing Declarations ({missingFields.length})
                  </h3>
                </div>
                <span className="text-[11px] text-amber-300/80">
                  Required by PCR 2011 Rules
                </span>
              </div>

              <p className="text-xs text-slate-300 leading-relaxed">
                The declarations below were not visible or captured in the uploaded panel image(s). To complete the full statutory compliance audit, please capture and upload the corresponding panel view.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {missingFields.map((field) => (
                  <div
                    key={field.field_key}
                    className="p-3.5 rounded-xl bg-slate-950/70 border border-amber-500/20 space-y-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-amber-300">
                        {field.label}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      {field.why_required}
                    </p>
                    <div className="pt-1.5 flex items-center justify-between text-[10px]">
                      <span className="inline-flex items-center space-x-1 text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                        <HelpCircle className="w-3 h-3 text-amber-400" />
                        <span>Usually on: <strong>{field.usually_on}</strong></span>
                      </span>
                    </div>
                  </div>
                ))}
              </div>

              {/* Action Prompt Callout Button */}
              <div className="pt-2 flex flex-col sm:flex-row items-center justify-between gap-3 bg-slate-950/80 p-4 rounded-xl border border-amber-500/30">
                <div className="space-y-0.5">
                  <h4 className="text-xs font-bold text-white">
                    Need to add another panel image?
                  </h4>
                  <p className="text-[11px] text-slate-400">
                    Upload the Front / Principal Display Panel or Back Information Side to fuse extractions.
                  </p>
                </div>
                <button
                  onClick={onReset}
                  className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs shadow-lg transition-all active:scale-95 flex-shrink-0"
                >
                  <PlusCircle className="w-4 h-4" />
                  <span>Upload Additional Panel Image</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Section 3: Collapsible Technical Rule Engine Table */}
      <div className="glass-panel rounded-2xl p-5 border border-slate-800 space-y-4">
        <button
          onClick={() => setShowTechnicalRules(!showTechnicalRules)}
          className="w-full flex items-center justify-between text-left focus:outline-none group"
        >
          <div className="flex items-center space-x-2">
            <Scale className="w-4 h-4 text-indigo-400" />
            <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider group-hover:text-white transition-colors">
              Technical Rule Engine & Legal Reference Audit ({compliance_result.results.length} Checks Evaluated)
            </h3>
          </div>
          <div className="flex items-center space-x-2 text-xs text-slate-400 font-medium">
            <span>{showTechnicalRules ? 'Hide Technical Details' : 'Show Technical Details'}</span>
            {showTechnicalRules ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </div>
        </button>

        {showTechnicalRules && (
          <div className="space-y-4 pt-3 border-t border-slate-800/80 animate-fade-in">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <p className="text-xs text-slate-400">
                Individual PCR 2011 rule verification logic based on detected features vs statutory requirements.
              </p>

              {/* Filter Pills */}
              <div className="flex items-center space-x-1 bg-slate-900 p-1 rounded-lg border border-slate-800 text-xs">
                {(['ALL', 'FAIL', 'WARNING', 'PASS'] as const).map((filter) => (
                  <button
                    key={filter}
                    onClick={() => setSelectedFilter(filter)}
                    className={`px-2.5 py-1 rounded-md font-semibold transition-all ${
                      selectedFilter === filter
                        ? 'bg-brand-600 text-white shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {filter}
                  </button>
                ))}
              </div>
            </div>

            {/* Rules List */}
            <div className="space-y-3 max-h-[460px] overflow-y-auto pr-1">
              {filteredResults.length === 0 ? (
                <div className="text-center py-8 text-slate-500 text-xs">
                  No declarations match the selected filter.
                </div>
              ) : (
                filteredResults.map((rule) => (
                  <div
                    key={rule.rule_id}
                    className={`p-4 rounded-xl border transition-all ${
                      rule.status === 'PASS'
                        ? 'bg-emerald-950/20 border-emerald-500/30'
                        : rule.status === 'WARNING'
                        ? 'bg-amber-950/20 border-amber-500/30'
                        : 'bg-rose-950/20 border-rose-500/30'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="space-y-1 flex-1">
                        <div className="flex items-center space-x-2">
                          {rule.status === 'PASS' && (
                            <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                          )}
                          {rule.status === 'FAIL' && (
                            <XCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
                          )}
                          {rule.status === 'WARNING' && (
                            <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />
                          )}
                          <h4 className="text-sm font-bold text-slate-100">
                            {rule.rule_name}
                          </h4>
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">
                            {rule.rule_id}
                          </span>
                        </div>

                        <p className="text-xs text-slate-300 font-medium">
                          {rule.reason}
                        </p>

                        {rule.detected_value && (
                          <div className="text-[11px] text-slate-400 bg-slate-950/50 p-2 rounded-lg border border-slate-800/80 font-mono">
                            <span className="text-slate-500">Detected Value:</span> {rule.detected_value}
                          </div>
                        )}
                      </div>

                      <span
                        className={`px-2.5 py-1 rounded-md text-[11px] font-bold ${
                          rule.status === 'PASS'
                            ? 'bg-emerald-500/20 text-emerald-300'
                            : rule.status === 'WARNING'
                            ? 'bg-amber-500/20 text-amber-300'
                            : 'bg-rose-500/20 text-rose-300'
                        }`}
                      >
                        {rule.status}
                      </span>
                    </div>

                    {/* Legal Citation & DoCA Source Document */}
                    <div className="mt-3 pt-2.5 border-t border-slate-800/60 flex flex-wrap items-center justify-between gap-2 text-[11px]">
                      <div className="flex items-center space-x-1.5 text-brand-300">
                        <BookOpen className="w-3.5 h-3.5 text-brand-400" />
                        <span>{rule.official_legal_reference || rule.legal_reference}</span>
                      </div>

                      {rule.source_pdf && (
                        <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-[10px] font-mono">
                          <FileText className="w-2.5 h-2.5" />
                          <span>DoCA: {rule.source_pdf}</span>
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

      {/* Permanent DoCA Legal Grounding Footer Info Card */}
      <div className="pt-4 border-t border-slate-800/80 text-center">
        <p className="text-xs text-slate-400 font-medium inline-flex items-center justify-center space-x-2 bg-slate-900/80 px-4 py-2 rounded-full border border-slate-800">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span>Powered by Official Legal Metrology (Packaged Commodities) Rules, 2011 and amendments issued by Department of Consumer Affairs</span>
        </p>
      </div>
    </div>
  );
};
