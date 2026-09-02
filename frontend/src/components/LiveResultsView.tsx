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
  Sparkles
} from 'lucide-react';
import type { AnalyzeScanResponse } from '../types/api';
import { scanApi } from '../services/api';

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
  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false);

  const { compliance_result, visual_evidence, authenticity_result, scan_id, ocr_summary } = result;
  const isCompliant = compliance_result.overall_status === 'COMPLIANT';
  const isPotentiallyNonCompliant = compliance_result.overall_status === 'POTENTIALLY_NON_COMPLIANT';

  // Filtered rules
  const filteredResults = compliance_result.results.filter((rule) => {
    if (selectedFilter === 'ALL') return true;
    return rule.status === selectedFilter;
  });

  // Download PDF Report
  const handleDownloadPdf = async () => {
    if (!scan_id) {
      alert('PDF Report is available for saved scans. Scan ID was not generated.');
      return;
    }
    try {
      setIsDownloadingPdf(true);
      const blob = await scanApi.downloadPdfBlob(scan_id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `LegalMetrology_Compliance_Report_Scan_${scan_id}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch {
      alert('Failed to download PDF report. Ensure backend PDF generator is running.');
    } finally {
      setIsDownloadingPdf(false);
    }
  };

  // Image source priority: Base64 annotated image -> Original preview
  const displayImage = visual_evidence?.annotated_image_base64
    ? `data:image/jpeg;base64,${visual_evidence.annotated_image_base64}`
    : originalImageSrc;

  return (
    <div className="w-full max-w-6xl mx-auto space-y-6 animate-fade-in">
      {/* Top Action Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <button
          onClick={onReset}
          className="flex items-center space-x-2 text-xs font-semibold text-slate-400 hover:text-slate-100 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 hover:bg-slate-800 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>New Inspection Scan</span>
        </button>

        <div className="flex items-center space-x-3 w-full sm:w-auto justify-between sm:justify-end">
          {scan_id && (
            <button
              onClick={handleDownloadPdf}
              disabled={isDownloadingPdf}
              className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold text-xs shadow-lg transition-all active:scale-95 disabled:opacity-50"
            >
              <Download className="w-3.5 h-3.5" />
              <span>{isDownloadingPdf ? 'Generating PDF...' : 'Download Official PDF Report'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Compliance Overview Banner */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-5">
        {/* Left: Score & Status Card */}
        <div
          className={`md:col-span-8 p-6 rounded-2xl glass-panel border flex flex-col justify-between ${
            isCompliant
              ? 'border-emerald-500/30 bg-emerald-950/10'
              : isPotentiallyNonCompliant
              ? 'border-amber-500/30 bg-amber-950/10'
              : 'border-rose-500/30 bg-rose-950/10'
          }`}
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-1.5">
              <div className="flex items-center space-x-2">
                <span
                  className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                    isCompliant
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                      : isPotentiallyNonCompliant
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                      : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                  }`}
                >
                  {compliance_result.overall_status.replace(/_/g, ' ')}
                </span>
                {scan_id && (
                  <span className="text-xs text-slate-400 font-mono">
                    Scan ID #{scan_id}
                  </span>
                )}
              </div>
              <h2 className="text-2xl font-bold text-white font-display">
                {compliance_result.product_name || 'Standard Pre-Packaged Commodity'}
              </h2>
              <p className="text-xs text-slate-300 max-w-xl">
                {compliance_result.summary}
              </p>
            </div>

            {/* Circular / Block Score Gauge */}
            <div className="flex-shrink-0 flex items-center space-x-3 bg-slate-900/90 border border-slate-800 p-4 rounded-xl">
              <div className="text-center">
                <span className="block text-3xl font-extrabold text-white font-display">
                  {compliance_result.compliance_score.toFixed(0)}%
                </span>
                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                  Compliance Score
                </span>
              </div>
            </div>
          </div>

          {/* Quick Metrics Bar */}
          <div className="grid grid-cols-3 gap-3 mt-6 pt-4 border-t border-slate-800/80">
            <div className="text-center p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
              <span className="block text-lg font-bold text-emerald-300">
                {compliance_result.passed_rules_count}
              </span>
              <span className="text-[10px] text-emerald-400/80 font-medium">Passed Declarations</span>
            </div>
            <div className="text-center p-2 rounded-lg bg-rose-500/10 border border-rose-500/20">
              <span className="block text-lg font-bold text-rose-300">
                {compliance_result.failed_rules_count}
              </span>
              <span className="text-[10px] text-rose-400/80 font-medium">Violations Detected</span>
            </div>
            <div className="text-center p-2 rounded-lg bg-amber-500/10 border border-amber-500/20">
              <span className="block text-lg font-bold text-amber-300">
                {compliance_result.warning_rules_count}
              </span>
              <span className="text-[10px] text-amber-400/80 font-medium">Advisory Warnings</span>
            </div>
          </div>
        </div>

        {/* Right: DINOv2 Authenticity Card */}
        <div className="md:col-span-4 p-5 rounded-2xl glass-panel border border-slate-800 flex flex-col justify-between space-y-3">
          <div className="flex items-center space-x-2 pb-2 border-b border-slate-800">
            <Sparkles className="w-4 h-4 text-brand-400" />
            <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider font-display">
              DINOv2 Visual Authenticity
            </h3>
          </div>

          {authenticity_result ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">Verdict:</span>
                <span
                  className={`px-2.5 py-1 rounded-md text-xs font-bold ${
                    authenticity_result.verdict === 'GENUINE_LIKELY'
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                      : authenticity_result.verdict === 'SUSPICIOUS'
                      ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                      : 'bg-slate-800 text-slate-300 border border-slate-700'
                  }`}
                >
                  {authenticity_result.verdict.replace(/_/g, ' ')}
                </span>
              </div>

              <div className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-400">Trade Dress Similarity</span>
                  <span className="text-slate-200 font-mono font-semibold">
                    {(authenticity_result.similarity_score * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="w-full bg-slate-900 rounded-full h-2 overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      authenticity_result.similarity_score >= authenticity_result.threshold_used
                        ? 'bg-emerald-500'
                        : 'bg-rose-500'
                    }`}
                    style={{ width: `${Math.min(100, authenticity_result.similarity_score * 100)}%` }}
                  />
                </div>
              </div>

              <p className="text-[11px] text-slate-400 bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
                {authenticity_result.notes}
              </p>
            </div>
          ) : (
            <div className="text-center py-6 text-slate-500 text-xs">
              No reference brand was specified for DINOv2 trade dress verification.
            </div>
          )}

          {ocr_summary && (
            <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
              <span>OCR Strategy: <strong className="text-slate-200">{ocr_summary.strategy_used}</strong></span>
              <span>Avg Confidence: <strong className="text-slate-200">{(ocr_summary.average_confidence * 100).toFixed(0)}%</strong></span>
            </div>
          )}
        </div>
      </div>

      {/* Main Evidence Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Annotated Evidence Image */}
        <div className="lg:col-span-5 glass-panel rounded-2xl p-4 flex flex-col space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <div className="flex items-center space-x-2">
              <Eye className="w-4 h-4 text-brand-400" />
              <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                Visual Statutory Evidence
              </h3>
            </div>
            {visual_evidence?.bounding_boxes && (
              <span className="text-[11px] font-mono text-slate-400">
                {visual_evidence.bounding_boxes.length} Bounding Regions
              </span>
            )}
          </div>

          <div className="relative w-full h-[400px] rounded-xl overflow-hidden bg-slate-950 border border-slate-800 flex items-center justify-center">
            <img
              src={displayImage}
              alt="Annotated Package Evidence"
              className="w-full h-full object-contain"
            />
          </div>

          <p className="text-[10px] text-slate-500 italic text-center">
            Green boxes represent compliant statutory declarations; Red boxes indicate missing, obscured, or non-compliant text.
          </p>
        </div>

        {/* Right: Statutory Declarations Table (PCR 2011) */}
        <div className="lg:col-span-7 glass-panel rounded-2xl p-5 flex flex-col space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
            <div className="flex items-center space-x-2">
              <Scale className="w-4 h-4 text-indigo-400" />
              <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                Rule-by-Rule Compliance Table
              </h3>
            </div>

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
              <div className="text-center py-12 text-slate-500 text-xs">
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

                  {/* Official Legal Citation & DoCA Source Document */}
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
      </div>
    </div>
  );
};
