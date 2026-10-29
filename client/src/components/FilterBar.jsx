import { api, useApi } from '../api.js';
import { useFilters } from '../filters.jsx';
import { MultiSelect } from './ui.jsx';

export function useMeta() {
  return useApi('meta', () => api.get('/api/meta'));
}

export default function FilterBar() {
  const { filters, setFilter, reset, active } = useFilters();
  const meta = useMeta().data;
  return (
    <form className="filter-bar" onSubmit={(e) => e.preventDefault()} aria-label="Filters">
      <div className="field">
        <span>Date range</span>
        <div className="date-pair">
          <input className="input" type="date" aria-label="From date" value={filters.start} min={meta?.date_min} max={meta?.date_max}
            onChange={(e) => setFilter('start', e.target.value)} />
          <input className="input" type="date" aria-label="To date" value={filters.end} min={meta?.date_min} max={meta?.date_max}
            onChange={(e) => setFilter('end', e.target.value)} />
        </div>
      </div>
      <MultiSelect label="Station" searchable placeholder="All stations" value={filters.stations} onChange={(v) => setFilter('stations', v)}
        options={(meta?.stations ?? []).map((s) => ({ value: s.station_code, label: s.station_name, keys: [s.station_code] }))} />
      <MultiSelect label="Train type" options={meta?.train_types ?? []} value={filters.train_types} onChange={(v) => setFilter('train_types', v)} placeholder="All types" />
      <label className="field">
        <span>Season</span>
        <select className="select" value={filters.season} onChange={(e) => setFilter('season', e.target.value)}>
          <option value="All">All seasons</option>
          {(meta?.seasons ?? []).map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
      </label>
      <button type="button" className="link-btn" onClick={reset} disabled={!active} style={{ visibility: active ? 'visible' : 'hidden' }}>
        Clear filters
      </button>
    </form>
  );
}
