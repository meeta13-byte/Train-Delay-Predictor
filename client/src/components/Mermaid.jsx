// Renders a Mermaid diagram (loaded lazily from the bundled npm package, no CDN needed).

import { useEffect, useId, useRef, useState } from 'react';

let mermaidPromise = null;
function loadMermaid() {
  mermaidPromise ??= import('mermaid').then(({ default: mermaid }) => {
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: 'strict',
      theme: 'base',
      fontFamily: 'Inter, sans-serif',
      themeVariables: {
        primaryColor: '#ECF2FF',
        primaryBorderColor: '#B6C4F8',
        primaryTextColor: '#2B2B33',
        lineColor: '#6E7FE6',
        tertiaryColor: '#FFFFFF',
        attributeBackgroundColorOdd: '#FFFFFF',
        attributeBackgroundColorEven: '#F7F9FF',
      },
    });
    return mermaid;
  });
  return mermaidPromise;
}

export default function Mermaid({ chart }) {
  const ref = useRef(null);
  const id = useId().replace(/[^a-zA-Z0-9]/g, '');
  const [error, setError] = useState(null);
  useEffect(() => {
    let alive = true;
    loadMermaid()
      .then((m) => m.render(`er${id}`, chart))
      .then(({ svg }) => alive && ref.current && (ref.current.innerHTML = svg))
      .catch((e) => alive && setError(e.message));
    return () => {
      alive = false;
    };
  }, [chart, id]);
  if (error) return <pre className="code">{chart}</pre>;
  return <div className="mermaid-box" ref={ref} aria-label="Entity relationship diagram" role="img" />;
}
