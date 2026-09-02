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
  X
} from 'lucide-react';
import { scanApi } from '../services/api';
import type { ScanRecord } from '../types/api';

export const ScanHistoryView: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [page, setPage] = useState(0);
  const [selectedScan, setSelectedScan] = useState<ScanRecord | null>(null);
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

  const handleDownloadPdf = async (scanId: number) => {
    try {
      const blob = await scanApi.downloadPdfBlob(scanId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `LegalMetrology_Report_Scan_${scanId}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch {
      alert('Failed to download PDF report. Ensure backend service is running.');
    }
  };

  return (
    <div className="w-full max-w-6xl mx-auto space-y-6 animate-fade-in pb-12">
      {/* Title & Filters */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center space-x-2">
            <History className="w-5 h-5 text-brand-400" />
            <h1 className="text-2xl font-bold text-white font-display">
              Inspection Audit History
            </h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Historical package compliance verification records and downloadable DoCA PDF citations.
          </p>
        </div>

        {/* Filter Controls */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Search Box */}
          <div className="relative">
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setPage(0);
              }}
              placeholder="Search product or brand..."
              className="bg-slate-900 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-brand-500"
            />
            <Search className="absolute left-2.5 top-2 w-3.5 h-3.5 text-slate-500" />
          </div>

          {/* Status Dropdown */}
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(0);
            }}
            className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-brand-500"
          >
            <option value="">All Statuses</option>
            <option value="COMPLIANT">Compliant</option>
            <option value="NON_COMPLIANT">Non-Compliant</option>
            <option value="POTENTIALLY_NON_COMPLIANT">Potentially Non-Compliant</option>
          </select>
        </div>
      </div>

      {/* History Table */}
      <div className="glass-panel rounded-2xl overflow-hidden border border-slate-800">
        {isLoading ? (
          <div className="py-16 text-center">
            <RefreshCw className="w-8 h-8 text-brand-400 animate-spin mx-auto mb-2" />
            <p className="text-xs text-slate-400">Loading audit scans...</p>
          </div>
        ) : !data || data.scans.length === 0 ? (
          <div className="py-16 text-center text-slate-500 text-xs">
            No inspection records found matching the current filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/90 text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Scan ID</th>
                  <th className="py-3 px-4">Product Name</th>
                  <th className="py-3 px-4">Overall Status</th>
                  <th className="py-3 px-4">Score</th>
                  <th className="py-3 px-4">Authenticity</th>
                  <th className="py-3 px-4">Date & Time</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {data.scans.map((scan) => {
                  const isPass = scan.overall_status === 'COMPLIANT';
                  const isWarning = scan.overall_status === 'POTENTIALLY_NON_COMPLIANT';
                  return (
                    <tr key={scan.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-3.5 px-4 font-mono font-bold text-slate-300">
                        #{scan.id}
                      </td>
                      <td className="py-3.5 px-4 font-semibold text-white">
                        {scan.product_name || 'Commodity Package'}
                      </td>
                      <td className="py-3.5 px-4">
                        <span
                          className={`inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full font-bold text-[11px] ${
                            isPass
                              ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                              : isWarning
                              ? 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
                              : 'bg-rose-500/15 text-rose-300 border border-rose-500/30'
                          }`}
                        >
                          {isPass && <CheckCircle2 className="w-3 h-3 mr-1" />}
                          {!isPass && !isWarning && <XCircle className="w-3 h-3 mr-1" />}
                          {isWarning && <AlertTriangle className="w-3 h-3 mr-1" />}
                          <span>{scan.overall_status.replace(/_/g, ' ')}</span>
                        </span>
                      </td>
                      <td className="py-3.5 px-4 font-mono font-bold text-slate-200">
                        {scan.compliance_score.toFixed(0)}%
                      </td>
                      <td className="py-3.5 px-4">
                        {scan.authenticity_result ? (
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                              scan.authenticity_result.verdict === 'GENUINE_LIKELY'
                                ? 'bg-emerald-500/20 text-emerald-300'
                                : scan.authenticity_result.verdict === 'SUSPICIOUS'
                                ? 'bg-rose-500/20 text-rose-300'
                                : 'bg-slate-800 text-slate-400'
                            }`}
                          >
                            {scan.authenticity_result.verdict.replace(/_/g, ' ')}
                          </span>
                        ) : (
                          <span className="text-slate-600 text-[11px]">N/A</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-slate-400">
                        {new Date(scan.created_at).toLocaleString('en-IN', {
                          day: '2-digit',
                          month: 'short',
                          year: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end space-x-2">
                          <button
                            onClick={() => setSelectedScan(scan)}
                            title="Inspect Declarations"
                            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleDownloadPdf(scan.id)}
                            title="Download PDF Report"
                            className="p-1.5 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 transition-colors"
                          >
                            <Download className="w-3.5 h-3.5" />
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

        {/* Pagination Bar */}
        {data && data.total > pageSize && (
          <div className="p-4 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400 bg-slate-900/60">
            <span>
              Showing {page * pageSize + 1} - {Math.min((page + 1) * pageSize, data.total)} of {data.total} records
            </span>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-200"
              >
                Previous
              </button>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={(page + 1) * pageSize >= data.total}
                className="px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-200"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Detail Modal */}
      {selectedScan && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="relative w-full max-w-2xl glass-panel bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div>
                <h3 className="text-base font-bold text-white font-display">
                  Inspection Details (Scan #{selectedScan.id})
                </h3>
                <p className="text-xs text-slate-400">{selectedScan.product_name}</p>
              </div>
              <button
                onClick={() => setSelectedScan(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="my-4 overflow-y-auto space-y-3 flex-1 pr-1">
              {selectedScan.compliance_result.results.map((r) => (
                <div key={r.rule_id} className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs">
                  <div className="flex items-center justify-between font-semibold">
                    <span className="text-slate-200">{r.rule_name}</span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] ${
                        r.status === 'PASS'
                          ? 'bg-emerald-500/20 text-emerald-300'
                          : r.status === 'WARNING'
                          ? 'bg-amber-500/20 text-amber-300'
                          : 'bg-rose-500/20 text-rose-300'
                      }`}
                    >
                      {r.status}
                    </span>
                  </div>
                  <p className="text-slate-400 mt-1">{r.reason}</p>
                  <p className="text-[10px] text-brand-300 mt-1">{r.official_legal_reference || r.legal_reference}</p>
                </div>
              ))}
            </div>

            <div className="pt-3 border-t border-slate-800 flex justify-end space-x-3">
              <button
                onClick={() => handleDownloadPdf(selectedScan.id)}
                className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center space-x-1.5"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download Official PDF</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
