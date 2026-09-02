import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { 
  BarChart3, 
  TrendingUp, 
  ShieldAlert, 
  Percent, 
  FileCheck2, 
  Calendar, 
  RefreshCw, 
  AlertOctagon,
  Sparkles,
  Type,
  FileSpreadsheet
} from 'lucide-react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  CartesianGrid
} from 'recharts';
import { statsApi, scanApi } from '../services/api';
import type { DashboardStatistics } from '../types/api';

export const DashboardView: React.FC = () => {
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [isExporting, setIsExporting] = useState<boolean>(false);

  const { data: stats, isLoading, refetch, isError } = useQuery<DashboardStatistics>({
    queryKey: ['dashboardStats', startDate, endDate],
    queryFn: () => statsApi.getDashboardStats({
      start_date: startDate || undefined,
      end_date: endDate || undefined,
    }),
    refetchInterval: 30000, // auto refresh every 30s
  });

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-3">
        <RefreshCw className="w-8 h-8 text-brand-400 animate-spin" />
        <p className="text-sm text-slate-400 font-medium">Loading Department Compliance Analytics...</p>
      </div>
    );
  }

  if (isError || !stats) {
    return (
      <div className="glass-panel rounded-2xl p-8 text-center space-y-3 border-rose-500/30">
        <AlertOctagon className="w-10 h-10 text-rose-400 mx-auto" />
        <h3 className="text-lg font-bold text-white">Failed to Load Dashboard Statistics</h3>
        <p className="text-xs text-slate-400">
          Ensure you are logged in with valid officer credentials and backend is running.
        </p>
        <button
          onClick={() => refetch()}
          className="px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold"
        >
          Retry
        </button>
      </div>
    );
  }

  const { summary, violation_rate_by_field, violation_trend_over_time, top_non_compliant_brands, authenticity_flag_rate, font_size_distribution } = stats;

  // Prepare font size distribution data
  const fontSizeData = [
    { name: '< 8px (Non-compliant)', count: font_size_distribution.less_than_8px, fill: '#ef4444' },
    { name: '8 - 12px (Small Pack)', count: font_size_distribution.between_8_and_12px, fill: '#f59e0b' },
    { name: '12 - 24px (Standard)', count: font_size_distribution.between_12_and_24px, fill: '#10b981' },
    { name: '> 24px (Headline)', count: font_size_distribution.greater_than_24px, fill: '#6366f1' },
  ];

  const handleBulkExport = async () => {
    try {
      setIsExporting(true);
      const blob = await scanApi.downloadBulkXlsxBlob({ limit: 1000 });
      const timestamp = new Date().toISOString().slice(0, 10);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `LegalMetrology_Compliance_Analytics_Export_${timestamp}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch {
      alert('Failed to download bulk scans Excel workbook.');
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="w-full max-w-7xl mx-auto space-y-6 animate-fade-in pb-12">
      {/* Header & Date Filters */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center space-x-2">
            <BarChart3 className="w-5 h-5 text-brand-400" />
            <h1 className="text-2xl font-bold text-white font-display">
              Legal Metrology Compliance Analytics
            </h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real-time statutory inspection metrics aggregated from persistent scan repository.
          </p>
        </div>

        {/* Action Controls: Date Filters & Bulk Export */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Date Filter Inputs */}
          <div className="flex items-center space-x-2 bg-slate-900/80 p-2 rounded-xl border border-slate-800 text-xs">
            <div className="flex items-center space-x-1.5">
              <Calendar className="w-3.5 h-3.5 text-slate-400" />
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-slate-200 focus:outline-none focus:border-brand-500"
              />
            </div>
            <span className="text-slate-500">to</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-slate-200 focus:outline-none focus:border-brand-500"
            />
            {(startDate || endDate) && (
              <button
                onClick={() => {
                  setStartDate('');
                  setEndDate('');
                }}
                className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px]"
              >
                Clear
              </button>
            )}
          </div>

          {/* Bulk Export Button */}
          <button
            onClick={handleBulkExport}
            disabled={isExporting}
            className="flex items-center space-x-1.5 px-3.5 py-2.5 rounded-xl bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 text-xs font-semibold shadow transition-all active:scale-95 disabled:opacity-50"
            title="Download all historical scans into a formatted Excel workbook"
          >
            {isExporting ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
            )}
            <span>Bulk Export (Excel)</span>
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Total Scans */}
        <div className="p-4 rounded-xl glass-panel border border-slate-800 flex flex-col justify-between">
          <span className="text-xs font-semibold text-slate-400">Total Scans Audited</span>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl font-extrabold text-white font-display">
              {summary.total_scans}
            </span>
            <FileCheck2 className="w-4 h-4 text-brand-400" />
          </div>
          <span className="text-[10px] text-slate-500 mt-1">Persistent Records</span>
        </div>

        {/* Compliance Rate */}
        <div className="p-4 rounded-xl glass-panel border border-emerald-500/20 bg-emerald-950/10 flex flex-col justify-between">
          <span className="text-xs font-semibold text-emerald-300">Overall Compliance Rate</span>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl font-extrabold text-emerald-400 font-display">
              {summary.compliance_rate.toFixed(1)}%
            </span>
            <Percent className="w-4 h-4 text-emerald-400" />
          </div>
          <span className="text-[10px] text-emerald-500/70 mt-1">
            {summary.compliant_scans} Compliant Packages
          </span>
        </div>

        {/* Non-Compliant Packages */}
        <div className="p-4 rounded-xl glass-panel border border-rose-500/20 bg-rose-950/10 flex flex-col justify-between">
          <span className="text-xs font-semibold text-rose-300">Violations Detected</span>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl font-extrabold text-rose-400 font-display">
              {summary.non_compliant_scans}
            </span>
            <ShieldAlert className="w-4 h-4 text-rose-400" />
          </div>
          <span className="text-[10px] text-rose-500/70 mt-1">Requiring Department Notice</span>
        </div>

        {/* Average Compliance Score */}
        <div className="p-4 rounded-xl glass-panel border border-indigo-500/20 bg-indigo-950/10 flex flex-col justify-between">
          <span className="text-xs font-semibold text-indigo-300">Average Score</span>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl font-extrabold text-indigo-400 font-display">
              {summary.average_compliance_score.toFixed(1)}%
            </span>
            <TrendingUp className="w-4 h-4 text-indigo-400" />
          </div>
          <span className="text-[10px] text-indigo-500/70 mt-1">Weighted Rule Metric</span>
        </div>

        {/* Authenticity Flag Rate */}
        <div className="p-4 rounded-xl glass-panel border border-amber-500/20 bg-amber-950/10 flex flex-col justify-between col-span-2 lg:col-span-1">
          <span className="text-xs font-semibold text-amber-300">Trade Dress Flag Rate</span>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl font-extrabold text-amber-400 font-display">
              {authenticity_flag_rate.suspicious_rate.toFixed(1)}%
            </span>
            <Sparkles className="w-4 h-4 text-amber-400" />
          </div>
          <span className="text-[10px] text-amber-500/70 mt-1">
            {authenticity_flag_rate.suspicious_count} Suspicious of {authenticity_flag_rate.total_checked}
          </span>
        </div>
      </div>

      {/* Main Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Violation Rate by Field Bar Chart */}
        <div className="lg:col-span-7 glass-panel rounded-2xl p-5 flex flex-col space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <h3 className="text-sm font-bold text-slate-100 font-display">
              Statutory Violation Rate by Declaration Field
            </h3>
            <span className="text-[11px] text-slate-400 font-mono">PCR 2011 Rules</span>
          </div>

          <div className="h-[280px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={violation_rate_by_field} layout="vertical" margin={{ left: 20, right: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                <XAxis type="number" unit="%" stroke="#94a3b8" fontSize={11} domain={[0, 100]} />
                <YAxis dataKey="declaration_name" type="category" stroke="#94a3b8" fontSize={11} width={130} />
                <Tooltip
                  formatter={(value: any) => [`${value}%`, 'Violation Rate']}
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                />
                <Bar dataKey="violation_rate" fill="#ef4444" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Violation Trend Over Time Line Chart */}
        <div className="lg:col-span-5 glass-panel rounded-2xl p-5 flex flex-col space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <h3 className="text-sm font-bold text-slate-100 font-display">
              Compliance Trend Over Time
            </h3>
            <span className="text-[11px] text-emerald-400 font-medium">Daily Audits</span>
          </div>

          <div className="h-[280px] w-full">
            {violation_trend_over_time.length === 0 ? (
              <div className="h-full flex items-center justify-center text-slate-500 text-xs">
                No time-series audit records available.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={violation_trend_over_time}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                  <XAxis dataKey="date" stroke="#94a3b8" fontSize={10} />
                  <YAxis unit="%" stroke="#94a3b8" fontSize={11} domain={[0, 100]} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                  />
                  <Line type="monotone" dataKey="compliance_rate" stroke="#10b981" strokeWidth={2.5} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* Secondary Visualizations Grid */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
        {/* Top Non-Compliant Brands */}
        <div className="md:col-span-6 glass-panel rounded-2xl p-5 flex flex-col space-y-3">
          <h3 className="text-sm font-bold text-slate-100 font-display pb-2 border-b border-slate-800">
            Top Non-Compliant Brands
          </h3>

          <div className="overflow-x-auto">
            {top_non_compliant_brands.length === 0 ? (
              <div className="py-8 text-center text-slate-500 text-xs">
                No brand violations recorded.
              </div>
            ) : (
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="text-slate-400 border-b border-slate-800 pb-2">
                    <th className="py-2">Brand</th>
                    <th className="py-2">Scans</th>
                    <th className="py-2">Violations</th>
                    <th className="py-2">Common Violation</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {top_non_compliant_brands.map((b) => (
                    <tr key={b.brand_name} className="hover:bg-slate-800/30">
                      <td className="py-2.5 font-bold text-slate-200">{b.brand_name}</td>
                      <td className="py-2.5 text-slate-400">{b.total_scans}</td>
                      <td className="py-2.5">
                        <span className="px-2 py-0.5 rounded bg-rose-500/10 text-rose-300 font-semibold">
                          {b.non_compliance_rate}% ({b.non_compliant_scans})
                        </span>
                      </td>
                      <td className="py-2.5 text-slate-400 font-mono text-[11px]">{b.most_common_violation}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Font Size Readability Distribution */}
        <div className="md:col-span-6 glass-panel rounded-2xl p-5 flex flex-col space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <div className="flex items-center space-x-2">
              <Type className="w-4 h-4 text-indigo-400" />
              <h3 className="text-sm font-bold text-slate-100 font-display">
                Font Size Readability Metric (Rule 9)
              </h3>
            </div>
            <span className="text-[11px] text-slate-400">
              {font_size_distribution.total_measured} Samples
            </span>
          </div>

          <div className="h-[200px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={fontSizeData} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                <XAxis dataKey="name" stroke="#94a3b8" fontSize={10} angle={-15} textAnchor="end" />
                <YAxis stroke="#94a3b8" fontSize={11} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                />
                <Bar dataKey="count" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
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
