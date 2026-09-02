import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { 
  History, 
  Search, 
  Download, 
  Eye, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  RefreshCw,
  X,
  FileSpreadsheet,
  FileText,
  FileCode2,
  Package,
  Filter,
  ChevronLeft,
  ChevronRight,
  Calendar
} from 'lucide-react';
import { scanApi } from '../services/api';
import type { ScanRecord } from '../types/api';

export const ScanHistoryView: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [page, setPage] = useState(0);
  const [selectedScan, setSelectedScan] = useState<ScanRecord | null>(null);
  const [isBulkDownloading, setIsBulkDownloading] = useState(false);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);
  const pageSize = 10;

  const { data, isLoading } = useQuery({
    queryKey: ['scans', page, statusFilter, searchTerm],
    queryFn: () => scanApi.getScans({
      limit: pageSize,
      offset: page * pageSize,
      status: statusFilter || undefined,
      product_name: searchTerm || undefined,
    }),
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

  const handleDownloadPdf = async (scanId: number) => {
    try {
      setActionInProgress(`pdf-${scanId}`);
      const blob = await scanApi.downloadPdfBlob(scanId);
      downloadFile(blob, `LegalMetrology_Report_Scan_${scanId}.pdf`);
    } catch { alert('Failed to download PDF report.'); }
    finally { setActionInProgress(null); }
  };

  const handleDownloadExcel = async (scanId: number) => {
    try {
      setActionInProgress(`xlsx-${scanId}`);
      const blob = await scanApi.downloadXlsxBlob(scanId);
      downloadFile(blob, `LegalMetrology_Audit_Scan_${scanId}.xlsx`);
    } catch { alert('Failed to download Excel report.'); }
    finally { setActionInProgress(null); }
  };

  const handleDownloadCsv = async (scanId: number) => {
    try {
      setActionInProgress(`csv-${scanId}`);
      const blob = await scanApi.downloadCsvBlob(scanId);
      downloadFile(blob, `LegalMetrology_Scan_${scanId}.csv`);
    } catch { alert('Failed to download CSV.'); }
    finally { setActionInProgress(null); }
  };

  const handleDownloadDocx = async (scanId: number) => {
    try {
      setActionInProgress(`docx-${scanId}`);
      const blob = await scanApi.downloadDocxBlob(scanId);
      downloadFile(blob, `Show_Cause_Notice_Scan_${scanId}.docx`);
    } catch { alert('Failed to generate Show-Cause Notice.'); }
    finally { setActionInProgress(null); }
  };

  const handleBulkDownloadExcel = async () => {
    try {
      setIsBulkDownloading(true);
      const blob = await scanApi.downloadBulkXlsxBlob({ status: statusFilter || undefined, product_name: searchTerm || undefined, limit: 500 });
      const timestamp = new Date().toISOString().slice(0, 10);
      downloadFile(blob, `LegalMetrology_Bulk_Scans_${timestamp}.xlsx`);
    } catch { alert('Failed to download bulk Excel export.'); }
    finally { setIsBulkDownloading(false); }
  };

  const statusConfig = {
    COMPLIANT:              { label: 'Compliant',            cls: 'badge-pass',  icon: <CheckCircle2 className="w-3 h-3" /> },
    NON_COMPLIANT:          { label: 'Non-Compliant',        cls: 'badge-fail',  icon: <XCircle className="w-3 h-3" /> },
    POTENTIALLY_NON_COMPLIANT: { label: 'Potential Violation', cls: 'badge-warn', icon: <AlertTriangle className="w-3 h-3" /> },
  } as const;

  return (
    <div className="w-full max-w-6xl mx-auto space-y-6 animate-fade-in pb-16">

      {/* ── Page Header ── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-5 pb-5 border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, rgba(14,165,233,0.15), rgba(99,102,241,0.15))', border: '1px solid rgba(14,165,233,0.2)' }}
          >
            <History className="w-5 h-5 text-sky-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white font-display tracking-tight">Audit Inspection History</h1>
            <p className="text-xs text-slate-500 mt-0.5">Historical package compliance records & downloadable reports</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Search */}
          <div className="relative">
            <input
              type="text" value={searchTerm}
              onChange={(e) => { setSearchTerm(e.target.value); setPage(0); }}
              placeholder="Search product or brand..."
              className="pl-9 pr-3 py-2.5 rounded-xl text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-sky-500/40 transition-all w-52"
              style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}
            />
            <Search className="absolute left-3 top-3 w-3.5 h-3.5 text-slate-600" />
          </div>

          {/* Status Filter */}
          <div className="relative flex items-center">
            <Filter className="absolute left-3 w-3.5 h-3.5 text-slate-600" />
            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(0); }}
              className="pl-9 pr-3 py-2.5 rounded-xl text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-sky-500/40 transition-all appearance-none"
              style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}
            >
              <option value="">All Statuses</option>
              <option value="COMPLIANT">Compliant</option>
              <option value="NON_COMPLIANT">Non-Compliant</option>
              <option value="POTENTIALLY_NON_COMPLIANT">Potentially Non-Compliant</option>
            </select>
          </div>

          {/* Bulk Export */}
          <button
            onClick={handleBulkDownloadExcel} disabled={isBulkDownloading}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/15 text-emerald-300 border border-emerald-500/20 text-xs font-semibold transition-all active:scale-95 disabled:opacity-50"
          >
            {isBulkDownloading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <FileSpreadsheet className="w-3.5 h-3.5" />}
            Bulk Export
          </button>
        </div>
      </div>

      {/* ── Records Table ── */}
      <div className="glass rounded-2xl border border-white/5 overflow-hidden">
        {isLoading ? (
          <div className="py-20 flex flex-col items-center gap-4">
            <div className="relative w-12 h-12">
              <div className="absolute inset-0 rounded-full border-2 border-sky-500/20" />
              <div className="absolute inset-0 rounded-full border-2 border-sky-500 border-t-transparent animate-spin" />
            </div>
            <p className="text-xs text-slate-500">Loading audit records...</p>
          </div>
        ) : !data || data.scans.length === 0 ? (
          <div className="py-20 text-center">
            <div className="w-14 h-14 rounded-2xl bg-white/4 border border-white/8 flex items-center justify-center mx-auto mb-4">
              <Package className="w-7 h-7 text-slate-600" />
            </div>
            <p className="text-slate-500 text-sm font-medium">No inspection records found</p>
            <p className="text-slate-600 text-xs mt-1">Try adjusting your filters or start a new scan</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs data-table">
              <thead className="border-b border-white/5">
                <tr className="text-slate-500 text-[11px] font-semibold uppercase tracking-wider">
                  <th className="py-3.5 px-5">Scan ID</th>
                  <th className="py-3.5 px-4">Product</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-4">Score</th>
                  <th className="py-3.5 px-4 hidden lg:table-cell">Authenticity</th>
                  <th className="py-3.5 px-4 hidden md:table-cell">Date</th>
                  <th className="py-3.5 px-5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/3">
                {data.scans.map((scan) => {
                  const statusKey = scan.overall_status as keyof typeof statusConfig;
                  const cfg = statusConfig[statusKey] || { label: scan.overall_status, cls: 'bg-white/5 text-slate-400 border border-white/10', icon: null };
                  return (
                    <tr key={scan.id} className="hover:bg-white/2 transition-colors">
                      <td className="py-4 px-5 font-mono font-bold text-slate-400">#{scan.id}</td>
                      <td className="py-4 px-4 font-semibold text-slate-100 max-w-[180px] truncate">
                        {scan.product_name || 'Commodity Package'}
                      </td>
                      <td className="py-4 px-4">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full font-bold text-[11px] ${cfg.cls}`}>
                          {cfg.icon}
                          {cfg.label}
                        </span>
                      </td>
                      <td className="py-4 px-4">
                        <div className="flex items-center gap-2">
                          <span className="font-bold font-mono text-slate-200">{scan.compliance_score.toFixed(0)}%</span>
                          <div className="progress-bar w-14 hidden sm:block">
                            <div className="progress-bar-fill" style={{ width: `${scan.compliance_score}%` }} />
                          </div>
                        </div>
                      </td>
                      <td className="py-4 px-4 hidden lg:table-cell">
                        {scan.authenticity_result ? (
                          <span className={`px-2 py-0.5 rounded-md text-[10px] font-semibold ${
                            scan.authenticity_result.verdict === 'GENUINE_LIKELY'
                              ? 'bg-emerald-500/15 text-emerald-300'
                              : scan.authenticity_result.verdict === 'SUSPICIOUS'
                              ? 'bg-rose-500/15 text-rose-300'
                              : 'bg-white/5 text-slate-400'
                          }`}>
                            {scan.authenticity_result.verdict.replace(/_/g, ' ')}
                          </span>
                        ) : (
                          <span className="text-slate-700 text-[11px]">N/A</span>
                        )}
                      </td>
                      <td className="py-4 px-4 text-slate-500 hidden md:table-cell">
                        <div className="flex items-center gap-1.5">
                          <Calendar className="w-3 h-3" />
                          {new Date(scan.created_at).toLocaleString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                        </div>
                      </td>
                      <td className="py-4 px-5">
                        <div className="flex items-center justify-end gap-1.5">
                          <button onClick={() => setSelectedScan(scan)} title="Inspect"
                            className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition-colors border border-white/5">
                            <Eye className="w-3.5 h-3.5" />
                          </button>
                          <button onClick={() => handleDownloadPdf(scan.id)} title="PDF"
                            className="p-2 rounded-lg bg-sky-500/10 hover:bg-sky-500/20 text-sky-400 border border-sky-500/15 transition-colors">
                            {actionInProgress === `pdf-${scan.id}` ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                          </button>
                          <button onClick={() => handleDownloadExcel(scan.id)} title="Excel"
                            className="p-2 rounded-lg bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 border border-blue-500/15 transition-colors">
                            {actionInProgress === `xlsx-${scan.id}` ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <FileSpreadsheet className="w-3.5 h-3.5" />}
                          </button>
                          <button onClick={() => handleDownloadCsv(scan.id)} title="CSV"
                            className="p-2 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 border border-indigo-500/15 transition-colors">
                            {actionInProgress === `csv-${scan.id}` ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <FileCode2 className="w-3.5 h-3.5" />}
                          </button>
                          <button onClick={() => handleDownloadDocx(scan.id)} title="Show-Cause"
                            className="p-2 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/15 transition-colors">
                            {actionInProgress === `docx-${scan.id}` ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <FileText className="w-3.5 h-3.5" />}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {data && data.total > pageSize && (
          <div className="px-5 py-4 border-t border-white/5 flex items-center justify-between text-xs text-slate-500">
            <span>
              Showing <strong className="text-slate-300">{page * pageSize + 1}</strong>–
              <strong className="text-slate-300">{Math.min((page + 1) * pageSize, data.total)}</strong>
              {' '}of <strong className="text-slate-300">{data.total}</strong> records
            </span>
            <div className="flex items-center gap-2">
              <button onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0}
                className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white disabled:opacity-30 border border-white/5 transition-colors">
                <ChevronLeft className="w-3.5 h-3.5" />
              </button>
              <span className="px-3 py-1.5 rounded-lg bg-sky-500/10 border border-sky-500/20 text-sky-300 font-semibold">
                {page + 1}
              </span>
              <button onClick={() => setPage((p) => p + 1)} disabled={(page + 1) * pageSize >= data.total}
                className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white disabled:opacity-30 border border-white/5 transition-colors">
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ── Scan Detail Modal ── */}
      {selectedScan && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-fade-in">
          <div className="relative w-full max-w-3xl glass-strong border border-white/10 rounded-2xl shadow-2xl max-h-[90vh] flex flex-col overflow-hidden"
            style={{ boxShadow: '0 25px 80px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.06)' }}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/5">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center">
                  <Eye className="w-4 h-4 text-sky-400" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">Inspection Details — Scan #{selectedScan.id}</h3>
                  <p className="text-xs text-slate-500">{selectedScan.product_name || 'Commodity Package'}</p>
                </div>
              </div>
              <button onClick={() => setSelectedScan(null)}
                className="p-1.5 rounded-lg text-slate-500 hover:text-white hover:bg-white/8 transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Rule Results */}
            <div className="flex-1 overflow-y-auto px-6 py-4 space-y-2.5">
              {selectedScan.compliance_result.results.map((r) => (
                <div key={r.rule_id}
                  className={`p-3.5 rounded-xl border text-xs transition-all ${
                    r.status === 'PASS' ? 'bg-emerald-950/15 border-emerald-500/20'
                      : r.status === 'WARNING' ? 'bg-amber-950/15 border-amber-500/20'
                      : 'bg-rose-950/15 border-rose-500/20'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      {r.status === 'PASS' && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}
                      {r.status === 'FAIL' && <XCircle className="w-3.5 h-3.5 text-rose-400" />}
                      {r.status === 'WARNING' && <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />}
                      <span className="font-bold text-slate-200">{r.rule_name}</span>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      r.status === 'PASS' ? 'bg-emerald-500/15 text-emerald-300'
                        : r.status === 'WARNING' ? 'bg-amber-500/15 text-amber-300'
                        : 'bg-rose-500/15 text-rose-300'
                    }`}>{r.status}</span>
                  </div>
                  <p className="text-slate-400 leading-relaxed">{r.reason}</p>
                  <p className="text-[10px] text-sky-500 mt-1.5 font-medium">{r.official_legal_reference || r.legal_reference}</p>
                </div>
              ))}
            </div>

            {/* Modal Actions */}
            <div className="px-6 py-4 border-t border-white/5 flex flex-wrap items-center justify-end gap-2.5">
              <button onClick={() => handleDownloadCsv(selectedScan.id)} disabled={actionInProgress === `csv-${selectedScan.id}`}
                className="btn-ghost !text-xs disabled:opacity-50">
                {actionInProgress === `csv-${selectedScan.id}` ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <FileCode2 className="w-3.5 h-3.5 text-indigo-400" />}
                CSV
              </button>
              <button onClick={() => handleDownloadExcel(selectedScan.id)} disabled={actionInProgress === `xlsx-${selectedScan.id}`}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-blue-500/15 hover:bg-blue-500/20 text-blue-300 text-xs font-semibold border border-blue-500/20 transition-all active:scale-95 disabled:opacity-50">
                {actionInProgress === `xlsx-${selectedScan.id}` ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <FileSpreadsheet className="w-3.5 h-3.5" />}
                Excel
              </button>
              <button onClick={() => handleDownloadPdf(selectedScan.id)} disabled={actionInProgress === `pdf-${selectedScan.id}`}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-white text-xs font-semibold shadow transition-all active:scale-95 disabled:opacity-50"
                style={{ background: 'linear-gradient(135deg, #0171c7, #4f46e5)' }}>
                {actionInProgress === `pdf-${selectedScan.id}` ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                Download PDF
              </button>
              <button onClick={() => handleDownloadDocx(selectedScan.id)} disabled={actionInProgress === `docx-${selectedScan.id}`}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-white text-xs font-bold shadow transition-all active:scale-95 disabled:opacity-50"
                style={{ background: 'linear-gradient(135deg, #dc2626, #d97706)' }}>
                {actionInProgress === `docx-${selectedScan.id}` ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <FileText className="w-3.5 h-3.5" />}
                Show-Cause Draft
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
