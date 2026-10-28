// RailPulse API server: `npm run dev` (with the Vite client) or `npm start` (serves the built client).

import { createApp } from './app.js';
import { PipelineRunner } from './pipeline.js';
import { PythonBridge } from './python.js';

const PORT = Number(process.env.PORT) || 8000;

const bridge = new PythonBridge();
const pipeline = new PipelineRunner({
  python: bridge.python,
  onFinished: () => bridge.call('reset_cache').catch(() => {}),
});

bridge.start().then(
  () => console.log(`[server] Python worker ready (${bridge.python})`),
  (err) => console.error(`[server] ${err.message}`),
);

const server = createApp({ bridge, pipeline }).listen(PORT, () => {
  console.log(`[server] RailPulse API on http://localhost:${PORT}`);
});

const shutdown = () => {
  bridge.stop();
  server.close(() => process.exit(0));
};
process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);
