// Long-lived Python worker (src/bridge.py) that answers JSON requests.
// One request per line on stdin, one reply per line on stdout.

import { spawn, spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';
import readline from 'node:readline';

export const PROJECT_ROOT = path.resolve(import.meta.dirname, '..');

/** Pick the Python interpreter: $PYTHON, a local virtualenv, then python3 / python on PATH. */
export function findPython() {
  if (process.env.PYTHON) return process.env.PYTHON;
  const venvs = ['.venv/bin/python', 'venv/bin/python', '.venv/Scripts/python.exe', 'venv/Scripts/python.exe'];
  for (const rel of venvs) {
    const p = path.join(PROJECT_ROOT, rel);
    if (existsSync(p)) return p;
  }
  for (const cmd of ['python3', 'python']) {
    const r = spawnSync(cmd, ['--version'], { encoding: 'utf8' });
    if (r.status === 0) return cmd;
  }
  return 'python3';
}

export class PythonBridge {
  constructor({ python = findPython(), timeoutMs = 120_000, log = console } = {}) {
    this.python = python;
    this.timeoutMs = timeoutMs;
    this.log = log;
    this.nextId = 1;
    this.pending = new Map();
    this.proc = null;
    this.ready = null;
  }

  start() {
    if (this.proc) return this.ready;
    const proc = spawn(this.python, ['-u', '-m', 'src.bridge'], {
      cwd: PROJECT_ROOT,
      env: { ...process.env, PYTHONUNBUFFERED: '1', MPLBACKEND: 'Agg' },
      stdio: ['pipe', 'pipe', 'pipe'],
    });
    this.proc = proc;

    let markReady;
    let failReady;
    this.ready = new Promise((resolve, reject) => {
      markReady = resolve;
      failReady = reject;
    });

    readline.createInterface({ input: proc.stdout }).on('line', (line) => {
      let msg;
      try {
        msg = JSON.parse(line);
      } catch {
        this.log.warn(`[python] non-JSON output: ${line.slice(0, 200)}`);
        return;
      }
      if (msg.ready) {
        markReady();
        return;
      }
      const job = this.pending.get(msg.id);
      if (!job) return;
      this.pending.delete(msg.id);
      clearTimeout(job.timer);
      if (msg.ok) job.resolve(msg.result);
      else job.reject(new BridgeError(msg.error));
    });

    // Python logs go to stderr; only surface warnings and errors.
    readline.createInterface({ input: proc.stderr }).on('line', (line) => {
      if (/\| INFO /.test(line)) return;
      this.log.warn(`[python] ${line}`);
    });

    proc.on('error', (err) => {
      failReady(new BridgeError(`Could not start Python (${this.python}): ${err.message}`));
    });
    proc.on('exit', (code) => {
      if (this.proc === proc) this.proc = null;
      failReady(new BridgeError(`Python worker exited with code ${code}`));
      for (const job of this.pending.values()) {
        clearTimeout(job.timer);
        job.reject(new BridgeError('Python worker stopped. Check that requirements.txt is installed.'));
      }
      this.pending.clear();
    });
    return this.ready;
  }

  async call(method, params = {}) {
    await this.start();
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new BridgeError(`Python call "${method}" timed out`));
      }, this.timeoutMs);
      this.pending.set(id, { resolve, reject, timer });
      this.proc.stdin.write(JSON.stringify({ id, method, params }) + '\n');
    });
  }

  stop() {
    if (this.proc) this.proc.kill();
    this.proc = null;
  }
}

export class BridgeError extends Error {}
