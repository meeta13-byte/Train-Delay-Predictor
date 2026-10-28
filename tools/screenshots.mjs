// Screenshot every page of the running app and report browser console errors.
//
//   npm run dev                      (in another terminal)
//   npm run screenshots              -> outputs/ui_screenshots/*.png at 1440px
//   node tools/screenshots.mjs --widths 1440,1024,390 --base http://localhost:5173
//
// Needs Playwright:  npm i -D playwright && npx playwright install chromium

import { mkdirSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';

const require = createRequire(import.meta.url);
let chromium;
try {
  ({ chromium } = require('playwright'));
} catch {
  console.error('Playwright is not installed. Run: npm i -D playwright && npx playwright install chromium');
  process.exit(1);
}

const args = Object.fromEntries(
  process.argv.slice(2).reduce((acc, a, i, all) => (a.startsWith('--') ? [...acc, [a.slice(2), all[i + 1]]] : acc), []),
);
const BASE = args.base || 'http://localhost:5173';
const WIDTHS = (args.widths || '1440').split(',').map(Number);
const ONLY = args.pages ? args.pages.split(',') : null;
const OUT = path.resolve(import.meta.dirname, '..', args.out || 'outputs/ui_screenshots');

const PAGES = [
  ['home', '/'],
  ['plan', '/plan', async (page) => {
    await page.selectOption('#plan-train', '12951');
    await page.selectOption('#plan-to', 'NGP');
    await page.fill('#plan-date', '2026-12-18');
    await page.click('button[type=submit]');
    await page.waitForSelector('.trip-title', { timeout: 30000 });
  }],
  ['dashboard', '/dashboard'],
  ['delays', '/delays'],
  ['stations', '/stations'],
  ['forecast', '/forecast'],
  ['pipeline', '/pipeline', async (page) => {
    for (const s of await page.$$('details.step')) await s.evaluate((el) => (el.open = true));
    await page.waitForTimeout(1500);
  }],
  ['lab-outputs', '/lab-outputs'],
  ['about', '/about'],
];

mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch();
let problems = 0;
for (const width of WIDTHS) {
  const page = await browser.newPage({ viewport: { width, height: width < 600 ? 844 : 900 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
  page.on('pageerror', (e) => errors.push(String(e)));
  for (const [name, url, act] of PAGES) {
    if (ONLY && !ONLY.includes(name)) continue;
    errors.length = 0;
    const t0 = Date.now();
    await page.goto(BASE + url, { waitUntil: 'networkidle' });
    await page.waitForFunction(() => !document.querySelector('[aria-busy="true"]'), null, { timeout: 60000 }).catch(() => {});
    const loadMs = Date.now() - t0;
    if (act) await act(page);
    await page.waitForTimeout(900);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    const file = path.join(OUT, `${name}-${width}.png`);
    await page.screenshot({ path: file, fullPage: true });
    // map tiles are fetched from the internet; ignore those failures when offline
    const real = errors.filter((e) => !/cartocdn|basemaps|Map error|fonts\.g|ERR_TUNNEL|ERR_NAME|Failed to load resource/.test(e));
    if (real.length || overflow > 0) problems++;
    console.log(`${name.padEnd(12)} ${String(width).padStart(4)}px  ${String(loadMs).padStart(5)}ms  overflow=${overflow}px  errors=${real.length}${real.length ? '  ' + real.slice(0, 3).join(' | ').slice(0, 300) : ''}`);
  }
  await page.close();
}
await browser.close();
console.log(`Saved to ${OUT}`);
process.exit(problems ? 1 : 0);
