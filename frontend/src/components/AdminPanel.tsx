import React, { useState } from 'react';

export const AdminPanel: React.FC = () => {
  const [activePage, setActivePage] = useState<'overview' | 'records' | 'officers' | 'rules' | 'settings'>('overview');

  return (
    <div className="app-container-flex active" id="admin-app">
      <aside className="admin-sidebar">
        <div className="admin-brand">
          <div className="seal">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#F5ECD8" strokeWidth="1.8"><path d="M12 3v18M5 7l-3 6a4 4 0 0 0 8 0l-3-6M19 7l-3 6a4 4 0 0 0 8 0l-3-6M5 7h14M3 21h18"/></svg>
          </div>
          <div><div className="name">LegalMetrix</div><div className="tag">Admin Console</div></div>
        </div>
        
        <div className="admin-nav">
          <div className="admin-nav-group">
            <div className="admin-nav-title">Monitor</div>
            <button className={activePage === 'overview' ? 'active' : ''} onClick={() => setActivePage('overview')}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/><rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/></svg>
              Overview
            </button>
            <button className={activePage === 'records' ? 'active' : ''} onClick={() => setActivePage('records')}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>
              Inspection records
            </button>
          </div>
          <div className="admin-nav-group">
            <div className="admin-nav-title">Manage</div>
            <button className={activePage === 'officers' ? 'active' : ''} onClick={() => setActivePage('officers')}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>
              Officers
            </button>
            <button className={activePage === 'rules' ? 'active' : ''} onClick={() => setActivePage('rules')}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
              Rules database
            </button>
            <button className={activePage === 'settings' ? 'active' : ''} onClick={() => setActivePage('settings')}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
              System settings
            </button>
          </div>
        </div>
        
        <div className="admin-foot">
          <div className="admin-avatar">RS</div>
          <div><div className="u1">R. Subramaniam</div><div className="u2">State Nodal Officer</div></div>
        </div>
      </aside>

      <main className="admin-main">
        <div className="admin-topbar">
          <div>
            <h2>Compliance overview</h2>
            <div className="sub">Tamil Nadu · all districts</div>
          </div>
          <div className="admin-filters">
            <select className="filter-select"><option>All districts</option><option>Coimbatore</option><option>Chennai</option><option>Madurai</option></select>
            <select className="filter-select"><option>Last 7 days</option><option>Last 30 days</option><option>This quarter</option></select>
          </div>
        </div>

        <div className="admin-content">
          {/* OVERVIEW */}
          <div className={`admin-page ${activePage === 'overview' ? 'active' : ''}`} id="ap-overview">
            <div className="kpi-row admin">
              <div className="kpi-card admin"><div className="kpi-label">Total scans</div><div className="kpi-value">3,842</div><div className="kpi-delta delta-up">+412 this week</div></div>
              <div className="kpi-card admin"><div className="kpi-label">Violations found</div><div className="kpi-value">915</div><div className="kpi-delta delta-down">23.8% rate</div></div>
              <div className="kpi-card admin"><div className="kpi-label">Compliance rate</div><div className="kpi-value">76.2%</div><div className="kpi-delta delta-up">+1.4 pts</div></div>
              <div className="kpi-card admin"><div className="kpi-label">Active officers</div><div className="kpi-value">58</div><div className="kpi-delta delta-up">across 12 districts</div></div>
            </div>

            <div className="two-col">
              <div className="chart-card">
                <h4>Violations by rule, statewide</h4>
                <div className="bar-row"><div className="bar-label">MRP declaration — 6(1)(f)</div><div className="bar-track"><div className="bar-fill" style={{ width: '85%' }}></div></div><div className="bar-value">312</div></div>
                <div className="bar-row"><div className="bar-label">Net quantity — 6(1)(b)</div><div className="bar-track"><div className="bar-fill gold" style={{ width: '62%' }}></div></div><div className="bar-value">228</div></div>
                <div className="bar-row"><div className="bar-label">Manufacturer address — 6(1)(a)</div><div className="bar-track"><div className="bar-fill" style={{ width: '48%' }}></div></div><div className="bar-value">176</div></div>
                <div className="bar-row"><div className="bar-label">Consumer care detail — 6(8)</div><div className="bar-track"><div className="bar-fill gold" style={{ width: '33%' }}></div></div><div className="bar-value">121</div></div>
                <div className="bar-row"><div className="bar-label">Date of manufacture — 6(1)(c)</div><div className="bar-track"><div className="bar-fill" style={{ width: '21%' }}></div></div><div className="bar-value">78</div></div>
              </div>
              <div className="chart-card">
                <div className="section-title">Top officers this week</div>
                <div className="section-sub">Ranked by inspections completed</div>
                <div className="officer-row"><div className="off-avatar">AK</div><div><div className="off-name">A. Kumaresan</div><div className="off-meta">Coimbatore Zone I</div></div><div className="off-count"><div className="n">91</div><div className="l">scans</div></div></div>
                <div className="officer-row"><div className="off-avatar">SP</div><div><div className="off-name">S. Priyanka</div><div className="off-meta">Chennai Zone IV</div></div><div className="off-count"><div className="n">84</div><div className="l">scans</div></div></div>
                <div className="officer-row"><div className="off-avatar">RS</div><div><div className="off-name">R. Subramaniam</div><div className="off-meta">Coimbatore Zone III</div></div><div className="off-count"><div className="n">77</div><div className="l">scans</div></div></div>
                <div className="officer-row"><div className="off-avatar">VM</div><div><div className="off-name">V. Meenakshi</div><div className="off-meta">Madurai Zone II</div></div><div className="off-count"><div className="n">69</div><div className="l">scans</div></div></div>
              </div>
            </div>
          </div>

          {/* RECORDS */}
          <div className={`admin-page ${activePage === 'records' ? 'active' : ''}`} id="ap-records">
            <div className="view-header" style={{ marginBottom: '18px' }}>
              <div><h2 style={{ fontSize: '19px' }}>Inspection records</h2><p>All scans logged across the state, with officer and outcome.</p></div>
              <div className="toolbar">
                <input className="search-input" placeholder="Search product, brand or officer…" />
                <button className="btn"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>Export Excel</button>
              </div>
            </div>
            <table>
              <thead><tr><th>Inspection ID</th><th>Product / brand</th><th>Officer</th><th>District</th><th>Result</th><th></th></tr></thead>
              <tbody>
                <tr><td className="id-mono">INS-24081</td><td>Fortune Sunflower Oil, 1L</td><td>R. Subramaniam</td><td>Coimbatore</td><td><span className="badge badge-green">● Compliant</span></td><td><a className="link-btn" href="#">View</a></td></tr>
                <tr><td className="id-mono">INS-24080</td><td>Parle-G Biscuits, 200g</td><td>S. Priyanka</td><td>Chennai</td><td><span className="badge badge-red">● Non-compliant</span></td><td><a className="link-btn" href="#">View</a></td></tr>
                <tr><td className="id-mono">INS-24079</td><td>Amul Butter, 500g</td><td>A. Kumaresan</td><td>Coimbatore</td><td><span className="badge badge-green">● Compliant</span></td><td><a className="link-btn" href="#">View</a></td></tr>
                <tr><td className="id-mono">INS-24078</td><td>Local Brand Namkeen, 400g</td><td>V. Meenakshi</td><td>Madurai</td><td><span className="badge badge-amber">● Pending review</span></td><td><a className="link-btn" href="#">View</a></td></tr>
                <tr><td className="id-mono">INS-24077</td><td>Tata Salt, 1kg</td><td>R. Subramaniam</td><td>Coimbatore</td><td><span className="badge badge-green">● Compliant</span></td><td><a className="link-btn" href="#">View</a></td></tr>
              </tbody>
            </table>
          </div>

          {/* OFFICERS */}
          <div className={`admin-page ${activePage === 'officers' ? 'active' : ''}`} id="ap-officers">
            <div className="view-header" style={{ marginBottom: '18px' }}>
              <div><h2 style={{ fontSize: '19px' }}>Officers</h2><p>Field inspectors with scanner access, by district.</p></div>
              <button className="btn btn-primary">+ Add officer</button>
            </div>
            <table>
              <thead><tr><th>Officer</th><th>District / zone</th><th>Scans (30d)</th><th>Status</th><th></th></tr></thead>
              <tbody>
                <tr><td>A. Kumaresan</td><td>Coimbatore Zone I</td><td>91</td><td><span className="status-dot dot-green"></span>Active</td><td><a className="link-btn" href="#">Manage</a></td></tr>
                <tr><td>S. Priyanka</td><td>Chennai Zone IV</td><td>84</td><td><span className="status-dot dot-green"></span>Active</td><td><a className="link-btn" href="#">Manage</a></td></tr>
                <tr><td>R. Subramaniam</td><td>Coimbatore Zone III</td><td>77</td><td><span className="status-dot dot-green"></span>Active</td><td><a className="link-btn" href="#">Manage</a></td></tr>
                <tr><td>V. Meenakshi</td><td>Madurai Zone II</td><td>69</td><td><span className="status-dot dot-amber"></span>On leave</td><td><a className="link-btn" href="#">Manage</a></td></tr>
              </tbody>
            </table>
          </div>

          {/* RULES DB */}
          <div className={`admin-page ${activePage === 'rules' ? 'active' : ''}`} id="ap-rules">
            <div className="view-header" style={{ marginBottom: '18px' }}>
              <div><h2 style={{ fontSize: '19px' }}>Rules database</h2><p>Gazette notifications and clause references used to ground the assistant and the scanner.</p></div>
              <button className="btn btn-primary">+ Add gazette notice</button>
            </div>
            <table>
              <thead><tr><th>Clause</th><th>Subject</th><th>Last updated</th><th>Source</th><th></th></tr></thead>
              <tbody>
                <tr><td className="mono">6(1)(e)</td><td>MRP declaration format</td><td>14 Jan 2025</td><td>Gazette No. 221</td><td><a className="link-btn" href="#">Edit</a></td></tr>
                <tr><td className="mono">6(1)(b)</td><td>Net quantity declaration</td><td>3 Nov 2024</td><td>Gazette No. 198</td><td><a className="link-btn" href="#">Edit</a></td></tr>
                <tr><td className="mono">6(1)(a)</td><td>Manufacturer / packer address</td><td>3 Nov 2024</td><td>Gazette No. 198</td><td><a className="link-btn" href="#">Edit</a></td></tr>
                <tr><td className="mono">6(8)</td><td>Consumer care detail</td><td>19 Aug 2024</td><td>Gazette No. 176</td><td><a className="link-btn" href="#">Edit</a></td></tr>
              </tbody>
            </table>
          </div>

          {/* SETTINGS */}
          <div className={`admin-page ${activePage === 'settings' ? 'active' : ''}`} id="ap-settings">
            <div className="view-header" style={{ marginBottom: '6px' }}><div><h2 style={{ fontSize: '19px' }}>System settings</h2><p>Engine defaults applied across every officer's scan.</p></div></div>
            <div className="panel">
              <div className="settings-row">
                <div><div className="settings-title">OCR ensemble by default</div><div className="settings-desc">New scans start with all three OCR engines enabled. Officers can turn this off for a faster, single-engine read.</div></div>
                <label className="switch"><input type="checkbox" defaultChecked /><span className="slider-track"></span></label>
              </div>
              <div className="settings-row">
                <div><div className="settings-title">Require brand authenticity check</div><div className="settings-desc">Blocks a scan from completing until a registered brand name is entered.</div></div>
                <label className="switch"><input type="checkbox" /><span className="slider-track"></span></label>
              </div>
              <div className="settings-row">
                <div><div className="settings-title">Auto-flag for review below confidence threshold</div><div className="settings-desc">Scans where OCR confidence falls under the threshold are routed to a senior officer instead of auto-closing.</div></div>
                <select className="filter-select"><option>85% confidence</option><option>90% confidence</option><option>95% confidence</option></select>
              </div>
              <div className="settings-row">
                <div><div className="settings-title">Assistant grounding source</div><div className="settings-desc">Which documents the Legal Assistant is allowed to cite from when answering officers.</div></div>
                <select className="filter-select"><option>PCR 2011 + gazettes</option><option>PCR 2011 only</option><option>PCR 2011 + gazettes + state circulars</option></select>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};
