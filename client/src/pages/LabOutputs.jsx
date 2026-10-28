import { useEffect, useRef, useState } from 'react';
import { api, useApi } from '../api.js';
import { Async, EmptyState, PageHead } from '../components/ui.jsx';
import RunPipeline from '../components/RunPipeline.jsx';

export default function LabOutputs() {
  const state = useApi('lab-charts', () => api.get('/api/lab-charts'));
  const [open, setOpen] = useState(null);
  const dialog = useRef(null);

  useEffect(() => {
    const d = dialog.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);

  return (
    <>
      <PageHead eyebrow="Lab outputs" title="Saved Matplotlib & Seaborn charts">
        The static charts written by <code>python main.py</code> to <code>outputs/charts/</code>, labelled with the lab they belong to.
        Click a chart to enlarge it.
      </PageHead>
      <Async state={state} skeleton={3}>
        {(charts) =>
          charts.length === 0 ? (
            <EmptyState title="No charts yet" action={<RunPipeline onDone={state.reload} />}>Run the pipeline to generate the lab charts.</EmptyState>
          ) : (
            <div className="gallery page-enter">
              {charts.map((c) => (
                <button key={c.file} type="button" className="shot" onClick={() => setOpen(c)} aria-label={`Enlarge ${c.title}`}>
                  <img src={`/charts/${c.file}`} alt={c.title} loading="lazy" />
                  <strong>{c.title}</strong>
                  <span className="chip indigo">{c.lab}</span>
                </button>
              ))}
            </div>
          )
        }
      </Async>
      <dialog className="modal" ref={dialog} onClose={() => setOpen(null)} onClick={(e) => e.target === dialog.current && setOpen(null)}>
        {open && (
          <>
            <div className="modal-head">
              <div>
                <h2 className="card-title">{open.title}</h2>
                <span className="chip indigo">{open.lab}</span>
              </div>
              <button type="button" className="btn btn-secondary btn-small" onClick={() => setOpen(null)}>Close</button>
            </div>
            <img src={`/charts/${open.file}`} alt={open.title} />
          </>
        )}
      </dialog>
    </>
  );
}
