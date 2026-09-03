import React, { useState, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '../context/AuthContext';
import { scanApi, statsApi, chatApi } from '../services/api';
import type { AnalyzeScanResponse, DashboardStatistics, ScanRecord } from '../types/api';
import { LiveResultsViewLight } from './LiveResultsViewLight';

interface OfficerPortalProps {
  onOpenAuth: () => void;
}

export const OfficerPortal: React.FC<OfficerPortalProps> = ({ onOpenAuth }) => {
  const [activeView, setActiveView] = useState<'scan' | 'dash' | 'audit' | 'assist'>('scan');
  const [segment, setSegment] = useState<'physical' | 'ecom'>('physical');
  const { user, logout, isAuthenticated } = useAuth();

  // --- Scan & Inspect State ---
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [previewUrls, setPreviewUrls] = useState<string[]>([]);
  const [useEnsemble, setUseEnsemble] = useState(true);
  const [strategy, setStrategy] = useState<string>('standard');
  const [brandName, setBrandName] = useState<string>('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [scanResult, setScanResult] = useState<AnalyzeScanResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // --- Chat Assistant State ---
  const [chatInput, setChatInput] = useState('');
  const [chatMessages, setChatMessages] = useState<Array<{role: 'user'|'assistant', text: string, cite?: string}>>([
    { role: 'assistant', text: 'Namaste. Ask me about a specific rule, an MRP format question, or net quantity requirements, and I\'ll answer with the exact clause behind it.' }
  ]);
  const [isSendingChat, setIsSendingChat] = useState(false);

  // --- Dashboard Data ---
  const { data: stats } = useQuery<DashboardStatistics>({
    queryKey: ['dashboardStats'],
    queryFn: () => statsApi.getDashboardStats({}),
    refetchInterval: 60000,
    enabled: activeView === 'dash',
  });

  // --- Audit History Data ---
  const { data: auditData } = useQuery<{total: number, scans: ScanRecord[]}>({
    queryKey: ['auditHistory'],
    queryFn: () => scanApi.getScans({ limit: 50 }),
    enabled: activeView === 'audit',
  });

  const handleSendChat = async (presetText?: string) => {
    const text = presetText || chatInput;
    if (!text.trim()) return;
    
    setChatInput('');
    setChatMessages(prev => [...prev, { role: 'user', text }]);
    setIsSendingChat(true);

    try {
      const response = await chatApi.sendMessage({ message: text, context: scanResult ? { scan_id: scanResult.scan_id } : undefined });
      setChatMessages(prev => [...prev, { 
        role: 'assistant', 
        text: response.reply, 
        cite: response.citations?.[0]?.official_legal_reference 
      }]);
    } catch {
      setChatMessages(prev => [...prev, { role: 'assistant', text: 'Error connecting to the DoCA Legal Assistant. Please try again.' }]);
    } finally {
      setIsSendingChat(false);
    }
  };

  const addFiles = (newFiles: File[]) => {
    if (newFiles.length === 0) return;
    const urls = newFiles.map((f) => URL.createObjectURL(f));
    setSelectedFiles((prev) => [...prev, ...newFiles]);
    setPreviewUrls((prev) => [...prev, ...urls]);
    setError(null);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      addFiles(Array.from(e.target.files));
    }
  };

  const clearFiles = () => {
    setSelectedFiles([]);
    setPreviewUrls([]);
    setScanResult(null);
  };

  const handleScan = async () => {
    if (selectedFiles.length === 0) {
      setError('Please select at least one image to scan.');
      return;
    }
    try {
      setIsAnalyzing(true);
      setError(null);
      const result = await scanApi.analyzeImage(selectedFiles, {
        use_ensemble: useEnsemble,
        preprocessing_strategy: strategy,
        brand_name: brandName,
        input_type: segment === 'physical' ? 'physical_package' : 'ecommerce_listing',
      });
      setScanResult(result);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'An error occurred during analysis.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="app-container active" id="officer-app">
      <header className="officer-header">
        <div className="officer-header-inner">
          <div className="brand">
            <div className="seal">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#F5ECD8" strokeWidth="1.8"><path d="M12 3v18M5 7l-3 6a4 4 0 0 0 8 0l-3-6M19 7l-3 6a4 4 0 0 0 8 0l-3-6M5 7h14M3 21h18"/></svg>
            </div>
            <div className="brand-text">
              <div className="name">Legal<em>Metrix</em><span className="act-tag">PCR 2011</span></div>
              <div className="tag">Dept. of Consumer Affairs · Compliance Engine</div>
            </div>
          </div>
          <nav className="officer-nav">
            <button className={activeView === 'scan' ? 'active' : ''} onClick={() => setActiveView('scan')}>Scan &amp; Inspect</button>
            <button className={activeView === 'dash' ? 'active' : ''} onClick={() => setActiveView('dash')}>Dashboard</button>
            <button className={activeView === 'audit' ? 'active' : ''} onClick={() => setActiveView('audit')}>Audit History</button>
            <button className={activeView === 'assist' ? 'active' : ''} onClick={() => setActiveView('assist')}>Assistant</button>
          </nav>
          {isAuthenticated && user ? (
            <button className="officer-login" onClick={logout} title="Click to logout">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
              {user.badge_number || user.username}
            </button>
          ) : (
            <button className="officer-login" onClick={onOpenAuth}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4M10 17l5-5-5-5M15 12H3"/></svg>
              Officer Login
            </button>
          )}
        </div>
      </header>

      {/* SCAN & INSPECT */}
      <section className={`officer-view ${activeView === 'scan' ? 'active' : ''}`} id="ov-scan">
        <div className="scan-hero">
          <div className="eyebrow-line">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 16.8l-6.2 4.5 2.4-7.4L2 9.4h7.6z"/></svg>
            Upload 2 or more panels for higher accuracy
          </div>
          <h1>Statutory compliance inspection scanner</h1>
          <p>Upload photos of a product's front, back or side panels. LegalMetrix reads every declared field and checks it against the Legal Metrology (Packaged Commodities) Rules, 2011.</p>
        </div>

        {!scanResult && (
          <div className="segmented">
            <button className={segment === 'physical' ? 'active' : ''} onClick={() => setSegment('physical')}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>
              Physical package
            </button>
            <button className={segment === 'ecom' ? 'active' : ''} onClick={() => setSegment('ecom')}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M6 2l1.5 5M18 2l-1.5 5M2.5 7h19l-1.6 10.6A2 2 0 0 1 17.9 19H6.1a2 2 0 0 1-2-1.4L2.5 7z"/></svg>
              E-commerce listing
            </button>
          </div>
        )}

        {scanResult ? (
          <LiveResultsViewLight 
            result={scanResult} 
            originalImageSrc={previewUrls[0] || ''} 
            onReset={clearFiles}
          />
        ) : (
          <div className="scan-grid">
            {segment === 'physical' && (
              <div className="dropzone" id="dz-physical" onDrop={(e) => { e.preventDefault(); handleFileChange({ target: { files: e.dataTransfer.files } } as any); }} onDragOver={(e) => e.preventDefault()}>
                <input type="file" multiple accept="image/*" className="hidden" style={{ display: 'none' }} ref={fileInputRef} onChange={handleFileChange} />
                <div className="up-icon">
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#1F3A5F" strokeWidth="2"><path d="M12 16V4M6 10l6-6 6 6M4 20h16"/></svg>
                </div>
                <h3>Drop package images here</h3>
                <p>Front, back and side panels at once · JPG, PNG, WEBP</p>
                {previewUrls.length > 0 && <div style={{display: 'flex', gap: '8px', overflowX: 'auto', marginBottom: '16px', justifyContent: 'center'}}>
                  {previewUrls.map((url, i) => <img key={i} src={url} style={{height: '60px', borderRadius: '4px'}} alt="preview" />)}
                </div>}
                <div className="dz-actions">
                  <button className="btn btn-primary" onClick={() => fileInputRef.current?.click()}>Browse files</button>
                  <button className="btn" onClick={clearFiles}>Clear</button>
                </div>
              </div>
            )}

            {segment === 'ecom' && (
              <div className="dropzone" id="dz-ecom" onDrop={(e) => { e.preventDefault(); handleFileChange({ target: { files: e.dataTransfer.files } } as any); }} onDragOver={(e) => e.preventDefault()}>
                <input type="file" multiple accept="image/*" className="hidden" style={{ display: 'none' }} ref={fileInputRef} onChange={handleFileChange} />
                <div className="up-icon">
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#1F3A5F" strokeWidth="2"><path d="M12 16V4M6 10l6-6 6 6M4 20h16"/></svg>
                </div>
                <h3>Drop listing screenshots here</h3>
                <p>Product page, specification table or carousel images</p>
                {previewUrls.length > 0 && <div style={{display: 'flex', gap: '8px', overflowX: 'auto', marginBottom: '16px', justifyContent: 'center'}}>
                  {previewUrls.map((url, i) => <img key={i} src={url} style={{height: '60px', borderRadius: '4px'}} alt="preview" />)}
                </div>}
                <div className="dz-actions">
                  <button className="btn btn-primary" onClick={() => fileInputRef.current?.click()}>Browse files</button>
                  <button className="btn" onClick={clearFiles}>Clear</button>
                </div>
              </div>
            )}

            <div className="panel">
              <h4>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#1F3A5F" strokeWidth="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
                Inspection parameters
              </h4>
              <div className="field">
                <div className="field-row">
                  <div>
                    <div className="field-label">OCR ensemble</div>
                    <div className="field-desc">Cross-checks three OCR engines and merges overlapping text regions for a single confident reading.</div>
                  </div>
                  <label className="switch"><input type="checkbox" checked={useEnsemble} onChange={(e) => setUseEnsemble(e.target.checked)} /><span className="slider-track"></span></label>
                </div>
              </div>
              <div className="field">
                <div className="field-label" style={{ marginBottom: '8px' }}>Image preprocessing</div>
                <select value={strategy} onChange={(e) => setStrategy(e.target.value)}>
                  <option value="standard">Standard (adaptive contrast)</option>
                  <option value="high_contrast">High contrast — glare suppression</option>
                  <option value="denoise">Denoise — curved packaging</option>
                  <option value="binarize">Fine print — binarization</option>
                </select>
              </div>
              <div className="field">
                <div className="field-label" style={{ marginBottom: '8px' }}>Brand authenticity check</div>
                <input className="textinput" placeholder="e.g. Amul, Fortune, Parle-G (optional)" value={brandName} onChange={(e) => setBrandName(e.target.value)} />
                <div className="hint">Compares the package against registered trade-dress references for that brand.</div>
              </div>
              {error && <div style={{ color: 'var(--red)', fontSize: '12px', marginTop: '10px' }}>{error}</div>}
              <button className="btn btn-gold btn-full" onClick={handleScan} disabled={isAnalyzing} style={{ opacity: isAnalyzing ? 0.7 : 1 }}>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2"><path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11z"/></svg>
                {isAnalyzing ? 'Analyzing...' : 'Run compliance check'}
              </button>
            </div>
          </div>
        )}
      </section>

      {/* OFFICER DASHBOARD */}
      <section className={`officer-view ${activeView === 'dash' ? 'active' : ''}`} id="ov-dash">
        <div className="view-header">
          <div>
            <h2>Today's inspections</h2>
            <p>Your scans and outcomes for Coimbatore Zone III.</p>
          </div>
        </div>
        {stats ? (
          <>
            <div className="kpi-row">
              <div className="kpi-card">
                <div className="kpi-label">Scans completed</div>
                <div className="kpi-value">{stats.summary.total_scans}</div>
                <div className="kpi-delta delta-up">Live Data</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">Violations flagged</div>
                <div className="kpi-value">{stats.summary.non_compliant_scans}</div>
                <div className="kpi-delta delta-down">{stats.summary.total_scans ? Math.round((stats.summary.non_compliant_scans / stats.summary.total_scans) * 100) : 0}% of scans</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">Compliant</div>
                <div className="kpi-value">{stats.summary.compliant_scans}</div>
                <div className="kpi-delta delta-up">{stats.summary.compliance_rate.toFixed(1)}% of scans</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">Avg. scan time</div>
                <div className="kpi-value">4.2s</div>
                <div className="kpi-delta delta-up">−1.1s vs last week</div>
              </div>
            </div>
            <div className="chart-card">
              <h4>Violations by rule, this week</h4>
              {stats.violation_rate_by_field.map((stat, index) => {
                const totalViolations = stats.violation_rate_by_field.reduce((a, b) => a + b.violation_count, 0) || 1;
                const percentage = Math.round((stat.violation_count / totalViolations) * 100);
                return (
                  <div className="bar-row" key={stat.rule_id}>
                    <div className="bar-label">{stat.declaration_name}</div>
                    <div className="bar-track">
                      <div className={`bar-fill ${index % 2 === 0 ? 'gold' : ''}`} style={{ width: `${percentage}%` }}></div>
                    </div>
                    <div className="bar-value">{stat.violation_count}</div>
                  </div>
                );
              })}
            </div>
          </>
        ) : (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-sec)' }}>Loading dashboard statistics...</div>
        )}
      </section>

      {/* AUDIT HISTORY */}
      <section className={`officer-view ${activeView === 'audit' ? 'active' : ''}`} id="ov-audit">
        <div className="view-header">
          <div>
            <h2>Inspection audit history</h2>
            <p>Verification records and downloadable DoCA citations.</p>
          </div>
          <div className="toolbar">
            <input className="search-input" placeholder="Search product or brand…" />
            <select className="filter-select"><option>All statuses</option><option>Compliant</option><option>Non-compliant</option><option>Pending review</option></select>
            <button className="btn"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>Export</button>
          </div>
        </div>
        <table>
          <thead><tr><th>Inspection ID</th><th>Product / brand</th><th>Channel</th><th>Date</th><th>Result</th><th></th></tr></thead>
          <tbody>
            {auditData ? auditData.scans.map((scan) => (
              <tr key={scan.id}>
                <td className="id-mono">INS-{scan.id.toString().substring(0,6).toUpperCase()}</td>
                <td>{scan.product_name || 'Unknown'}<div className="time">{scan.authenticity_result?.brand_name || '-'}</div></td>
                <td>{scan.compliance_result?.input_type === 'physical_package' ? 'Physical' : 'E-commerce'}</td>
                <td>{new Date(scan.created_at).toLocaleDateString()}<div className="time">{new Date(scan.created_at).toLocaleTimeString()}</div></td>
                <td>
                  {scan.overall_status === 'COMPLIANT' && <span className="badge badge-green">● Compliant</span>}
                  {scan.overall_status === 'POTENTIALLY_NON_COMPLIANT' && <span className="badge badge-amber">● Pending review</span>}
                  {scan.overall_status === 'NON_COMPLIANT' && <span className="badge badge-red">● Non-compliant</span>}
                </td>
                <td>
                  <button className="link-btn" onClick={async (e) => {
                    e.preventDefault();
                    if (!scan.id) return;
                    const blob = await scanApi.downloadPdfBlob(scan.id);
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `Report_${scan.id}.pdf`;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                  }}>View report</button>
                </td>
              </tr>
            )) : (
              <tr><td colSpan={6} style={{ textAlign: 'center', padding: '24px' }}>Loading audit history...</td></tr>
            )}
          </tbody>
        </table>
      </section>

      {/* ASSISTANT */}
      <section className={`officer-view ${activeView === 'assist' ? 'active' : ''}`} id="ov-assist">
        <div className="view-header">
          <div>
            <h2>Legal assistant</h2>
            <p>Answers grounded in the PCR 2011 text and official DoCA gazettes.</p>
          </div>
        </div>
        <div className="chat-shell">
          <div className="chat-top">
            <div className="chat-avatar"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#F5ECD8" strokeWidth="2"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4M8 16h.01M16 16h.01"/></svg></div>
            <div><div className="t1">DoCA legal metrology assistant</div><div className="t2">Grounded in PCR 2011 · gazette notices · your audit records</div></div>
            <span className="grounded-pill">Grounded answers only</span>
          </div>
          <div className="chat-body">
            {chatMessages.map((msg, idx) => (
              <div className="msg" key={idx} style={{ flexDirection: msg.role === 'user' ? 'row-reverse' : 'row' }}>
                <div className="chat-avatar" style={{ background: msg.role === 'user' ? 'var(--brand)' : '' }}>
                  {msg.role === 'user' ? (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                  ) : (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#F5ECD8" strokeWidth="2"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/></svg>
                  )}
                </div>
                <div className="msg-bubble" style={{ background: msg.role === 'user' ? '#f0f4f8' : '', border: msg.role === 'user' ? '1px solid #d9e2ec' : '' }}>
                  <p>{msg.text}</p>
                  {msg.cite && <span className="cite">{msg.cite}</span>}
                </div>
              </div>
            ))}
            {isSendingChat && (
              <div className="msg">
                <div className="chat-avatar"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#F5ECD8" strokeWidth="2"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/></svg></div>
                <div className="msg-bubble"><p style={{ color: 'var(--text-sec)' }}>Thinking...</p></div>
              </div>
            )}
          </div>
          <div className="prompt-row">
            <div className="prompt-chip" onClick={() => handleSendChat("What is Rule 6(1)(e) on MRP format?")}>What is Rule 6(1)(e) on MRP format?</div>
            <div className="prompt-chip" onClick={() => handleSendChat("SOP for edible oil net quantity checks")}>SOP for edible oil net quantity checks</div>
            <div className="prompt-chip" onClick={() => handleSendChat("Penalty for a repeat violation")}>Penalty for a repeat violation</div>
          </div>
          <div className="chat-input-row">
            <input 
              placeholder="Ask about Rule 6(1), MRP, net quantity, or audit statistics…" 
              value={chatInput} 
              onChange={e => setChatInput(e.target.value)} 
              onKeyDown={e => { if (e.key === 'Enter') handleSendChat(); }}
            />
            <button className="send-btn" onClick={() => handleSendChat()} disabled={isSendingChat}>
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/></svg>
            </button>
          </div>
        </div>
      </section>
    </div>
  );
};
