import { useEffect, useMemo, useState } from 'react';
import { api, useApi } from '../api.js';
import { useMeta } from '../components/FilterBar.jsx';
import Plot from '../components/Plot.jsx';
import { Async, Card, EmptyState, KpiTile, PageHead, Tabs } from '../components/ui.jsx';
import { C, fmt } from '../theme.js';

const SCOPES = [
  { id: 'all', label: 'All trains' },
  { id: 'zone', label: 'Railway zone' },
  { id: 'train_type', label: 'Train type' },
  { id: 'train', label: 'Single train' },
];

const month = (m) => `${m}-01`;

export default function Forecast() {
  const meta = useMeta().data;
  const [kind, setKind] = useState('all');
  const [value, setValue] = useState('');
  const options = kind === 'zone' ? meta?.zones ?? [] : kind === 'train_type' ? meta?.train_types ?? [] : kind === 'train' ? meta?.trains ?? [] : [];
  const v = kind === 'all' ? null : value || (kind === 'train' ? String(options[0]?.train_no ?? '') : options[0] ?? '');
  const scope = { kind, value: v };
  const ready = kind === 'all' || Boolean(v);
  const state = useApi(ready ? `forecast:${kind}:${v}` : null, () => api.post('/api/forecast', { scope }), { enabled: ready });

  return (
    <>
      <PageHead eyebrow="Forecast" title="Delay forecast for the next 3 months">
        An ARIMA(1,1,1) model is trained on monthly average delay and checked on the last 6 months it never saw.
        The shaded band is the 95% confidence interval.
      </PageHead>

      <div className="filter-bar" style={{ gridTemplateColumns: 'auto minmax(220px, 360px)', justifyContent: 'start' }}>
        <div className="field">
          <span>Scope</span>
          <Tabs tabs={SCOPES} value={kind} onChange={(k) => { setKind(k); setValue(''); }} label="Forecast scope" />
        </div>
        {kind !== 'all' && (
          <label className="field" style={{ marginBottom: 20 }}>
            <span>{SCOPES.find((s) => s.id === kind).label}</span>
            <select className="select" value={v ?? ''} onChange={(e) => setValue(e.target.value)}>
              {kind === 'train'
                ? options.map((t) => <option key={t.train_no} value={t.train_no}>{t.train_no} · {t.train_name}</option>)
                : options.map((o) => <option key={o} value={o}>{meta?.zone_names?.[o] ? `${meta.zone_names[o]} (${o})` : o}</option>)}
            </select>
          </label>
        )}
      </div>

      <Async state={state} skeleton={3}>
        {(d) => (d.empty ? <EmptyState title="Not enough history">{d.message}</EmptyState> : <Body d={d} />)}
      </Async>
    </>
  );
}

function Body({ d }) {
  const [tab, setTab] = useState('decomp');
  const csv = useMemo(() => {
    const rows = d.forecast.months.map((m, i) => `${m},${d.forecast.values[i]},${d.forecast.lower[i]},${d.forecast.upper[i]}`);
    return URL.createObjectURL(new Blob([`month,forecast_delay,lower_95,upper_95\n${rows.join('\n')}\n`], { type: 'text/csv' }));
  }, [d]);
  useEffect(() => () => URL.revokeObjectURL(csv), [csv]);

  const main = useMemo(() => {
    const h = d.history;
    const f = d.forecast;
    const lastM = month(h.months.at(-1));
    const fx = f.months.map(month);
    return {
      data: [
        { type: 'scatter', mode: 'lines', x: [lastM, ...fx, ...fx.slice().reverse(), lastM], y: [h.values.at(-1), ...f.upper, ...f.lower.slice().reverse(), h.values.at(-1)],
          fill: 'toself', fillcolor: 'rgba(251,123,27,0.12)', line: { width: 0 }, hoverinfo: 'skip', name: '95% interval' },
        { type: 'scatter', mode: 'lines', x: h.months.map(month), y: h.values, name: 'History', line: { color: C.indigo, width: 3, shape: 'spline', smoothing: 0.5 },
          hovertemplate: '%{x|%b %Y}: %{y:.1f} min<extra>History</extra>' },
        { type: 'scatter', mode: 'lines+markers', x: [lastM, ...fx], y: [h.values.at(-1), ...f.values], name: 'Forecast',
          line: { color: C.accent, width: 3, dash: 'dash' }, marker: { size: [0, 8, 8, 8], color: C.accent },
          hovertemplate: '%{x|%b %Y}: %{y:.1f} min<extra>Forecast</extra>' },
        { type: 'scatter', mode: 'markers', x: d.holdout.months.map(month), y: d.holdout.predicted, name: 'Holdout prediction',
          marker: { color: C.navy, size: 7, symbol: 'circle-open', line: { width: 2 } }, hovertemplate: '%{x|%b %Y}: predicted %{y:.1f} min<extra></extra>' },
      ],
      layout: { xaxis: { type: 'date', tickformat: '%b %Y' }, yaxis: { title: { text: 'Average delay (minutes)' } } },
    };
  }, [d]);

  const x = d.decomposition.months.map(month);
  const line = (y, name, color, extra = {}) => ({ type: 'scatter', mode: 'lines', x, y, name, line: { color, width: 2.5 }, hovertemplate: `%{x|%b %Y}: %{y:.1f}<extra>${name}</extra>`, ...extra });
  const lags = d.acf.map((_, i) => i);
  const tabs = {
    decomp: (
      <div className="grid grid-3">
        <Card title="Trend"><Plot data={[line(d.decomposition.trend, 'Trend', C.indigo)]} layout={{ showlegend: false, yaxis: { title: { text: 'minutes' } } }} height={260} /></Card>
        <Card title="Seasonal"><Plot data={[line(d.decomposition.seasonal, 'Seasonal', C.accent)]} layout={{ showlegend: false }} height={260} /></Card>
        <Card title="Residual"><Plot data={[{ type: 'bar', x, y: d.decomposition.resid, marker: { color: C.periwinkle }, name: 'Residual', hovertemplate: '%{x|%b %Y}: %{y:.1f}<extra></extra>' }]} layout={{ showlegend: false }} height={260} /></Card>
      </div>
    ),
    ma: (
      <Card title="Moving averages" sub="3-month simple (SMA) and exponential (EMA) moving averages">
        <Plot data={[line(d.history.values, 'Monthly average', C.periwinkle), line(d.smoothing.sma, 'SMA (3)', C.indigo), line(d.smoothing.ema, 'EMA (span 3)', C.navy, { line: { color: C.navy, width: 2.5, dash: 'dot' } })]}
          layout={{ yaxis: { title: { text: 'Average delay (minutes)' } }, xaxis: { type: 'date' } }} />
      </Card>
    ),
    es: (
      <Card title="Exponential smoothing" sub="Simple (α = 0.2) and Holt-Winters (additive trend + 12-month season), with Holt-Winters' 3-month forecast">
        <Plot data={[line(d.history.values, 'Monthly average', C.periwinkle), line(d.smoothing.ses, 'Simple ES', C.indigo), line(d.smoothing.holt_winters, 'Holt-Winters fit', C.navy),
          { type: 'scatter', mode: 'lines+markers', x: d.smoothing.hw_forecast_months.map(month), y: d.smoothing.hw_forecast, name: 'Holt-Winters forecast', line: { color: C.accent, dash: 'dash', width: 2.5 } }]}
          layout={{ yaxis: { title: { text: 'Average delay (minutes)' } }, xaxis: { type: 'date' } }} />
      </Card>
    ),
    adf: (
      <div className="grid grid-1-2">
        <div className={`kpi${d.adf.stationary ? '' : ' accent'}`} style={{ justifyContent: 'flex-start', gap: 14 }}>
          <div className="kpi-label">Augmented Dickey-Fuller test</div>
          <div className="kpi-value" style={{ fontSize: 26 }}>{d.adf.stationary ? 'Stationary ✓' : 'Not stationary ✗'}</div>
          <table className="data">
            <tbody>
              <tr><td>Test statistic</td><td className="num">{d.adf.statistic}</td></tr>
              <tr><td>p-value</td><td className="num">{d.adf.p_value}</td></tr>
              <tr><td>Lags used</td><td className="num">{d.adf.lags}</td></tr>
              {Object.entries(d.adf.critical_values).map(([k, v]) => (<tr key={k}><td>Critical value {k}</td><td className="num">{v}</td></tr>))}
            </tbody>
          </table>
          <p className="small muted">p &lt; 0.05 means the series is stationary. ARIMA's d = 1 differences it once either way.</p>
        </div>
        <Card title="ACF and PACF" sub={`Bars outside the dashed lines (±${d.conf_bound}) are significant`}>
          <Plot
            data={[
              { type: 'bar', x: lags, y: d.acf, name: 'ACF', marker: { color: C.indigo } },
              { type: 'bar', x: lags, y: d.pacf, name: 'PACF', marker: { color: C.periwinkle } },
            ]}
            layout={{ barmode: 'group', xaxis: { title: { text: 'Lag (months)' }, dtick: 2 }, yaxis: { range: [-1, 1] },
              shapes: [-1, 1].map((s) => ({ type: 'line', xref: 'paper', x0: 0, x1: 1, y0: s * d.conf_bound, y1: s * d.conf_bound, line: { color: C.accent, dash: 'dash', width: 1.5 } })) }}
          />
        </Card>
      </div>
    ),
  };

  const k = d.kpis;
  const change = k.last_actual ? ((k.next_month - k.last_actual) / k.last_actual) * 100 : null;
  return (
    <div className="page-enter">
      <div className="grid grid-4">
        <KpiTile icon="forecast" label={`Next month (${new Date(month(k.next_month_label)).toLocaleDateString('en-IN', { month: 'short', year: 'numeric' })})`} value={fmt.min(k.next_month, 1)} unit="min" accent
          foot={change != null && <><span className={`chip ${change > 0 ? 'bad' : 'good'}`}>{change > 0 ? '▲' : '▼'} {Math.abs(change).toFixed(0)}%</span><span>vs last month</span></>} />
        <KpiTile icon="clock" label="3-month average forecast" value={fmt.min(k.avg_3m, 1)} unit="min" />
        <KpiTile icon="chart" label="MAE on 6-month holdout" value={fmt.min(k.mae, 2)} unit="min" />
        <KpiTile icon="signal" label="RMSE on 6-month holdout" value={fmt.min(k.rmse, 2)} unit="min" />
      </div>
      <div className="mt-24">
        <Card title="History and 3-month forecast" actions={<a className="btn btn-secondary btn-small" href={csv} download="forecast_next_3_months.csv">Download forecast CSV</a>}>
          <Plot {...main} height={400} />
        </Card>
      </div>
      <section className="mt-48">
        <Tabs label="Time-series analysis" value={tab} onChange={setTab}
          tabs={[{ id: 'decomp', label: 'Decomposition' }, { id: 'ma', label: 'Moving averages' }, { id: 'es', label: 'Exponential smoothing' }, { id: 'adf', label: 'Stationarity' }]} />
        {tabs[tab]}
      </section>
    </div>
  );
}
