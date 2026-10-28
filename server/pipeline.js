// Runs `python main.py` in the background and tracks its progress for the UI.

import { spawn } from 'node:child_process';
import readline from 'node:readline';
import { PROJECT_ROOT } from './python.js';

const PHASES = [
  'Generate synthetic data',
  'Ingest all formats',
  'Clean + preprocess',
  'Database schema + load + integrity',
  'SQL queries',
  'Visualizations',
  'Time series + ARIMA forecast',
  'FINAL SUMMARY',
];

export class PipelineRunner {
  constructor({ python, onFinished = () => {} }) {
    this.python = python;
    this.onFinished = onFinished;
    this.state = { running: false, progress: 0, phase: null, error: null, finishedAt: null, log: [] };
  }

  status() {
    return { ...this.state, log: this.state.log.slice(-12) };
  }

  start({ regenerate = false } = {}) {
    if (this.state.running) return this.status();
    const args = ['-u', 'main.py'];
    if (regenerate) args.push('--regenerate');
    this.state = { running: true, progress: 2, phase: 'Starting', error: null, finishedAt: null, log: [] };

    const proc = spawn(this.python, args, { cwd: PROJECT_ROOT, env: { ...process.env, MPLBACKEND: 'Agg' } });
    const onLine = (line) => {
      const clean = line.replace(/^\S+ \S+ \| /, '');
      this.state.log.push(clean);
      if (this.state.log.length > 200) this.state.log.shift();
      // the Excel workbook is the slowest step (~30 s); say so instead of looking stuck
      if (/Excel sheet /.test(line)) {
        this.state.phase = 'Writing cleaned Excel workbook';
        this.state.progress = 30;
      }
      const m = line.match(/=== (?:Phase \d+: )?(.+?) ===/);
      if (m) {
        const idx = PHASES.findIndex((p) => m[1].startsWith(p));
        if (idx >= 0) {
          this.state.phase = PHASES[idx];
          this.state.progress = Math.round(((idx + 0.5) / PHASES.length) * 100);
        }
      }
    };
    readline.createInterface({ input: proc.stdout }).on('line', onLine);
    readline.createInterface({ input: proc.stderr }).on('line', onLine);

    proc.on('error', (err) => {
      this.state = { ...this.state, running: false, error: `Could not start Python: ${err.message}` };
    });
    proc.on('exit', async (code) => {
      const ok = code === 0;
      this.state = {
        ...this.state,
        running: false,
        progress: ok ? 100 : this.state.progress,
        phase: ok ? 'Done' : this.state.phase,
        error: ok ? null : `Pipeline failed (exit code ${code}). See the log below.`,
        finishedAt: new Date().toISOString(),
      };
      if (ok) await this.onFinished();
    });
    return this.status();
  }
}
