// "Re-run pipeline" button with a live progress bar (polls the server while python main.py runs).

import { useEffect, useRef, useState } from 'react';
import { api, clearCache } from '../api.js';

export default function RunPipeline({ onDone, label = 'Run pipeline', showLog = false }) {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const timer = useRef(null);

  const poll = async () => {
    try {
      const s = await api.get('/api/pipeline/run');
      setStatus(s);
      if (s.running) {
        timer.current = setTimeout(poll, 1000);
      } else if (!s.error && s.finishedAt) {
        clearCache();
        onDone?.();
      }
    } catch (e) {
      setError(e.message);
    }
  };

  useEffect(() => {
    // pick up a run that is already in progress (e.g. started from another tab)
    api.get('/api/pipeline/run').then((s) => {
      if (s.running) {
        setStatus(s);
        timer.current = setTimeout(poll, 1000);
      }
    }).catch(() => {});
    return () => clearTimeout(timer.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const start = async () => {
    setError(null);
    try {
      setStatus(await api.post('/api/pipeline/run', {}));
      timer.current = setTimeout(poll, 800);
    } catch (e) {
      setError(e.message);
    }
  };

  const running = status?.running;
  return (
    <div style={{ width: '100%', maxWidth: 520, display: 'flex', flexDirection: 'column', gap: 12, alignItems: 'center' }}>
      <button type="button" className="btn btn-primary" onClick={start} disabled={running}>
        {running ? 'Running…' : label}
      </button>
      {status && (status.running || status.error || status.phase === 'Done') && (
        <div style={{ width: '100%' }} aria-live="polite">
          <div className="progress" role="progressbar" aria-valuenow={status.progress} aria-valuemin={0} aria-valuemax={100} aria-label="Pipeline progress">
            <div style={{ width: `${status.progress}%` }} />
          </div>
          <p className="small muted mt-8" style={{ textAlign: 'center' }}>
            {status.error ? status.error : status.phase === 'Done' ? 'Done. Data refreshed.' : `${status.phase}…`}
          </p>
          {(showLog || status.error) && status.log?.length > 0 && <pre className="code mt-8" style={{ textAlign: 'left', maxHeight: 200 }}>{status.log.join('\n')}</pre>}
        </div>
      )}
      {error && <p className="small" style={{ color: 'var(--danger)' }}>{error}</p>}
    </div>
  );
}
