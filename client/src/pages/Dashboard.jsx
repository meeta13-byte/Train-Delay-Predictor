import { useMemo } from 'react';
import { api, useApi } from '../api.js';
import FilterBar from '../components/FilterBar.jsx';
import Plot from '../components/Plot.jsx';
import { Async, BatteryMeter, Card, EmptyState, KpiTile, PageHead } from '../components/ui.jsx';
import { apiFilters, useFilters } from '../filters.jsx';
import { C, CATEGORY_COLORS, SEQ_SCALE, fmt } from '../theme.js';

export default function Dashboard() {
  const { filters, reset } = useFilters();
  const f = apiFilters(filters);
  const state = useApi(`dashboard:${JSON.stringify(f)}`, () => api.post('/api/dashboard', { filters: f }));

  return (
    <>
      <PageHead eyebrow="Overview" title="Dashboard">
        How late trains run across the network, by month, train type and delay category. Cancelled runs are excluded.
      </PageHead>
      <FilterBar />
      <Async state={state} skeleton={3}>
        {(d) => (d.empty ? <EmptyState action={<button type="button" className="btn btn-secondary btn-small" onClick={reset}>Clear filters</button>} /> : <Body d={d} />)}
      </Async>
    </>
  );
}

function Body({ d }) {
  const charts = useMemo(() => {
    const worst = Math.max(...d.by_type.map((t) => t.avg_delay));
    return {
      trend: {
        data: [{ type: 'scatter', mode: 'lines', x: d.monthly.map((m) => `${m.month}-01`), y: d.monthly.map((m) => m.avg_delay),
          line: { color: C.indigo, width: 3, shape: 'spline', smoothing: 0.6 }, fill: 'tozeroy', fillcolor: 'rgba(110,127,230,0.08)',
          hovertemplate: '%{x|%b %Y}: %{y:.1f} min<extra></extra>' }],
        layout: { xaxis: { type: 'date', tickformat: '%b %Y' }, yaxis: { title: { text: 'Average delay (minutes)' }, rangemode: 'tozero' }, showlegend: false },
      },
      byType: {
        data: [{ type: 'bar', x: d.by_type.map((t) => t.train_type), y: d.by_type.map((t) => t.avg_delay),
          marker: { color: d.by_type.map((t) => (t.avg_delay === worst ? C.accent : C.indigo)), cornerradius: 8 },
          customdata: d.by_type.map((t) => t.records), hovertemplate: '%{x}<br>%{y:.1f} min · %{customdata:,} records<extra></extra>' }],
        layout: { yaxis: { title: { text: 'Average delay (minutes)' } }, showlegend: false },
      },
      donut: {
        data: [{ type: 'pie', hole: 0.62, labels: d.categories.map((c) => c.category), values: d.categories.map((c) => c.count),
          marker: { colors: d.categories.map((c) => CATEGORY_COLORS[c.category]), line: { color: '#fff', width: 3 } },
          sort: false, direction: 'clockwise', textinfo: 'percent', textfont: { color: '#fff', size: 12 },
          hovertemplate: '%{label}: %{value:,} (%{percent})<extra></extra>' }],
        layout: { showlegend: true, legend: { orientation: 'v', x: 1, y: 0.5, xanchor: 'left' }, margin: { t: 10, b: 10 },
          annotations: [{ text: 'On-time ≤15<br>Minor ≤60<br>Major ≤180', showarrow: false, font: { size: 11, color: C.textMuted } }] },
      },
      heat: {
        data: [{ type: 'heatmap', z: d.heatmap.values, x: d.heatmap.years.map(String), y: d.heatmap.months, colorscale: SEQ_SCALE,
          xgap: 3, ygap: 3, colorbar: { title: { text: 'min', side: 'top' }, thickness: 12, outlinewidth: 0 },
          hovertemplate: '%{y} %{x}: %{z:.1f} min<extra></extra>' }],
        layout: { yaxis: { autorange: 'reversed' }, xaxis: { type: 'category' } },
      },
    };
  }, [d]);

  const k = d.kpis;
  return (
    <div className="page-enter">
      <div className="grid grid-4">
        <KpiTile icon="files" label="Total records" value={fmt.int(k.total_records)} />
        <KpiTile icon="clock" label="Average delay" value={fmt.min(k.avg_delay, 1)} unit="min" accent />
        <BatteryMeter label="On-time performance (≤15 min late)" pct={k.ontime_pct} />
        <KpiTile icon="signal" label="Severe delays (>180 min)" value={fmt.int(k.severe_count)}
          foot={<span>{fmt.pct((k.severe_count / k.total_records) * 100, 2)} of records</span>} />
      </div>
      <div className="grid grid-2 mt-24">
        <Card title="Monthly average delay" sub="Mean delay per month (minutes)"><Plot {...charts.trend} /></Card>
        <Card title="Average delay by train type" sub="Worst type in orange"><Plot {...charts.byType} /></Card>
        <Card title="Delay category share" sub="Share of station arrivals"><Plot {...charts.donut} /></Card>
        <Card title="Month × year heatmap" sub="Average delay (minutes)"><Plot {...charts.heat} /></Card>
      </div>
    </div>
  );
}
