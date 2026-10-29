// Dashboard / analysis filters shared across pages and remembered in this browser.

import { createContext, useContext, useEffect, useMemo, useState } from 'react';

const STORAGE_KEY = 'railpulse.filters.v2';
export const EMPTY_FILTERS = { start: '', end: '', stations: [], train_types: [], season: 'All' };

const FiltersContext = createContext(null);

function load() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? { ...EMPTY_FILTERS, ...JSON.parse(raw) } : EMPTY_FILTERS;
  } catch {
    return EMPTY_FILTERS;
  }
}

export function FiltersProvider({ children }) {
  const [filters, setFilters] = useState(load);
  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(filters));
    } catch {
      /* storage unavailable (private mode): filters still work for this visit */
    }
  }, [filters]);
  const value = useMemo(
    () => ({
      filters,
      setFilter: (key, v) => setFilters((f) => ({ ...f, [key]: v })),
      reset: () => setFilters(EMPTY_FILTERS),
      active: JSON.stringify(filters) !== JSON.stringify(EMPTY_FILTERS),
    }),
    [filters],
  );
  return <FiltersContext.Provider value={value}>{children}</FiltersContext.Provider>;
}

export function useFilters() {
  return useContext(FiltersContext);
}

/** Filters in the shape the API expects (season "All" dropped). */
export function apiFilters(f) {
  const out = {};
  if (f.start) out.start = f.start;
  if (f.end) out.end = f.end;
  if (f.stations.length) out.stations = f.stations;
  if (f.train_types.length) out.train_types = f.train_types;
  if (f.season && f.season !== 'All') out.season = f.season;
  return out;
}
