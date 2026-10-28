// Colour tokens and the shared Plotly look ("railpulse" template).

export const C = {
  bgPage: '#F2F6FE',
  surface: '#FFFFFF',
  blob: '#D9E6FF',
  blobSoft: '#ECF2FF',
  periwinkle: '#B6C4F8',
  indigo: '#6E7FE6',
  navy: '#33325C',
  accent: '#FB7B1B',
  accentHover: '#E86A0C',
  textStrong: '#2B2B33',
  text: '#55565E',
  textMuted: '#8A8B94',
  success: '#2EAD7A',
  danger: '#E5484D',
  grid: '#EEF2FB',
};

/** Ordered chart palette. Orange is index 3 and is reserved for the series that matters most. */
export const PALETTE = ['#6E7FE6', '#33325C', '#B6C4F8', '#FB7B1B', '#8FA8F5', '#C9D3F7'];
/** Palette without orange, for categorical series where nothing should stand out. */
export const CALM = ['#6E7FE6', '#33325C', '#B6C4F8', '#8FA8F5', '#C9D3F7', '#4A4A7A', '#A5B3F2'];

export const CATEGORY_COLORS = { 'On-time': C.success, Minor: C.periwinkle, Major: C.indigo, Severe: C.navy };

export const SEQ_SCALE = [
  [0, '#ECF2FF'],
  [0.35, '#B6C4F8'],
  [0.7, '#6E7FE6'],
  [1, '#33325C'],
];

const axis = {
  gridcolor: C.grid,
  zeroline: false,
  linecolor: C.grid,
  tickfont: { color: C.textMuted, size: 12 },
  title: { font: { color: C.textMuted, size: 12 }, standoff: 10 },
  automargin: true,
  showspikes: false,
};

export const baseLayout = {
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: '#FFFFFF',
  font: { family: 'Inter, system-ui, sans-serif', color: C.text, size: 13 },
  title: { font: { family: 'Montserrat, sans-serif', size: 16, color: C.textStrong }, x: 0, xanchor: 'left' },
  margin: { l: 8, r: 12, t: 36, b: 8 },
  colorway: PALETTE,
  xaxis: axis,
  yaxis: axis,
  legend: { orientation: 'h', x: 0, y: 1.12, xanchor: 'left', font: { size: 12, color: C.text }, bgcolor: 'rgba(0,0,0,0)' },
  hoverlabel: { bgcolor: '#FFFFFF', bordercolor: C.blob, font: { family: 'Inter, sans-serif', color: C.navy, size: 13 } },
  hovermode: 'closest',
  bargap: 0.35,
};

export const plotConfig = {
  displaylogo: false,
  responsive: true,
  modeBarButtonsToRemove: ['select2d', 'lasso2d', 'autoScale2d', 'toggleSpikelines', 'hoverClosestCartesian', 'hoverCompareCartesian'],
};

/**
 * Deep-merge a page layout onto the base template (axes merged key by key).
 * Returns a fresh copy every time: Plotly writes auto-detected values (like axis
 * type) back into the layout it is given, so shared objects would leak between charts.
 */
export function themed(layout = {}) {
  const out = { ...baseLayout, ...layout };
  for (const key of new Set(['xaxis', 'yaxis', ...Object.keys(layout)])) {
    if (/^[xy]axis\d*$/.test(key)) out[key] = { ...axis, ...(layout[key] || {}), title: { ...axis.title, ...(layout[key]?.title || {}) } };
  }
  out.legend = { ...baseLayout.legend, ...(layout.legend || {}) };
  out.margin = { ...baseLayout.margin, ...(layout.margin || {}) };
  return structuredClone(out);
}

export const fmt = {
  int: (v) => (v == null ? '–' : Math.round(v).toLocaleString('en-IN')),
  min: (v, d = 0) => (v == null ? '–' : `${Number(v).toFixed(d)}`),
  pct: (v, d = 1) => (v == null ? '–' : `${Number(v).toFixed(d)}%`),
  dur(minutes) {
    if (minutes == null) return '–';
    const m = Math.round(Math.abs(minutes));
    const h = Math.floor(m / 60);
    const r = m % 60;
    if (h && r) return `${h}h ${r}m`;
    return h ? `${h}h` : `${r} min`;
  },
};
