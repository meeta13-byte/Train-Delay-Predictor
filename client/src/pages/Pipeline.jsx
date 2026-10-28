import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api, useApi } from '../api.js';
import Mermaid from '../components/Mermaid.jsx';
import Plot from '../components/Plot.jsx';
import RunPipeline from '../components/RunPipeline.jsx';
import { Async, Card, DataTable, IconBlob, PageHead } from '../components/ui.jsx';
import { C, fmt } from '../theme.js';

const cols = (names) => names.map((n) => ({ key: n, label: n, num: false, render: (v) => (v == null ? <span className="muted">null</span> : String(v)) }));

function Step({ n, icon, title, sub, open = false, children }) {
  return (
    <details className="step" open={open}>
      <summary>
        <IconBlob icon={icon} small />
        <div>
          <div className="eyebrow" style={{ marginBottom: 0 }}>Step {n}</div>
          <h2 className="card-title">{title}</h2>
          {sub && <div className="card-sub">{sub}</div>}
        </div>
        <svg className="chev" width="18" height="18" viewBox="0 0 18 18" aria-hidden="true"><path d="M4 7l5 5 5-5" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" /></svg>
      </summary>
      <div className="step-body">{children}</div>
    </details>
  );
}

export default function Pipeline() {
  const state = useApi('pipeline', () => api.get('/api/pipeline'));
  return (
    <>
      <PageHead eyebrow="For the viva" title="Data pipeline">
        Every lab stage, from raw files to the SQL database. Open a step to see the data at that point.
      </PageHead>
      <Async state={state} skeleton={4}>{(d) => <Body d={d} reload={state.reload} />}</Async>
    </>
  );
}

function Body({ d, reload }) {
  const c = d.cleaning || {};
  const stats = c.delay_records_stats || {};
  const tables = ['trains', 'stations', 'routes', 'delay_records', 'delay_remarks'];
  const db = d.database;

  return (
    <div className="steps page-enter">
      <Step n={1} icon="files" title="Collection" sub="Structured CSV / JSON / XML and unstructured TXT" open>
        {d.files.filter((f) => f.structured).map((f) => (
          <div key={f.file}>
            <div className="row" style={{ marginBottom: 10 }}>
              <strong style={{ color: 'var(--text-strong)' }}>{f.file}</strong>
              <span className="chip indigo">{f.format}</span>
              <span className="chip good">Structured</span>
              <span className="small muted">{fmt.int(f.rows)} rows × {f.columns.length} columns · first 8 rows</span>
            </div>
            <DataTable rows={f.head} columns={cols(f.columns)} />
          </div>
        ))}
        {d.files.filter((f) => !f.structured).map((f) => (
          <div key={f.file}>
            <div className="row" style={{ marginBottom: 10 }}>
              <strong style={{ color: 'var(--text-strong)' }}>{f.file}</strong>
              <span className="chip indigo">{f.format}</span>
              <span className="chip warn">Unstructured</span>
              <span className="small muted">{f.rows} lines · fields pulled out with regular expressions</span>
            </div>
            <div className="grid grid-2">
              <pre className="code">{f.lines.map((l) => l.line).join('\n')}</pre>
              <DataTable
                rows={f.lines}
                columns={[
                  { key: 'train_no', label: 'train_no', render: (v, r) => (r.unparsed ? <span className="chip bad">unparsed</span> : v) },
                  { key: 'station_code', label: 'station' },
                  { key: 'delay_minutes', label: 'delay (min)', num: true },
                  { key: 'reason', label: 'reason' },
                ]}
              />
            </div>
          </div>
        ))}
      </Step>

      <Step n={2} icon="broom" title="Cleaning" sub="Missing values, duplicates, outliers and feature engineering">
        <div className="grid grid-4">
          {[['Missing delays imputed', stats.missing_imputed, 'train median'], ['Duplicates removed', stats.duplicates_removed, 'exact repeats'],
            [`Outliers dropped`, stats.outliers_dropped, `> ${fmt.int(stats.outlier_cap_minutes)} min`], ['Invalid rows dropped', stats.invalid_dropped, 'bad dates / keys']].map(([label, v, foot]) => (
            <div key={label} className="kpi"><div className="kpi-label">{label}</div><div className="kpi-value">{fmt.int(v)}</div><div className="kpi-foot">{foot}</div></div>
          ))}
        </div>
        <div className="grid grid-2">
          <Card title="Rows before and after cleaning">
            <Plot
              data={[
                { type: 'bar', name: 'Before', x: tables, y: tables.map((t) => c.before_counts?.[t] ?? 0), marker: { color: C.periwinkle, cornerradius: 6 } },
                { type: 'bar', name: 'After', x: tables, y: tables.map((t) => c.after_counts?.[t] ?? 0), marker: { color: C.indigo, cornerradius: 6 } },
              ]}
              layout={{ barmode: 'group', yaxis: { type: 'log', title: { text: 'Rows (log scale)' } } }}
              height={300}
            />
          </Card>
          <Card title="Cleaning report">
            <DataTable
              rows={tables.map((t) => ({ table: t, before: c.before_counts?.[t], after: c.after_counts?.[t], removed: (c.before_counts?.[t] ?? 0) - (c.after_counts?.[t] ?? 0) }))}
              columns={[
                { key: 'table', label: 'Table' },
                { key: 'before', label: 'Before', num: true, render: fmt.int },
                { key: 'after', label: 'After', num: true, render: fmt.int },
                { key: 'removed', label: 'Removed', num: true, render: fmt.int },
              ]}
            />
            <p className="small muted mt-16">Features added: year, month, day of week, weekend flag, season, fog season, delay category.</p>
            {c.remarks_unparsed?.length > 0 && <p className="small muted mt-8">Unparseable remark lines kept aside: {c.remarks_unparsed.length}</p>}
          </Card>
        </div>
      </Step>

      <Step n={3} icon="route" title="Relationships & cardinality" sub="Entity-relationship model with primary and foreign keys">
        <Mermaid chart={d.er_diagram} />
        <DataTable
          rows={d.relationships}
          columns={[
            { key: 'parent', label: 'Parent' }, { key: 'child', label: 'Child' }, { key: 'key', label: 'Key' },
            { key: 'cardinality', label: 'Cardinality', render: (v) => <span className="chip indigo">{v}</span> }, { key: 'meaning', label: 'Meaning' },
          ]}
        />
        <div className="row">
          <strong style={{ color: 'var(--text-strong)' }}>Orphan-record check</strong>
          {Object.entries(d.integrity).filter(([k]) => k.startsWith('orphan')).map(([k, v]) => (
            <span key={k} className={`chip ${v === 0 ? 'good' : 'warn'}`}>{k.replace('orphan_', '').replaceAll('_', ' ')}: {v}</span>
          ))}
        </div>
      </Step>

      <Step n={4} icon="database" title="Database" sub={`${db.type} via SQLAlchemy · ${db.url}`}>
        <div className="grid grid-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))' }}>
          {Object.entries(db.tables).map(([t, n]) => (
            <div key={t} className="kpi" style={{ minHeight: 0 }}><div className="kpi-label">{t}</div><div className="kpi-value" style={{ fontSize: 26 }}>{fmt.int(n)}</div></div>
          ))}
        </div>
        <SqlPlayground queries={d.queries} />
      </Step>

      <Step n={5} icon="chart" title="Downloads" sub="Cleaned Excel workbook, cleaned CSVs, reports and forecast">
        <DataTable
          rows={d.downloads}
          columns={[
            { key: 'name', label: 'File', render: (v, r) => <a href={`/api/download/${r.group}/${encodeURIComponent(v)}`} download>{v}</a> },
            { key: 'group', label: 'Folder', render: (v, r) => <span className="muted">{r.path.replace(`/${r.name}`, '')}</span> },
            { key: 'size_kb', label: 'Size', num: true, render: (v) => (v > 1024 ? `${(v / 1024).toFixed(1)} MB` : `${v} KB`) },
          ]}
        />
        <p className="small muted">Saved Matplotlib charts are on the <Link to="/lab-outputs">Lab Outputs</Link> page.</p>
      </Step>

      <Card title="Re-run the pipeline" sub="Runs python main.py: generate → ingest → clean → load → query → charts → forecast (about a minute)">
        <div className="mt-16" style={{ display: 'flex', justifyContent: 'center' }}>
          <RunPipeline label="Re-run pipeline" onDone={reload} showLog />
        </div>
      </Card>
    </div>
  );
}

function SqlPlayground({ queries }) {
  const [name, setName] = useState(queries[0]?.name);
  const [custom, setCustom] = useState('SELECT t.train_type, COUNT(*) AS trains\nFROM trains t\nGROUP BY t.train_type\nORDER BY trains DESC');
  const [mode, setMode] = useState('preset');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const preset = queries.find((q) => q.name === name);

  const run = async () => {
    setBusy(true);
    setError(null);
    try {
      setResult(mode === 'preset' ? await api.get(`/api/queries/${name}`) : await api.post('/api/sql', { sql: custom }));
    } catch (e) {
      setError(e.message);
      setResult(null);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card title="SQL playground" sub="Predefined queries from src/database/queries.py, or your own read-only SELECT">
      <div className="row mt-8" style={{ alignItems: 'end' }}>
        <label className="field" style={{ minWidth: 260, flex: 1 }}>
          <span>Query</span>
          <select className="select" value={mode === 'preset' ? name : '__custom'} onChange={(e) => {
            if (e.target.value === '__custom') setMode('custom');
            else { setMode('preset'); setName(e.target.value); }
            setResult(null);
          }}>
            {queries.map((q) => <option key={q.name} value={q.name}>{q.label}</option>)}
            <option value="__custom">Write my own SELECT…</option>
          </select>
        </label>
        <button type="button" className="btn btn-primary btn-small" onClick={run} disabled={busy}>{busy ? 'Running…' : 'Run query'}</button>
      </div>
      <div className="mt-16">
        {mode === 'preset' ? (
          <pre className="code" aria-label="SQL">{preset?.sql}</pre>
        ) : (
          <label className="field">
            <span>SELECT only. Opened read-only; max 500 rows.</span>
            <textarea className="textarea" value={custom} onChange={(e) => setCustom(e.target.value)} spellCheck={false} />
          </label>
        )}
      </div>
      <div className="mt-16" aria-live="polite">
        {error && <div className="callout accent" role="alert"><div><div className="callout-kind">Query refused</div>{error}</div></div>}
        {result && (
          <>
            <p className="small muted" style={{ marginBottom: 8 }}>{result.rows.length} row(s){result.truncated ? ' (first 500 shown)' : ''}</p>
            <DataTable rows={result.rows} columns={result.columns.map((k) => ({ key: k, label: k, num: typeof result.rows[0]?.[k] === 'number', render: (v) => (typeof v === 'number' && !Number.isInteger(v) ? v.toFixed(2) : v ?? '–') }))} />
          </>
        )}
      </div>
    </Card>
  );
}
