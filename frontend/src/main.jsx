import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { AlertTriangle, Check, Database, FileUp, Filter, Lock, RotateCcw, X } from 'lucide-react';
import './styles.css';

const API = import.meta.env.VITE_API_BASE || '/api';
const TENANT = 'acme-industrial';

function formatKg(value) {
  const number = Number(value || 0);
  if (number >= 1000) return `${(number / 1000).toFixed(1)} tCO2e`;
  return `${number.toFixed(1)} kgCO2e`;
}

function statusLabel(status) {
  return status.replaceAll('_', ' ');
}

async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, options);
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || 'Request failed');
  }
  return response.json();
}

function App() {
  const [summary, setSummary] = useState(null);
  const [activities, setActivities] = useState([]);
  const [sources, setSources] = useState([]);
  const [batches, setBatches] = useState([]);
  const [filter, setFilter] = useState({ status: '', source_type: '', flagged: false });
  const [selected, setSelected] = useState(null);
  const [uploadState, setUploadState] = useState({ source_type: 'sap', file: null, busy: false, message: '' });
  const [error, setError] = useState('');

  const query = useMemo(() => {
    const params = new URLSearchParams({ tenant: TENANT });
    if (filter.status) params.set('status', filter.status);
    if (filter.source_type) params.set('source_type', filter.source_type);
    if (filter.flagged) params.set('flagged', 'true');
    return params.toString();
  }, [filter]);

  async function load() {
    const [summaryData, activityData, sourceData, batchData] = await Promise.all([
      request(`/summary/?tenant=${TENANT}`),
      request(`/activities/?${query}`),
      request('/sources/'),
      request('/batches/'),
    ]);
    setSummary(summaryData);
    setActivities(activityData.results || activityData);
    setSources(sourceData.results || sourceData);
    setBatches(batchData.results || batchData);
  }

  useEffect(() => {
    load().catch((exc) => setError(exc.message));
  }, [query]);

  async function upload(event) {
    event.preventDefault();
    if (!uploadState.file) return;
    setUploadState((state) => ({ ...state, busy: true, message: '' }));
    const body = new FormData();
    body.append('tenant', TENANT);
    body.append('source_type', uploadState.source_type);
    body.append('file', uploadState.file);
    try {
      const batch = await request('/upload/', { method: 'POST', body });
      setUploadState((state) => ({ ...state, busy: false, file: null, message: `Ingested ${batch.row_count} rows from ${batch.file_name}` }));
      await load();
    } catch (exc) {
      setUploadState((state) => ({ ...state, busy: false, message: exc.message }));
    }
  }

  async function act(activity, action, note = '') {
    const updated = await request(`/activities/${activity.id}/${action}/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ note }),
    });
    setSelected(updated);
    await load();
  }

  async function saveSelected() {
    const updated = await request(`/activities/${selected.id}/`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        description: selected.description,
        normalized_quantity: selected.normalized_quantity,
        emission_factor: selected.emission_factor,
        analyst_notes: selected.analyst_notes,
        flags: selected.flags,
      }),
    });
    setSelected(updated);
    await load();
  }

  return (
    <main>
      <header className="topbar">
        <div className="brand-row">
          <div className="logo-mark" aria-label="Breathe ESG logo">
            <span>B</span>
          </div>
          <div>
            <p className="wordmark">Breathe ESG</p>
            <h1>Emissions ingestion review</h1>
            <p className="eyebrow">ACME Industrial</p>
          </div>
        </div>
        <div className="status-pill"><Database size={16} /> {summary?.rows || 0} normalized rows</div>
      </header>

      {error && <div className="notice error">{error}</div>}

      <section className="metrics">
        <div><span>Total</span><strong>{formatKg(summary?.total_co2e_kg)}</strong></div>
        <div><span>Needs review</span><strong>{summary?.pending_rows || 0}</strong></div>
        <div><span>Flagged</span><strong>{summary?.flagged_rows || 0}</strong></div>
        <div><span>Sources</span><strong>{summary?.by_source?.length || 0}</strong></div>
      </section>

      <section className="workspace">
        <aside className="panel">
          <form className="upload" onSubmit={upload}>
            <div className="panel-title"><FileUp size={18} /> Ingest source file</div>
            <select value={uploadState.source_type} onChange={(event) => setUploadState({ ...uploadState, source_type: event.target.value })}>
              {sources.map((source) => <option key={source.id} value={source.source_type}>{source.source_type_label}</option>)}
            </select>
            <input type="file" accept=".csv" onChange={(event) => setUploadState({ ...uploadState, file: event.target.files[0] })} />
            <button disabled={uploadState.busy || !uploadState.file}>{uploadState.busy ? 'Ingesting...' : 'Upload CSV'}</button>
            {uploadState.message && <p className="muted">{uploadState.message}</p>}
          </form>

          <div className="filters">
            <div className="panel-title"><Filter size={18} /> Review queue</div>
            <select value={filter.status} onChange={(event) => setFilter({ ...filter, status: event.target.value })}>
              <option value="">All statuses</option>
              <option value="needs_review">Needs review</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="locked">Locked</option>
            </select>
            <select value={filter.source_type} onChange={(event) => setFilter({ ...filter, source_type: event.target.value })}>
              <option value="">All sources</option>
              <option value="sap">SAP</option>
              <option value="utility">Utility</option>
              <option value="travel">Travel</option>
            </select>
            <label className="checkline">
              <input type="checkbox" checked={filter.flagged} onChange={(event) => setFilter({ ...filter, flagged: event.target.checked })} />
              Flagged rows only
            </label>
            <button type="button" className="secondary" onClick={() => setFilter({ status: '', source_type: '', flagged: false })}><RotateCcw size={16} /> Reset</button>
          </div>

          <div className="batches">
            <div className="panel-title">Recent batches</div>
            {batches.slice(0, 5).map((batch) => (
              <div className="batch" key={batch.id}>
                <strong>{batch.file_name}</strong>
                <span>{batch.source_name} - {batch.row_count} rows - {batch.status}</span>
              </div>
            ))}
          </div>
        </aside>

        <section className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Source</th>
                <th>Facility</th>
                <th>Category</th>
                <th>Quantity</th>
                <th>CO2e</th>
                <th>Status</th>
                <th>Flags</th>
              </tr>
            </thead>
            <tbody>
              {activities.map((activity) => (
                <tr key={activity.id} onClick={() => setSelected(activity)} className={selected?.id === activity.id ? 'active' : ''}>
                  <td>{activity.activity_date}</td>
                  <td>{activity.source_name}</td>
                  <td>{activity.facility_code || 'Unknown'}</td>
                  <td>{activity.category}</td>
                  <td>{activity.normalized_quantity} {activity.normalized_unit}</td>
                  <td>{formatKg(activity.co2e_kg)}</td>
                  <td><span className={`tag ${activity.status}`}>{statusLabel(activity.status)}</span></td>
                  <td>{activity.flags.length ? <AlertTriangle size={16} className="warn" /> : 'Clear'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <aside className="drawer">
          {selected ? (
            <>
              <div className="drawer-head">
                <div>
                  <p className="eyebrow">{selected.source_reference || selected.source_name}</p>
                  <h2>{selected.description}</h2>
                </div>
                <span className={`tag ${selected.status}`}>{statusLabel(selected.status)}</span>
              </div>
              <label>Description<input value={selected.description} onChange={(event) => setSelected({ ...selected, description: event.target.value })} /></label>
              <div className="split">
                <label>Quantity<input value={selected.normalized_quantity} onChange={(event) => setSelected({ ...selected, normalized_quantity: event.target.value })} /></label>
                <label>Factor<input value={selected.emission_factor} onChange={(event) => setSelected({ ...selected, emission_factor: event.target.value })} /></label>
              </div>
              <label>Analyst notes<textarea value={selected.analyst_notes || ''} onChange={(event) => setSelected({ ...selected, analyst_notes: event.target.value })} /></label>
              <div className="flags">
                {(selected.flags || []).map((flag) => <span key={flag}><AlertTriangle size={13} /> {flag}</span>)}
                {!selected.flags?.length && <span>no flags</span>}
              </div>
              <div className="actions">
                <button className="secondary" onClick={saveSelected}>Save edit</button>
                <button onClick={() => act(selected, 'approve', selected.analyst_notes)}><Check size={16} /> Approve</button>
                <button className="danger" onClick={() => act(selected, 'reject', selected.analyst_notes)}><X size={16} /> Reject</button>
                <button className="secondary" onClick={() => act(selected, 'lock')}><Lock size={16} /> Lock</button>
              </div>
              <details>
                <summary>Raw source row</summary>
                <pre>{JSON.stringify(selected.raw_payload, null, 2)}</pre>
              </details>
              <details>
                <summary>Audit trail</summary>
                {(selected.audit_events || []).map((event) => (
                  <p key={event.id} className="audit">{event.created_at} - {event.action} - {event.note}</p>
                ))}
              </details>
            </>
          ) : (
            <div className="empty">Select a row to inspect normalization, source payload, and audit history.</div>
          )}
        </aside>
      </section>
    </main>
  );
}

createRoot(document.getElementById('root')).render(<App />);
