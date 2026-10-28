// Shared building blocks: icon blobs, KPI tiles, battery meter, cards, tabs, tables and page states.

import { useEffect, useId, useRef, useState } from 'react';
import broom from '../assets/icons/broom.svg';
import chart from '../assets/icons/chart.svg';
import clock from '../assets/icons/clock.svg';
import database from '../assets/icons/database.svg';
import empty from '../assets/icons/empty.svg';
import files from '../assets/icons/files.svg';
import forecast from '../assets/icons/forecast.svg';
import pin from '../assets/icons/pin.svg';
import route from '../assets/icons/route.svg';
import signal from '../assets/icons/signal.svg';
import train from '../assets/icons/train.svg';
import RunPipeline from './RunPipeline.jsx';

export const ICONS = { broom, chart, clock, database, empty, files, forecast, pin, route, signal, train };

export function IconBlob({ icon, small = false }) {
  return (
    <div className={`icon-blob${small ? ' small' : ''}`} aria-hidden="true">
      <img src={ICONS[icon]} alt="" />
    </div>
  );
}

export function PageHead({ eyebrow, title, children }) {
  return (
    <header className="page-head page-enter">
      {eyebrow && <div className="eyebrow">{eyebrow}</div>}
      <h1 style={{ fontSize: 'clamp(30px, 3.4vw, 42px)' }}>{title}</h1>
      {children && <p>{children}</p>}
    </header>
  );
}

export function KpiTile({ icon = 'chart', label, value, unit, accent = false, foot }) {
  return (
    <div className={`kpi${accent ? ' accent' : ''}`}>
      <div className="kpi-top">
        <IconBlob icon={icon} small />
        <div className="kpi-label">{label}</div>
      </div>
      <div className="kpi-value">
        {value}
        {unit && <small>{unit}</small>}
      </div>
      {foot && <div className="kpi-foot">{foot}</div>}
    </div>
  );
}

/** Vertical battery-style meter (from the reference's "charging" card), used for on-time %. */
export function BatteryMeter({ label, pct, foot }) {
  const v = Math.max(0, Math.min(100, pct ?? 0));
  return (
    <div className="kpi">
      <div className="kpi-label">{label}</div>
      <div className="battery">
        <div className="battery-shell" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={v} aria-label={label}>
          <div className="battery-fill" style={{ height: `${v}%` }} />
        </div>
        <div className="kpi-value">
          {v.toFixed(1)}
          <small>%</small>
        </div>
      </div>
      {foot && <div className="kpi-foot">{foot}</div>}
    </div>
  );
}

export function TrendChip({ value, goodWhenDown = true, suffix = '%' }) {
  if (value == null || Number.isNaN(value)) return null;
  const up = value > 0;
  const good = goodWhenDown ? !up : up;
  return (
    <span className={`chip ${good ? 'good' : 'bad'}`}>
      {up ? '▲' : '▼'} {Math.abs(value).toFixed(0)}
      {suffix}
    </span>
  );
}

export function FeatureCard({ icon, title, stat, accent, children }) {
  return (
    <article className="feature-card">
      <IconBlob icon={icon} />
      <h3>{title}</h3>
      {stat != null && <div className={`feature-stat${accent ? ' accent' : ''}`}>{stat}</div>}
      <p>{children}</p>
    </article>
  );
}

export function Card({ title, sub, actions, children, style }) {
  return (
    <section className="card" style={style}>
      {(title || actions) && (
        <div className="card-head">
          <div>
            {title && <h2 className="card-title">{title}</h2>}
            {sub && <div className="card-sub">{sub}</div>}
          </div>
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}

export function Tabs({ tabs, value, onChange, label }) {
  return (
    <div className="tabs" role="tablist" aria-label={label}>
      {tabs.map((t) => (
        <button key={t.id} role="tab" type="button" className="tab" aria-selected={value === t.id} onClick={() => onChange(t.id)}>
          {t.label}
        </button>
      ))}
    </div>
  );
}

/** Simple table. columns: [{key, label, num, render}] */
export function DataTable({ columns, rows, highlight, maxRows = 200, caption }) {
  return (
    <div className="table-wrap">
      <table className="data">
        {caption && <caption className="sr-only">{caption}</caption>}
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key} className={c.num ? 'num' : ''} scope="col">
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, maxRows).map((r, i) => (
            <tr key={i} className={highlight?.(r) ? 'highlight' : ''}>
              {columns.map((c) => (
                <td key={c.key} className={c.num ? 'num' : ''}>
                  {c.render ? c.render(r[c.key], r) : r[c.key] ?? '–'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function delayChip(minutes) {
  if (minutes == null) return '–';
  const cls = minutes <= 15 ? 'good' : minutes <= 45 ? 'indigo' : minutes <= 90 ? 'warn' : 'bad';
  return <span className={`chip ${cls}`}>{Number(minutes).toFixed(1)} min</span>;
}

export function Loading({ rows = 2 }) {
  return (
    <div className="grid" aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="skeleton" />
      ))}
    </div>
  );
}

export function EmptyState({ title = 'Nothing matches these filters', children, action }) {
  return (
    <div className="state">
      <IconBlob icon="empty" />
      <h3>{title}</h3>
      <p>{children || 'Try widening the date range or clearing a filter.'}</p>
      {action}
    </div>
  );
}

/** Friendly error card. If the database is missing it offers to run the pipeline. */
export function ErrorState({ error, onRetry }) {
  const msg = error?.message || String(error);
  const noDb = /database|no such table|railway\.db|Run the pipeline/i.test(msg);
  const offline = error?.status === 0;
  return (
    <div className="state error" role="alert">
      <IconBlob icon={noDb ? 'database' : 'signal'} />
      <h3>{noDb ? 'The database has not been built yet' : offline ? 'Server not reachable' : 'Something went wrong'}</h3>
      <p>{noDb ? 'Run the data pipeline once to generate, clean and load the data. It takes about a minute.' : msg}</p>
      {noDb ? <RunPipeline onDone={onRetry} /> : onRetry && <button type="button" className="btn btn-secondary btn-small" onClick={onRetry}>Try again</button>}
    </div>
  );
}

/** Wraps a useApi() result: shows loading / error / content. */
export function Async({ state, children, skeleton = 2 }) {
  if (state.error) return <ErrorState error={state.error} onRetry={state.reload} />;
  if (!state.data) return <Loading rows={skeleton} />;
  return children(state.data);
}

export function MultiSelect({ label, options, value, onChange, placeholder = 'All' }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const id = useId();
  useEffect(() => {
    if (!open) return undefined;
    const close = (e) => !ref.current?.contains(e.target) && setOpen(false);
    const esc = (e) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', esc);
    return () => {
      document.removeEventListener('mousedown', close);
      document.removeEventListener('keydown', esc);
    };
  }, [open]);
  const text = value.length === 0 ? placeholder : value.length <= 2 ? value.join(', ') : `${value.length} selected`;
  return (
    <div className="field multi" ref={ref}>
      <span id={`${id}-l`}>{label}</span>
      <button type="button" className="select multi-btn" aria-haspopup="listbox" aria-expanded={open} aria-labelledby={`${id}-l`} onClick={() => setOpen((o) => !o)}>
        {text}
      </button>
      {open && (
        <ul className="multi-menu" role="listbox" aria-multiselectable="true">
          {options.map((o) => (
            <li key={o}>
              <label>
                <input
                  type="checkbox"
                  checked={value.includes(o)}
                  onChange={(e) => onChange(e.target.checked ? [...value, o] : value.filter((v) => v !== o))}
                />
                {o}
              </label>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
