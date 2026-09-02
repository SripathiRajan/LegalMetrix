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
  FileSpreadsheet,
  ArrowUpRight,
  ArrowDownRight,
  Activity,
  Target
} from 'lucide-react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer, 
  CartesianGrid,
  Area,
  AreaChart,
  Cell
} from 'recharts';
import { statsApi, scanApi } from '../services/api';
import type { DashboardStatistics } from '../types/api';

const CustomTooltipStyle = {
  backgroundColor: '#080f1e',
  borderColor: 'rgba(255,255,255,0.08)',
  borderWidth: 1,
  borderStyle: 'solid',
  borderRadius: '10px',
  fontSize: '12px',
  color: '#f1f5f9',
  padding: '8px 12px',
};

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
    refetchInterval: 30000,
  });

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[500px] space-y-4">
        <div className="relative w-16 h-16">
          <div className="absolute inset-0 rounded-full border-2 border-sky-500/20" />
          <div className="absolute inset-0 rounded-full border-2 border-sky-500 border-t-transparent animate-spin" />
          <Activity className="absolute inset-0 m-auto w-6 h-6 text-sky-400" />
        </div>
        <div className="text-center space-y-1">
          <p className="text-sm font-semibold text-slate-200">Loading Compliance Analytics</p>
          <p className="text-xs text-slate-500">Fetching real-time audit metrics...</p>
        </div>
      </div>
    );
  }

  if (isError || !stats) {
    return (
      <div className="glass rounded-2xl p-10 text-center space-y-4 border border-rose-500/20 max-w-md mx-auto mt-16">
        <div className="w-14 h-14 rounded-2xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center mx-auto">
          <AlertOctagon className="w-7 h-7 text-rose-400" />
        </div>
        <div>
          <h3 className="text-lg font-bold text-white">Failed to Load Analytics</h3>
          <p className="text-xs text-slate-400 mt-1">Ensure you are logged in with valid officer credentials and the backend is running.</p>
        </div>
        <button onClick={() => refetch()} className="btn-primary mx-auto !text-xs">
          <RefreshCw className="w-3.5 h-3.5" /> Retry Connection
        </button>
      </div>
    );
  }

  const { summary, violation_rate_by_field, violation_trend_over_time, top_non_compliant_brands, authenticity_flag_rate, font_size_distribution } = stats;

  const fontSizeData = [
    { name: '< 8px', label: 'Non-compliant', count: font_size_distribution.less_than_8px, fill: '#ef4444' },
    { name: '8–12px', label: 'Small Pack', count: font_size_distribution.between_8_and_12px, fill: '#f59e0b' },
    { name: '12–24px', label: 'Standard', count: font_size_distribution.between_12_and_24px, fill: '#10b981' },
    { name: '> 24px', label: 'Headline', count: font_size_distribution.greater_than_24px, fill: '#6366f1' },
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

  const kpiCards = [
    {
      label: 'Total Scans Audited',
      value: summary.total_scans.toLocaleString(),
      sub: 'Persistent Records',
      icon: <FileCheck2 className="w-5 h-5" />,
      color: 'sky',
      gradient: 'from-sky-600 to-sky-800',
      trend: null,
    },
    {
      label: 'Overall Compliance Rate',
      value: `${summary.compliance_rate.toFixed(1)}%`,
      sub: `${summary.compliant_scans} Compliant`,
      icon: <Percent className="w-5 h-5" />,
      color: 'emerald',
      gradient: 'from-emerald-600 to-teal-700',
      trend: summary.compliance_rate >= 75 ? 'up' : 'down',
    },
    {
      label: 'Violations Detected',
      value: summary.non_compliant_scans.toLocaleString(),
      sub: 'Requiring Notice',
      icon: <ShieldAlert className="w-5 h-5" />,
      color: 'rose',
      gradient: 'from-rose-600 to-rose-800',
      trend: null,
    },
    {
      label: 'Average Compliance Score',
      value: `${summary.average_compliance_score.toFixed(1)}%`,
      sub: 'Weighted Rule Metric',
      icon: <TrendingUp className="w-5 h-5" />,
      color: 'indigo',
      gradient: 'from-indigo-600 to-violet-700',
      trend: summary.average_compliance_score >= 70 ? 'up' : 'down',
    },
    {
      label: 'Trade Dress Flag Rate',
      value: `${authenticity_flag_rate.suspicious_rate.toFixed(1)}%`,
      sub: `${authenticity_flag_rate.suspicious_count} of ${authenticity_flag_rate.total_checked}`,
      icon: <Sparkles className="w-5 h-5" />,
      color: 'amber',
      gradient: 'from-amber-600 to-orange-700',
      trend: null,
    },
  ];

  const colorVariants: Record<string, string> = {
    sky:     'bg-sky-500/10 border-sky-500/20 text-sky-400',
    emerald: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400',
    rose:    'bg-rose-500/10 border-rose-500/20 text-rose-400',
    indigo:  'bg-indigo-500/10 border-indigo-500/20 text-indigo-400',
    amber:   'bg-amber-500/10 border-amber-500/20 text-amber-400',
  };
  const textVariants: Record<string, string> = {
    sky: 'text-sky-300', emerald: 'text-emerald-300', rose: 'text-rose-300',
    indigo: 'text-indigo-300', amber: 'text-amber-300',
  };

  return (
    <div className="w-full max-w-7xl mx-auto space-y-7 animate-fade-in pb-16">

      {/* ── Page Header ── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-5 pb-5 border-b border-white/5">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, rgba(14,165,233,0.15), rgba(99,102,241,0.15))', border: '1px solid rgba(14,165,233,0.2)' }}
            >
              <BarChart3 className="w-5 h-5 text-sky-400" />
            </div>
            <h1 className="text-2xl font-bold text-white font-display tracking-tight">
              Compliance Analytics Dashboard
            </h1>
            <span className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-[11px] font-semibold">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Live
            </span>
          </div>
          <p className="text-xs text-slate-500 pl-11">
            Real-time inspection metrics · Auto-refreshes every 30 seconds
          </p>
        </div>

        {/* Controls */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Date Range */}
          <div className="flex items-center gap-2 glass rounded-xl p-2 border border-white/5">
            <Calendar className="w-3.5 h-3.5 text-slate-500 ml-1" />
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)}
              className="bg-transparent text-xs text-slate-300 focus:outline-none" />
            <span className="text-slate-600 text-xs">→</span>
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)}
              className="bg-transparent text-xs text-slate-300 focus:outline-none" />
            {(startDate || endDate) && (
              <button onClick={() => { setStartDate(''); setEndDate(''); }}
                className="px-2 py-0.5 rounded-md bg-white/5 hover:bg-white/10 text-slate-400 text-[11px] transition-colors ml-1">
                Clear
              </button>
            )}
          </div>

          <button
            onClick={handleBulkExport}
            disabled={isExporting}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/15 text-emerald-300 border border-emerald-500/20 text-xs font-semibold shadow transition-all active:scale-95 disabled:opacity-50"
          >
            {isExporting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <FileSpreadsheet className="w-3.5 h-3.5" />}
            Bulk Export (Excel)
          </button>
        </div>
      </div>

      {/* ── KPI Cards Row ── */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        {kpiCards.map((card, i) => (
          <div key={i}
            className={`relative glass rounded-2xl p-4 border overflow-hidden glass-hover ${colorVariants[card.color].split(' ')[1]}`}
            style={{ animationDelay: `${i * 60}ms` }}
          >
            {/* Background gradient blob */}
            <div className="absolute -top-6 -right-6 w-20 h-20 rounded-full opacity-[0.08] blur-xl"
              style={{ background: `radial-gradient(circle, currentColor, transparent)` }} />

            <div className={`w-8 h-8 rounded-xl border flex items-center justify-center mb-3 ${colorVariants[card.color]}`}>
              {card.icon}
            </div>
            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">{card.label}</p>
            <div className="flex items-baseline gap-2 mt-1">
              <span className={`text-2xl font-extrabold font-display ${textVariants[card.color]}`}>
                {card.value}
              </span>
              {card.trend && (
                card.trend === 'up'
                  ? <ArrowUpRight className="w-4 h-4 text-emerald-400" />
                  : <ArrowDownRight className="w-4 h-4 text-rose-400" />
              )}
            </div>
            <p className="text-[10px] text-slate-600 mt-1">{card.sub}</p>
          </div>
        ))}
      </div>

      {/* ── Charts Row 1 ── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Violation Rate Bar Chart */}
        <div className="lg:col-span-7 glass rounded-2xl border border-white/5 p-5">
          <div className="flex items-center justify-between mb-5 pb-4 border-b border-white/5">
            <div>
              <h3 className="text-sm font-bold text-slate-100 font-display">Violation Rate by Declaration Field</h3>
              <p className="text-xs text-slate-500 mt-0.5">Compliance rules evaluation by field</p>
            </div>
            <span className="px-2.5 py-1 rounded-lg bg-rose-500/10 text-rose-300 text-[11px] font-semibold border border-rose-500/20">
              % Violation
            </span>
          </div>
          <div className="h-[280px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={violation_rate_by_field} layout="vertical" margin={{ left: 16, right: 20, top: 4, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" opacity={1} horizontal={false} />
                <XAxis type="number" unit="%" stroke="#475569" fontSize={11} tickLine={false} axisLine={false} domain={[0, 100]} />
                <YAxis dataKey="declaration_name" type="category" stroke="#475569" fontSize={10} width={120} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={CustomTooltipStyle} formatter={(v: any) => [`${v}%`, 'Violation Rate']} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
                <Bar dataKey="violation_rate" radius={[0, 6, 6, 0]} background={{ fill: 'rgba(255,255,255,0.02)', radius: 6 }}>
                  {violation_rate_by_field.map((_entry, idx) => (
                    <Cell key={idx} fill={`url(#barGrad-${idx % 3})`} />
                  ))}
                </Bar>
                <defs>
                  <linearGradient id="barGrad-0" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stopColor="#ef4444" /><stop offset="100%" stopColor="#f97316" /></linearGradient>
                  <linearGradient id="barGrad-1" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stopColor="#dc2626" /><stop offset="100%" stopColor="#ef4444" /></linearGradient>
                  <linearGradient id="barGrad-2" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stopColor="#f97316" /><stop offset="100%" stopColor="#ef4444" /></linearGradient>
                </defs>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Compliance Trend Line Chart */}
        <div className="lg:col-span-5 glass rounded-2xl border border-white/5 p-5">
          <div className="flex items-center justify-between mb-5 pb-4 border-b border-white/5">
            <div>
              <h3 className="text-sm font-bold text-slate-100 font-display">Compliance Trend</h3>
              <p className="text-xs text-slate-500 mt-0.5">Daily audit performance</p>
            </div>
            <span className="px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-300 text-[11px] font-semibold border border-emerald-500/20">
              Daily
            </span>
          </div>
          <div className="h-[280px] w-full">
            {violation_trend_over_time.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center gap-3">
                <Target className="w-10 h-10 text-slate-700" />
                <p className="text-slate-500 text-xs">No time-series data available yet</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={violation_trend_over_time} margin={{ top: 4, right: 8, left: -16, bottom: 4 }}>
                  <defs>
                    <linearGradient id="complianceGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#10b981" stopOpacity={0.2} />
                      <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="date" stroke="#475569" fontSize={10} tickLine={false} axisLine={false} />
                  <YAxis unit="%" stroke="#475569" fontSize={10} domain={[0, 100]} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={CustomTooltipStyle} cursor={{ stroke: 'rgba(16,185,129,0.3)', strokeWidth: 1 }} />
                  <Area type="monotone" dataKey="compliance_rate" stroke="#10b981" strokeWidth={2.5} fill="url(#complianceGrad)" dot={{ r: 4, fill: '#10b981', strokeWidth: 2, stroke: '#080f1e' }} activeDot={{ r: 6, fill: '#10b981' }} />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* ── Charts Row 2 ── */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-5">
        {/* Top Non-Compliant Brands */}
        <div className="md:col-span-6 glass rounded-2xl border border-white/5 p-5">
          <div className="pb-4 border-b border-white/5 mb-4">
            <h3 className="text-sm font-bold text-slate-100 font-display">Top Non-Compliant Brands</h3>
            <p className="text-xs text-slate-500 mt-0.5">Brands with highest violation rates</p>
          </div>
          <div className="overflow-x-auto">
            {top_non_compliant_brands.length === 0 ? (
              <div className="py-12 text-center">
                <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto mb-3">
                  <ShieldAlert className="w-6 h-6 text-emerald-400" />
                </div>
                <p className="text-slate-500 text-xs">No brand violations recorded — great compliance!</p>
              </div>
            ) : (
              <table className="w-full text-left text-xs data-table">
                <thead>
                  <tr className="text-slate-500 text-[11px] font-semibold uppercase tracking-wider">
                    <th className="py-2.5 pr-4">Brand</th>
                    <th className="py-2.5 pr-4">Scans</th>
                    <th className="py-2.5 pr-4">Violation Rate</th>
                    <th className="py-2.5">Common Issue</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/4">
                  {top_non_compliant_brands.map((b, i) => (
                    <tr key={b.brand_name} className="transition-colors">
                      <td className="py-3 pr-4">
                        <div className="flex items-center gap-2">
                          <span className="w-5 h-5 rounded-md bg-white/5 text-slate-400 text-[10px] font-bold flex items-center justify-center">{i + 1}</span>
                          <span className="font-bold text-slate-100">{b.brand_name}</span>
                        </div>
                      </td>
                      <td className="py-3 pr-4 text-slate-400">{b.total_scans}</td>
                      <td className="py-3 pr-4">
                        <div className="space-y-1">
                          <div className="flex items-center gap-1.5">
                            <span className="font-bold text-rose-300">{b.non_compliance_rate}%</span>
                            <span className="text-slate-600">({b.non_compliant_scans})</span>
                          </div>
                          <div className="progress-bar w-20">
                            <div className="progress-bar-fill" style={{ width: `${b.non_compliance_rate}%`, background: 'linear-gradient(90deg, #ef4444, #f97316)' }} />
                          </div>
                        </div>
                      </td>
                      <td className="py-3 text-slate-400 font-mono text-[10px]">{b.most_common_violation}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Font Size Readability Distribution */}
        <div className="md:col-span-6 glass rounded-2xl border border-white/5 p-5">
          <div className="flex items-center justify-between pb-4 border-b border-white/5 mb-4">
            <div className="flex items-center gap-2.5">
              <Type className="w-4 h-4 text-indigo-400" />
              <div>
                <h3 className="text-sm font-bold text-slate-100 font-display">Font Size Distribution</h3>
                <p className="text-xs text-slate-500 mt-0.5">Rule 9 Readability Compliance</p>
              </div>
            </div>
            <span className="text-[11px] text-slate-500 font-mono">{font_size_distribution.total_measured} samples</span>
          </div>

          {/* Legend */}
          <div className="grid grid-cols-2 gap-2 mb-4">
            {fontSizeData.map(d => (
              <div key={d.name} className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/3 border border-white/5">
                <div className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ backgroundColor: d.fill }} />
                <div className="min-w-0">
                  <p className="text-[11px] font-semibold text-slate-300 truncate">{d.name}</p>
                  <p className="text-[10px] text-slate-600">{d.label} · {d.count}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="h-[160px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={fontSizeData} margin={{ top: 4, right: 8, left: -20, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
                <XAxis dataKey="name" stroke="#475569" fontSize={10} tickLine={false} axisLine={false} />
                <YAxis stroke="#475569" fontSize={10} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={CustomTooltipStyle} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
                <Bar dataKey="count" radius={[6, 6, 2, 2]}>
                  {fontSizeData.map((d, idx) => (
                    <Cell key={idx} fill={d.fill} fillOpacity={0.85} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* ── Footer ── */}
      <div className="flex items-center justify-center pt-2">
        <div className="inline-flex items-center gap-2.5 px-5 py-2.5 rounded-full glass border border-white/5 text-xs text-slate-500">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          Powered by LegalMetrix AI · Compliance Verification System
        </div>
      </div>
    </div>
  );
};
