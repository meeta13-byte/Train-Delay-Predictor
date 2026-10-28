// Plotly chart that always uses the RailPulse template. Plotly is loaded lazily (it is large).

import { useEffect, useRef, useState } from 'react';
import { plotConfig, themed } from '../theme.js';

let plotlyPromise = null;
const loadPlotly = () => (plotlyPromise ??= import('plotly.js-dist-min').then((m) => m.default ?? m));

export default function Plot({ data, layout, fallbackLayout, height = 340, className = '', ariaLabel }) {
  const ref = useRef(null);
  const [failed, setFailed] = useState(null);

  useEffect(() => {
    let alive = true;
    const el = ref.current;
    loadPlotly()
      .then((Plotly) => {
        if (!alive || !el) return;
        return Plotly.react(el, data, themed({ height, ...layout }), plotConfig).catch((e) => {
          // e.g. map tiles/style unreachable offline: redraw with a layout that needs no network
          if (!fallbackLayout || !alive) throw e;
          return Plotly.react(el, data, themed({ height, ...fallbackLayout }), plotConfig);
        });
      })
      .catch((e) => alive && setFailed(e.message));
    return () => {
      alive = false;
    };
  }, [data, layout, fallbackLayout, height]);

  useEffect(() => {
    const el = ref.current;
    if (!el || typeof ResizeObserver === 'undefined') return undefined;
    const ro = new ResizeObserver(() => {
      // skip hidden (closed tab / details) or already-removed charts
      if (el.data && el.isConnected && el.offsetParent) loadPlotly().then((Plotly) => Plotly.Plots.resize(el)).catch(() => {});
    });
    ro.observe(el);
    return () => {
      ro.disconnect();
      loadPlotly().then((Plotly) => Plotly.purge(el));
    };
  }, []);

  if (failed) return <p className="muted small">Chart could not be drawn: {failed}</p>;
  return <div ref={ref} className={`plot ${className}`} style={{ minHeight: height }} role="img" aria-label={ariaLabel || layout?.title?.text || 'Chart'} />;
}
