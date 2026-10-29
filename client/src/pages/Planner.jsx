import { useMemo, useState } from 'react';
import { api } from '../api.js';
import Combobox from '../components/Combobox.jsx';
import { useMeta } from '../components/FilterBar.jsx';
import Plot from '../components/Plot.jsx';
import { BatteryMeter, Card, DataTable, ErrorState, KpiTile, Loading, PageHead } from '../components/ui.jsx';
import { C, fmt } from '../theme.js';

const KIND_LABEL = {
  leave_later_arrive_earlier: 'Leave later, arrive earlier',
  leave_later_same_arrival: 'Same arrival, more time at home',
  late_but_earlier: 'Late but still earlier',
  arrives_earlier: 'Arrives earlier',
};

// local date (toISOString would give the UTC date, which is wrong early in the morning in India)
const todayIso = () => new Date().toLocaleDateString('en-CA');

function hhmm(iso, travelDate) {
  if (!iso) return '–';
  const t = iso.slice(11, 16);
  const days = Math.round((new Date(iso.slice(0, 10)) - new Date(travelDate)) / 86400000);
  return days > 0 ? `${t} (+${days}d)` : t;
}

export default function Planner() {
  const meta = useMeta();
  const [form, setForm] = useState({ train_no: '', train_type: '', from_code: '', to_code: '', travel_date: todayIso(), leave_after: '' });
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const trains = meta.data?.trains ?? [];
  const stations = meta.data?.stations ?? [];
  const chosen = trains.find((t) => String(t.train_no) === form.train_no);
  const stationName = useMemo(() => Object.fromEntries(stations.map((s) => [s.station_code, s.station_name])), [stations]);

  // train box: type a number or a name; a chosen category narrows the list
  const trainOptions = useMemo(
    () => trains
      .filter((t) => !form.train_type || chosen || t.train_type === form.train_type)
      .map((t) => ({
        value: String(t.train_no),
        label: `${t.train_no} · ${t.train_name}`,
        hint: `${t.train_type} · ${stationName[t.source_station_code] ?? t.source_station_code} → ${stationName[t.destination_station_code] ?? t.destination_station_code}`,
        keys: [t.train_name],
      })),
    [trains, form.train_type, chosen, stationName],
  );

  // with a train picked, only its stops (in route order) make sense
  const stationOptions = useMemo(() => {
    const codes = chosen ? meta.data?.train_stops?.[chosen.train_no] ?? [] : stations.map((s) => s.station_code);
    return codes.map((c) => ({ value: c, label: `${stationName[c] ?? c} (${c})`, keys: [stationName[c] ?? c], hint: chosen ? 'on this train\'s route' : undefined }));
  }, [chosen, stations, stationName, meta.data]);

  const pickTrain = (v) => {
    const t = trains.find((x) => String(x.train_no) === v);
    const stops = t ? meta.data?.train_stops?.[t.train_no] ?? [] : null;
    setForm((f) => ({
      ...f,
      train_no: v,
      // category comes from the train itself
      train_type: t ? t.train_type : f.train_type,
      // drop stations this train doesn't stop at
      from_code: stops && !stops.includes(f.from_code) ? '' : f.from_code,
      to_code: stops && !stops.includes(f.to_code) ? '' : f.to_code,
    }));
  };

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    if (!form.to_code) return setError('Choose your destination station.');
    if (!form.train_no && !form.from_code) return setError('Choose a From station when you search by category.');
    setLoading(true);
    try {
      const r = await api.post('/api/plan', form);
      if (r.error) {
        setError(r.error);
        setResult(null);
      } else setResult(r);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (meta.error) return <ErrorState error={meta.error} onRetry={meta.reload} />;

  return (
    <>
      <PageHead eyebrow="Journey planner" title="How late will my train be?">
        Enter your train (or just the kind of train), where you are going and when. We predict its delay from past
        journeys and check whether another train on the same route would get you there sooner.
      </PageHead>

      <Card>
        <form className="planner-form" onSubmit={submit} aria-label="Plan a journey">
          <Combobox
            id="plan-train"
            className="span-3"
            label="Train (type number or name)"
            placeholder="e.g. 12951 or Rajdhani"
            options={trainOptions}
            value={form.train_no}
            onChange={pickTrain}
            clearLabel={form.train_no ? 'Any train (search by category)' : undefined}
            emptyText={form.train_type ? `No ${form.train_type} train matches` : 'No train matches'}
          />
          {chosen ? (
            <div className="field span-3">
              <span>Train category <span className="field-note">· filled in from train {chosen.train_no}</span></span>
              <input id="plan-type" className="input auto" value={chosen.train_type} readOnly aria-readonly="true" />
            </div>
          ) : (
            <label className="field span-3">
              <span>Train category</span>
              <select id="plan-type" className="select" value={form.train_type} onChange={set('train_type')}>
                <option value="">Any category</option>
                {(meta.data?.train_types ?? []).map((t) => (
                  <option key={t}>{t}</option>
                ))}
              </select>
            </label>
          )}
          <Combobox
            id="plan-from"
            className="span-2"
            label="From"
            placeholder={chosen ? `${stationName[chosen.source_station_code]} (start)` : 'Type a station name'}
            options={stationOptions}
            value={form.from_code}
            onChange={(v) => setForm((f) => ({ ...f, from_code: v }))}
            emptyText="No station matches"
          />
          <Combobox
            id="plan-to"
            className="span-2"
            label="To (destination)"
            placeholder="Type a station name"
            options={stationOptions}
            value={form.to_code}
            onChange={(v) => setForm((f) => ({ ...f, to_code: v }))}
            emptyText="No station matches"
          />
          <label className="field">
            <span>Date of travel</span>
            <input id="plan-date" className="input" type="date" value={form.travel_date} onChange={set('travel_date')} required />
          </label>
          <label className="field">
            <span>Leave after</span>
            <input id="plan-after" className="input" type="time" value={form.leave_after} onChange={set('leave_after')} />
          </label>
          <div className="span-3 row">
            <button type="submit" className="btn btn-primary" disabled={loading}>{loading ? 'Checking…' : 'Predict & compare'}</button>
          </div>
        </form>
      </Card>

      <div className="mt-32" aria-live="polite">
        {loading && <Loading rows={2} />}
        {!loading && error && (
          <div className="callout accent" role="alert">
            <div>
              <div className="callout-kind">Can't plan that trip</div>
              {error}
            </div>
          </div>
        )}
        {!loading && !error && result && <Result r={result} />}
        {!loading && !error && !result && (
          <div className="callout">
            <div>
              Tip: try <strong>12951 Mumbai Nagpur Express</strong> to <strong>Nagpur</strong>. It is a slow Mail/Express, and two faster
              trains leave later but reach Nagpur hours earlier.
            </div>
          </div>
        )}
      </div>
    </>
  );
}

function Result({ r }) {
  const y = r.your_train;
  const td = r.travel_date;
  const options = r.options;

  const chart = useMemo(() => {
    const rows = [...options].reverse();
    const narrow = window.matchMedia('(max-width: 560px)').matches;
    const names = rows.map((o) => (narrow ? String(o.train_no) : `${o.train_no} ${o.train_name}`));
    const isYours = (o) => y && o.train_no === y.train_no;
    return {
      data: [
        {
          type: 'bar', orientation: 'h', y: names, base: rows.map((o) => o.sched_dep),
          x: rows.map((o) => new Date(o.sched_arr) - new Date(o.sched_dep)),
          marker: { color: rows.map((o) => (isYours(o) ? C.indigo : C.periwinkle)), cornerradius: 6 },
          name: 'Timetable', hovertemplate: '%{y}<br>Leaves %{base|%H:%M}<extra></extra>',
        },
        {
          type: 'scatter', mode: 'markers', y: names, x: rows.map((o) => o.expected_arr), name: 'Expected arrival',
          marker: { color: C.accent, size: 13, symbol: 'diamond', line: { color: '#fff', width: 1.5 } },
          hovertemplate: '%{y}<br>Expected %{x|%d %b %H:%M}<extra></extra>',
        },
      ],
      layout: {
        xaxis: { type: 'date', tickformat: '%H:%M\n%d %b', title: { text: 'Time' } },
        yaxis: { automargin: true },
        barmode: 'overlay', showlegend: !narrow, margin: { l: 8, t: narrow ? 10 : 40 },
      },
    };
  }, [options, y]);

  return (
    <div className="page-enter">
      <div className="trip-title">
        <h2>{r.from_name} → {r.to_name}</h2>
        <span className="chip indigo">{new Date(`${td}T00:00`).toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })}</span>
      </div>

      {y ? (
        <>
          <h3 className="mt-24">
            Your train: {y.train_no} {y.train_name} <span className="chip">{y.train_type}</span>
          </h3>
          <div className="grid grid-4 mt-16">
            <KpiTile icon="clock" label={`Expected delay at ${r.to_code}`} value={fmt.min(y.delay_at_to)} unit="min" accent
              foot={<span>likely {fmt.min(y.likely_low)}–{fmt.min(y.likely_high)} min</span>} />
            <KpiTile icon="pin" label="Expected arrival" value={hhmm(y.expected_arr, td)}
              foot={<span>timetable {hhmm(y.sched_arr, td)}</span>} />
            <KpiTile icon="train" label={`Expected at ${r.from_code}`} value={hhmm(y.expected_dep, td)}
              foot={<span>scheduled {hhmm(y.sched_dep, td)}</span>} />
            <BatteryMeter label="Chance of on-time (≤15 min)" pct={y.on_time_pct}
              foot={<span>{fmt.pct(y.cancel_pct)} cancelled · bad day {fmt.min(y.worst_case)} min</span>} />
          </div>
          <p className="small muted mt-8">Based on {y.based_on}, adjusted for the day of the week.</p>
        </>
      ) : (
        <p className="mt-16">No train of that category runs on this route, so here are all the trains that do.</p>
      )}

      <section className="mt-32" aria-labelledby="sugg">
        <h3 id="sugg">Suggestions</h3>
        <div className="grid mt-16" style={{ gap: 12 }}>
          {y && r.suggestions.length === 0 && (
            <div className="callout"><div>Your train is already the best choice on this route for the time you want to leave.</div></div>
          )}
          {!y && options[0] && (
            <div className="callout accent"><div><div className="callout-kind">Earliest arrival</div>
              {options[0].train_no} {options[0].train_name} leaves at {hhmm(options[0].sched_dep, td)} and should reach {r.to_code} at {hhmm(options[0].expected_arr, td)}.</div></div>
          )}
          {r.suggestions.slice(0, 5).map((s) => (
            <div key={s.train_no} className="callout accent">
              <div>
                <div className="callout-kind">{KIND_LABEL[s.kind]} · saves {fmt.dur(s.gain_minutes)}</div>
                {s.text.replace(/^[^:]+:\s*/, '')}
              </div>
            </div>
          ))}
        </div>
      </section>

      <div className="mt-32">
        <Card title="When each train leaves, and when it should really arrive" sub="Bars show the timetable; the orange diamond is the expected arrival including the usual delay.">
          <Plot data={chart.data} layout={chart.layout} height={110 + 46 * options.length} />
        </Card>
      </div>

      <div className="mt-32">
        <Card title="All trains on this route" sub="Sorted by expected arrival">
          <DataTable
            rows={options}
            highlight={(o) => y && o.train_no === y.train_no}
            columns={[
              { key: 'train_no', label: 'Train', render: (v, o) => <strong style={{ color: 'var(--text-strong)' }}>{v} {o.train_name}</strong> },
              { key: 'train_type', label: 'Category' },
              { key: 'sched_dep', label: 'Departs', render: (v) => hhmm(v, td) },
              { key: 'sched_arr', label: 'Timetable arrival', render: (v) => hhmm(v, td) },
              { key: 'delay_at_to', label: 'Expected delay', num: true, render: (v) => `${fmt.min(v)} min` },
              { key: 'expected_arr', label: 'Expected arrival', render: (v) => <strong>{hhmm(v, td)}</strong> },
              { key: 'journey_minutes', label: 'Journey', num: true, render: (v) => fmt.dur(v) },
              { key: 'on_time_pct', label: 'On-time', num: true, render: (v) => fmt.pct(v, 0) },
              { key: 'badges', label: 'Highlights', render: (v) => <span className="badges">{v.map((b) => <span key={b} className="chip indigo">{b}</span>)}</span> },
            ]}
          />
        </Card>
      </div>
    </div>
  );
}
