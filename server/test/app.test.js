import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createApp } from '../app.js';
import { BridgeError } from '../python.js';

function fakeBridge() {
  const calls = [];
  return {
    calls,
    async call(method, params) {
      calls.push([method, params]);
      if (method === 'run_select') throw new BridgeError('Only SELECT queries are allowed.');
      return { method };
    },
  };
}

async function withServer(fn) {
  const bridge = fakeBridge();
  const pipeline = { status: () => ({ running: false }), start: () => ({ running: true }) };
  const server = createApp({ bridge, pipeline }).listen(0);
  const base = `http://localhost:${server.address().port}`;
  try {
    await fn(base, bridge);
  } finally {
    server.close();
  }
}

test('routes map to bridge methods with params', async () => {
  await withServer(async (base, bridge) => {
    const r = await fetch(`${base}/api/dashboard`, {
      method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ filters: { season: 'Winter' } }),
    });
    assert.deepEqual(await r.json(), { method: 'dashboard' });
    assert.deepEqual(bridge.calls.at(-1), ['dashboard', { filters: { season: 'Winter' } }]);

    await fetch(`${base}/api/plan`, {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ train_no: 12951, to_code: 'NGP', travel_date: '2026-12-18', evil: 'x', from_code: '' }),
    });
    assert.deepEqual(bridge.calls.at(-1), ['plan_journey', { train_no: '12951', to_code: 'NGP', travel_date: '2026-12-18' }]);
  });
});

test('bridge errors become 400 with message', async () => {
  await withServer(async (base) => {
    const r = await fetch(`${base}/api/sql`, {
      method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ sql: 'drop table x' }),
    });
    assert.equal(r.status, 400);
    assert.deepEqual(await r.json(), { error: 'Only SELECT queries are allowed.' });
  });
});

test('downloads reject unknown groups and path tricks', async () => {
  await withServer(async (base) => {
    assert.equal((await fetch(`${base}/api/download/secret/x.csv`)).status, 404);
    assert.equal((await fetch(`${base}/api/download/excel/..%2Fconfig.yaml`)).status, 404);
    assert.equal((await fetch(`${base}/api/unknown`)).status, 404);
  });
});
