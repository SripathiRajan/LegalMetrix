import React, { useState } from 'react';
import type { AnalyzeScanResponse } from '../types/api';
import { scanApi } from '../services/api';

interface LiveResultsViewLightProps {
  result: AnalyzeScanResponse;
  originalImageSrc: string;
  onReset: () => void;
}

export const LiveResultsViewLight: React.FC<LiveResultsViewLightProps> = ({ result, originalImageSrc, onReset }) => {
  const { compliance_result, scan_id } = result;
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);

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
    if (!scan_id) { alert('Report unavailable for unsaved scans.'); return; }
    try {
      setActionInProgress('pdf');
      const blob = await scanApi.downloadPdfBlob(scan_id);
      downloadFile(blob, `Compliance_Report_${scan_id}.pdf`);
    } catch { alert('Failed to download PDF.'); }
    finally { setActionInProgress(null); }
  };

  const passCount = compliance_result.results.filter(r => r.status === 'PASS').length;
  const failCount = compliance_result.results.filter(r => r.status === 'FAIL').length;
  const warnCount = compliance_result.results.filter(r => r.status === 'WARNING').length;

  return (
    <div style={{ marginTop: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h3 style={{ margin: 0, color: 'var(--brand)', fontFamily: 'var(--font-serif)', fontSize: '20px' }}>Compliance Results</h3>
        <button className="btn" onClick={onReset}>New Scan</button>
      </div>

      <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
        <div style={{ flex: '1 1 300px', background: 'var(--paper)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '16px' }}>
          <img src={originalImageSrc} style={{ width: '100%', borderRadius: '4px', objectFit: 'contain', maxHeight: '300px', backgroundColor: '#f9f9f9' }} alt="Scanned product" />
          <div style={{ marginTop: '16px', display: 'flex', gap: '8px' }}>
            <button className="btn btn-primary" style={{ flex: 1 }} onClick={handleDownloadPdf} disabled={!!actionInProgress}>
              {actionInProgress === 'pdf' ? 'Generating...' : 'Export PDF'}
            </button>
          </div>
        </div>
        
        <div style={{ flex: '2 1 400px' }}>
          <div style={{ display: 'flex', gap: '16px', marginBottom: '16px' }}>
            <div style={{ flex: 1, padding: '16px', background: 'var(--paper)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', textAlign: 'center' }}>
              <div style={{ fontSize: '14px', color: 'var(--text-sec)', marginBottom: '4px' }}>Score</div>
              <div style={{ fontSize: '32px', color: 'var(--brand)', fontWeight: 600 }}>{compliance_result.compliance_score.toFixed(0)}%</div>
            </div>
            <div style={{ flex: 1, padding: '16px', background: 'var(--paper)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', textAlign: 'center' }}>
              <div style={{ fontSize: '14px', color: 'var(--text-sec)', marginBottom: '4px' }}>Passed</div>
              <div style={{ fontSize: '32px', color: 'var(--green)', fontWeight: 600 }}>{passCount}</div>
            </div>
            <div style={{ flex: 1, padding: '16px', background: 'var(--paper)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', textAlign: 'center' }}>
              <div style={{ fontSize: '14px', color: 'var(--text-sec)', marginBottom: '4px' }}>Violations</div>
              <div style={{ fontSize: '32px', color: 'var(--red)', fontWeight: 600 }}>{failCount + warnCount}</div>
            </div>
          </div>

          <div style={{ background: 'var(--paper)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '14px' }}>
              <thead>
                <tr style={{ background: '#f5f5f5', borderBottom: '1px solid var(--border)' }}>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>Rule</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>Status</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>Evidence</th>
                </tr>
              </thead>
              <tbody>
                {compliance_result.results.map((r, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td style={{ padding: '12px 16px' }}>
                      <div style={{ fontWeight: 500 }}>{r.rule_name}</div>
                      <div style={{ fontSize: '12px', color: 'var(--text-sec)', marginTop: '4px' }}>{r.reason}</div>
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      {r.status === 'PASS' && <span style={{ color: 'var(--green)', fontWeight: 500 }}>PASS</span>}
                      {r.status === 'FAIL' && <span style={{ color: 'var(--red)', fontWeight: 500 }}>FAIL</span>}
                      {r.status === 'WARNING' && <span style={{ color: '#d97706', fontWeight: 500 }}>WARN</span>}
                    </td>
                    <td style={{ padding: '12px 16px', fontSize: '13px' }}>
                      {r.detected_value || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
