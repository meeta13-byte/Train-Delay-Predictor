import { useMemo } from 'react';
import { api, useApi } from '../api.js';
import Plot from '../components/Plot.jsx';
import { Async, Card, DataTable, PageHead, delayChip } from '../components/ui.jsx';
import { C, SEQ_SCALE, fmt } from '../theme.js';

const WORST_N = 3;

export default function Stations() {
  const state = useApi('stations', () => api.get('/api/stations'));
  return (
    <>
      <PageHead eyebrow="Network" title="Stations">
        Where delays pile up. Dot size and colour show the average arrival delay at each station; the three worst stations are orange.
      </PageHead>
      <Async state={state} skeleton={2}>{(d) => <Body d={d} />}</Async>
    </>
  );
}

function Body({ d }) {
  const charts = useMemo(() => {
    const st = d.stations;
    const max = Math.max(...st.map((s) => s.avg_delay));
    const min = Math.min(...st.map((s) => s.avg_delay));
    const worstCodes = new Set(st.slice(0, WORST_N).map((s) => s.station_code));
    const calm = st.filter((s) => !worstCodes.has(s.station_code));
    const worst = st.filter((s) => worstCodes.has(s.station_code));
    const size = (v) => 10 + ((v - min) / (max - min || 1)) * 22;
    const trace = (rows, extra) => ({
      type: 'scattermap', lat: rows.map((s) => s.latitude), lon: rows.map((s) => s.longitude),
      text: rows.map((s) => `${s.station_name} (${s.station_code})`), customdata: rows.map((s) => [s.avg_delay, s.records, s.ontime_pct]),
      hovertemplate: '<b>%{text}</b><br>Avg delay %{customdata[0]:.1f} min<br>%{customdata[1]:,} records · %{customdata[2]:.0f}% on time<extra></extra>',
      ...extra,
    });
    const top = d.worst.slice().reverse();
    const byCode = Object.fromEntries(st.map((s) => [s.station_code, s]));
    const lat = [];
    const lon = [];
    for (const [a, b] of d.links) {
      if (!byCode[a] || !byCode[b]) continue;
      lat.push(byCode[a].latitude, byCode[b].latitude, null);
      lon.push(byCode[a].longitude, byCode[b].longitude, null);
    }
    const mapView = { center: { lat: 23.4, lon: 80.6 }, zoom: 4.4 };
    return {
      map: {
        data: [
          { type: 'scattermap', mode: 'lines', lat, lon, line: { color: C.periwinkle, width: 3 }, hoverinfo: 'skip', name: 'Rail lines' },
          trace(calm, { name: 'Stations', mode: 'markers', marker: { size: calm.map((s) => size(s.avg_delay)), color: calm.map((s) => s.avg_delay), colorscale: SEQ_SCALE, cmin: min, cmax: max, opacity: 0.9,
            colorbar: { title: { text: 'min' }, thickness: 12, outlinewidth: 0, len: 0.6 } } }),
          trace(worst, { name: `Worst ${WORST_N}`, mode: 'markers+text', textposition: 'top right', textfont: { color: C.navy, size: 12 },
            marker: { size: worst.map((s) => size(s.avg_delay)), color: C.accent, opacity: 0.95 } }),
        ],
        layout: {
          map: { style: 'carto-positron', ...mapView },
          margin: { l: 0, r: 0, t: 0, b: 0 }, showlegend: false, paper_bgcolor: C.blobSoft,
        },
        // no internet: plain background, rail lines still give the geography
        fallbackLayout: { map: { style: 'white-bg', ...mapView }, margin: { l: 0, r: 0, t: 0, b: 0 }, showlegend: false },
      },
      bars: {
        data: [{ type: 'bar', orientation: 'h', y: top.map((s) => s.station_name), x: top.map((s) => s.avg_delay),
          marker: { color: top.map((s) => (worstCodes.has(s.station_code) ? C.accent : C.indigo)), cornerradius: 8 },
          hovertemplate: '%{y}: %{x:.1f} min<extra></extra>' }],
        layout: { xaxis: { title: { text: 'Average delay (minutes)' } }, showlegend: false, bargap: 0.3 },
      },
    };
  }, [d]);

  return (
    <div className="page-enter">
      <Card title="Average delay by station" sub="Hover a dot for details. Lines show the rail routes in the timetable; the street map needs an internet connection.">
        <Plot {...charts.map} height={520} />
      </Card>
      <div className="grid grid-2 mt-24" style={{ alignItems: 'start' }}>
        <Card title="Worst 10 stations" sub="Average arrival delay"><Plot {...charts.bars} height={420} /></Card>
        <Card title="All stations" sub="Sorted by average delay">
          <DataTable
            rows={d.stations}
            columns={[
              { key: 'station_name', label: 'Station', render: (v, s) => <span><strong style={{ color: 'var(--text-strong)' }}>{v}</strong> <span className="muted small">{s.station_code}</span></span> },
              { key: 'zone', label: 'Zone' },
              { key: 'avg_delay', label: 'Avg delay', render: (v) => delayChip(v) },
              { key: 'ontime_pct', label: 'On time', num: true, render: (v) => fmt.pct(v, 0) },
              { key: 'records', label: 'Records', num: true, render: (v) => fmt.int(v) },
            ]}
          />
        </Card>
      </div>
    </div>
  );
}
