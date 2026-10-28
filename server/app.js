// Express app: JSON API for the RailPulse UI. All data comes from src/api.py via the Python bridge.

import express from 'express';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { BridgeError, PROJECT_ROOT } from './python.js';

const DOWNLOAD_DIRS = { excel: 'outputs/excel', processed: 'data/processed', reports: 'outputs/reports' };
const CLIENT_DIST = path.join(PROJECT_ROOT, 'client', 'dist');

export function createApp({ bridge, pipeline }) {
  const app = express();
  app.disable('x-powered-by');
  app.use(express.json({ limit: '100kb' }));

  // Wrap a bridge call as a route handler: (req) => [method, params]
  const route = (pick) => async (req, res, next) => {
    try {
      const [method, params] = pick(req);
      res.json(await bridge.call(method, params));
    } catch (err) {
      next(err);
    }
  };

  app.get('/api/status', route(() => ['db_status']));
  app.get('/api/meta', route(() => ['meta']));
  app.get('/api/home', route(() => ['home']));
  app.post('/api/dashboard', route((req) => ['dashboard', { filters: req.body?.filters ?? {} }]));
  app.post('/api/delays', route((req) => ['delay_analysis', { filters: req.body?.filters ?? {} }]));
  app.get('/api/trains/:trainNo', route((req) => ['train_explorer', { train_no: Number(req.params.trainNo) }]));
  app.get('/api/stations', route(() => ['stations']));
  app.post('/api/forecast', route((req) => ['forecast', { scope: req.body?.scope ?? { kind: 'all' } }]));
  app.get('/api/pipeline', route(() => ['pipeline']));
  app.get('/api/queries/:name', route((req) => ['run_query', { name: req.params.name }]));
  app.post('/api/sql', route((req) => ['run_select', { sql: String(req.body?.sql ?? '') }]));
  app.get('/api/lab-charts', route(() => ['lab_charts']));
  app.post('/api/plan', route((req) => ['plan_journey', pickPlanParams(req.body)]));

  app.get('/api/pipeline/run', (req, res) => res.json(pipeline.status()));
  app.post('/api/pipeline/run', (req, res) => res.json(pipeline.start({ regenerate: Boolean(req.body?.regenerate) })));

  // Downloads: only files that live directly inside the allowed output folders.
  app.get('/api/download/:group/:name', (req, res, next) => {
    const dir = DOWNLOAD_DIRS[req.params.group];
    const name = path.basename(req.params.name);
    if (!dir || name !== req.params.name || !/\.(xlsx|csv|json)$/.test(name)) return res.status(404).json({ error: 'Not found' });
    const file = path.join(PROJECT_ROOT, dir, name);
    if (!existsSync(file)) return res.status(404).json({ error: 'File not found. Run the pipeline first.' });
    res.download(file, name, (err) => err && next(err));
  });

  // Saved Matplotlib charts for the Lab Outputs page.
  app.use('/charts', express.static(path.join(PROJECT_ROOT, 'outputs', 'charts'), { maxAge: '5m' }));

  app.use('/api', (req, res) => res.status(404).json({ error: `No API route ${req.method} ${req.path}` }));

  // Production build of the React client (npm start). In development Vite serves it.
  if (existsSync(CLIENT_DIST)) {
    app.use(express.static(CLIENT_DIST));
    app.get(/^(?!\/api\/|\/charts\/).*/, (req, res) => res.sendFile(path.join(CLIENT_DIST, 'index.html')));
  }

  // eslint-disable-next-line no-unused-vars
  app.use((err, req, res, next) => {
    const known = err instanceof BridgeError;
    if (!known) console.error(err);
    res.status(known ? 400 : 500).json({ error: known ? err.message : 'Internal server error' });
  });

  return app;
}

function pickPlanParams(body = {}) {
  const out = {};
  for (const key of ['train_no', 'train_type', 'from_code', 'to_code', 'travel_date', 'leave_after']) {
    if (body[key] !== undefined && body[key] !== null && body[key] !== '') out[key] = String(body[key]);
  }
  return out;
}
