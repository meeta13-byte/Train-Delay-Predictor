import { useMemo, useState } from 'react';
import { api, useApi } from '../api.js';
import FilterBar, { useMeta } from '../components/FilterBar.jsx';
import Plot from '../components/Plot.jsx';
import { Async, Card, EmptyState, KpiTile, PageHead } from '../components/ui.jsx';
import { apiFilters, useFilters } from '../filters.jsx';
import { C, CALM, CATEGORY_COLORS, fmt } from '../theme.js';

const box = (rows, highlightWorst = true) => {
  const worst = Math.max(...rows.map((r) => r.median));
  return rows.map((r) => ({
    type: 'box', name: r.label, x: [r.label],
    q1: [r.q1], median: [r.median], q3: [r.q3], lowerfence: [r.lowerfence], upperfence: [r.upperfence], mean: [r.mean],
    boxmean: true, fillcolor: highlightWorst && r.median === worst ? 'rgba(251,123,27,0.25)' : 'rgba(110,127,230,0.18)',
    line: { color: highlightWorst && r.median === worst ? C.accent : C.indigo, width: 2 }, width: 0.5,
    hovertemplate: `${r.label}<br>median %{median:.0f} min · n=${r.n.toLocaleString('en-IN')}<extra></extra>`,
  }));
};

export default function Delays() {
  const { filters, reset } = useFilters();
  const f = apiFilters(filters);
  const state = useApi(`delays:${JSON.stringify(f)}`, () => api.post('/api/delays', { filters: f }));
  return (
    <>
      <PageHead eyebrow="Analysis" title="Delay analysis">
        How delays are distributed and what drives them: season, train type, weather, distance travelled and the
        reasons written in text remarks.
      </PageHead>
      <FilterBar />
      <Async state={state} skeleton={3}>
        {(d) => (d.empty ? <EmptyState action={<button type="button" className="btn btn-secondary btn-small" onClick={reset}>Clear filters</button>} /> : <Body d={d} />)}
      </Async>
      <TrainExplorer />
    </>
  );
}

function Body({ d }) {
  const c = useMemo(() => {
    const centers = d.histogram.edges.slice(0, -1).map((e, i) => (e + d.histogram.edges[i + 1]) / 2);
    const worstWeather = Math.max(...d.by_weather.map((w) => w.avg_delay));
    const types = [...new Set(d.scatter.train_type)];
    return {
      hist: {
        data: [{ type: 'bar', x: centers, y: d.histogram.counts, marker: { color: C.indigo, cornerradius: 4 }, width: 9,
          hovertemplate: '%{x:.0f} min: %{y:,} records<extra></extra>' }],
        layout: { bargap: 0.05, xaxis: { title: { text: `Delay (minutes, last bar = ${d.histogram.clipped_at}+)` } }, yaxis: { title: { text: 'Records' } }, showlegend: false },
      },
      season: { data: box(d.by_season), layout: { yaxis: { title: { text: 'Delay (minutes)' } }, showlegend: false } },
      type: { data: box(d.by_type), layout: { yaxis: { title: { text: 'Delay (minutes)' } }, showlegend: false } },
      weather: {
        data: [{ type: 'bar', orientation: 'h', y: d.by_weather.map((w) => w.weather), x: d.by_weather.map((w) => w.avg_delay),
          marker: { color: d.by_weather.map((w) => (w.avg_delay === worstWeather ? C.accent : C.periwinkle)), cornerradius: 8 },
          customdata: d.by_weather.map((w) => w.records), hovertemplate: '%{y}: %{x:.1f} min · %{customdata:,} records<extra></extra>' }],
        layout: { xaxis: { title: { text: 'Average delay (minutes)' } }, yaxis: { autorange: 'reversed' }, showlegend: false },
      },
      scatter: {
        data: types.map((t, i) => {
          const idx = d.scatter.train_type.map((v, j) => (v === t ? j : -1)).filter((j) => j >= 0);
          return { type: 'scattergl', mode: 'markers', name: t, x: idx.map((j) => d.scatter.distance[j]), y: idx.map((j) => d.scatter.delay[j]),
            marker: { size: 6, opacity: 0.55, color: CALM[i % CALM.length] }, hovertemplate: `${t}<br>%{x} km · %{y} min<extra></extra>` };
        }),
        layout: { xaxis: { title: { text: 'Distance from source (km)' } }, yaxis: { title: { text: 'Delay (minutes)' } } },
      },
      stacked: {
        data: d.category_share.series.map((s) => ({ type: 'bar', name: s.category, x: d.category_share.types, y: s.values,
          marker: { color: CATEGORY_COLORS[s.category] }, hovertemplate: `%{x}<br>${s.category}: %{y:.1f}%<extra></extra>` })),
        layout: { barmode: 'stack', yaxis: { title: { text: 'Share of records (%)' }, range: [0, 100] } },
      },
      reasons: {
        data: [{ type: 'pie', hole: 0.62, labels: d.reasons.map((r) => r.reason), values: d.reasons.map((r) => r.count), sort: true,
          marker: { colors: [C.accent, ...CALM], line: { color: '#fff', width: 3 } }, textinfo: 'label', textfont: { size: 12 },
          hovertemplate: '%{label}: %{value} remark(s)<extra></extra>' }],
        layout: { showlegend: false, margin: { t: 10, b: 10 } },
      },
    };
  }, [d]);

  return (
    <div className="page-enter">
      <div className="grid grid-2">
        <Card title="Distribution of delay" sub="How many station arrivals were late by how much"><Plot {...c.hist} /></Card>
        <Card title="Delay by season" sub="Box = middle 50%, line = median, dashed = mean"><Plot {...c.season} /></Card>
        <Card title="Delay by train type" sub="Worst median in orange"><Plot {...c.type} /></Card>
        <Card title="Delay by weather" sub="Average delay (minutes)"><Plot {...c.weather} /></Card>
        <Card title="Distance travelled vs delay" sub="Random sample of 1,500 arrivals: delay builds up along the route"><Plot {...c.scatter} /></Card>
        <Card title="Delay categories per train type" sub="On-time ≤15 · Minor ≤60 · Major ≤180 · Severe >180 min"><Plot {...c.stacked} /></Card>
      </div>
      <div className="grid grid-2 mt-24">
        <Card title="Top delay reasons" sub="Extracted with regex from unstructured text remarks"><Plot {...c.reasons} height={300} /></Card>
      </div>
    </div>
  );
}

function TrainExplorer() {
  const meta = useMeta();
  const trains = meta.data?.trains ?? [];
  const [trainNo, setTrainNo] = useState('');
  const selected = trainNo || (trains[0] ? String(trains.find((t) => t.train_type === 'Mail/Express')?.train_no ?? trains[0].train_no) : '');
  const state = useApi(selected ? `train:${selected}` : null, () => api.get(`/api/trains/${selected}`), { enabled: Boolean(selected) });

  return (
    <section className="section" aria-labelledby="explorer">
      <div className="section-head">
        <div>
          <div className="eyebrow">Train explorer</div>
          <h2 id="explorer">Where does a train lose time?</h2>
        </div>
        <label className="field" style={{ minWidth: 300 }}>
          <span>Train</span>
          <select className="select" value={selected} onChange={(e) => setTrainNo(e.target.value)}>
            {trains.map((t) => (
              <option key={t.train_no} value={t.train_no}>{t.train_no} · {t.train_name}</option>
            ))}
          </select>
        </label>
      </div>
      {selected && (
        <Async state={state}>
          {(t) => (
            <div className="grid grid-1-2">
              <div className="grid" style={{ alignContent: 'start' }}>
                <KpiTile icon="train" label={`${t.train_type} · ${t.source} → ${t.destination} · ${fmt.int(t.distance_km)} km`}
                  value={fmt.min(t.avg_delay_at_destination, 0)} unit="min at destination" accent />
                <KpiTile icon="signal" label="On-time arrivals (≤15 min)" value={fmt.pct(t.ontime_pct)}
                  foot={<span>{fmt.int(t.journeys)} journeys · {fmt.pct(t.cancel_pct)} cancelled</span>} />
              </div>
              <Card title="Delay accumulation along the route" sub="Average delay at each stop, in route order">
                <Plot
                  data={[{ type: 'scatter', mode: 'lines+markers', x: t.accumulation.map((a) => a.stop_sequence), y: t.accumulation.map((a) => a.avg_delay),
                    customdata: t.accumulation.map((a) => a.station_name), line: { color: C.accent, width: 3, shape: 'spline', smoothing: 0.5 },
                    marker: { size: 9, color: '#fff', line: { color: C.accent, width: 2.5 } }, fill: 'tozeroy', fillcolor: 'rgba(251,123,27,0.08)',
                    hovertemplate: '%{customdata}: %{y:.1f} min<extra></extra>' }]}
                  layout={{ xaxis: { tickmode: 'array', tickvals: t.accumulation.map((a) => a.stop_sequence), ticktext: t.accumulation.map((a) => a.station_name), tickangle: -30, title: { text: 'Station (in route order)' } },
                    yaxis: { title: { text: 'Average delay (minutes)' }, rangemode: 'tozero' }, showlegend: false }}
                  height={330}
                />
              </Card>
            </div>
          )}
        </Async>
      )}
    </section>
  );
}
