import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const require = createRequire(path.join(root, 'quality/browser/package.json'));
const policy = JSON.parse(fs.readFileSync(path.join(root, 'quality/runtime/policy.json'), 'utf8'));
const { chromium, expect } = require('@playwright/test');
if (require('@playwright/test/package.json').version !== policy.playwright) {
  throw new Error('Pinned Playwright package is required');
}

function boundedFile(value) {
  const absolute = path.resolve(value);
  if (value.split(/[\\/]/).some(part => ['..', 'engineering-log', '.git'].includes(part.toLowerCase()))) {
    throw new Error('Forbidden path');
  }
  if (!absolute.startsWith(path.join(root, '.cache/runtime/runs') + path.sep)) {
    throw new Error('Browser artifacts must stay in the dedicated runtime cache');
  }
  let current = path.parse(absolute).root;
  for (const part of absolute.slice(current.length).split(path.sep)) {
    current = path.join(current, part);
    try {
      if (fs.lstatSync(current).isSymbolicLink()) throw new Error('Symlink rejected');
    } catch (error) {
      if (error.code !== 'ENOENT') throw error;
    }
  }
  return absolute;
}

function locator(page, target) {
  if (target.role) return page.getByRole(target.role, { name: target.name, exact: true });
  if (target.label) return page.getByLabel(target.label, { exact: true });
  if (target.test_id) return page.getByTestId(target.test_id);
  throw new Error('Use a role, label or test ID locator');
}

async function run() {
  const browser = await chromium.launch();
  if (process.argv[2] === 'probe') {
    console.log(JSON.stringify({ status: 'READY', playwright: policy.playwright, chromium: browser.version() }));
    await browser.close();
    return;
  }
  let context;
  try {
    const input = JSON.parse(fs.readFileSync(boundedFile(process.argv[3]), 'utf8'));
    const directory = boundedFile(input.directory);
    const base = new URL(input.base_url);
    const allowed = new Set(input.allowed_origins);
    if (!['http:', 'https:'].includes(base.protocol) || !allowed.has(base.origin)) throw new Error('Invalid approved origin');
    context = await browser.newContext({ viewport: { width: 1280, height: 800 }, serviceWorkers: 'block' });
    context.setDefaultTimeout(5000);
    context.setDefaultNavigationTimeout(10000);
    const faults = [];
    await context.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (!allowed.has(url.origin) || decodeURIComponent(url.pathname).split('/').includes('engineering-log')) {
        faults.push('Request outside approved origins or path policy');
        await route.abort();
      } else {
        await route.continue();
      }
    });
    await context.tracing.start({ screenshots: true, snapshots: true });
    const page = await context.newPage();
    page.on('pageerror', error => faults.push(error.message));
    page.on('console', message => { if (message.type() === 'error') faults.push(message.text()); });
    page.on('response', response => { if (response.status() >= 500) faults.push('HTTP ' + response.status()); });
    page.on('requestfailed', () => faults.push('Browser request failed'));
    const results = [];
    const screenshots = [];
    for (const [index, scenario] of input.charter.scenarios.entries()) {
      if (!/^[A-Z][A-Z0-9_-]*$/.test(scenario.id) || !Array.isArray(scenario.steps) || !scenario.steps.length) throw new Error('Invalid scenario');
      const result = { id: scenario.id, status: 'PASS', assertions: 0 };
      try {
        for (const step of scenario.steps) {
          if (step.action === 'goto') {
            const url = new URL(step.path, base);
            if (url.origin !== base.origin) throw new Error('Navigation must stay on the approved UI origin');
            await page.goto(url.href);
            continue;
          }
          const target = locator(page, step.target);
          if (step.action === 'click') await target.click();
          else if (step.action === 'fill') {
            const value = step.value_env ? process.env[step.value_env] : step.value;
            if (typeof value !== 'string') throw new Error('Input value is unavailable');
            await target.fill(value);
          } else if (step.action === 'press') await target.press(step.key);
          else if (step.action === 'select') await target.selectOption(step.value);
          else if (step.action === 'expect_visible') { await expect(target).toBeVisible(); result.assertions++; }
          else if (step.action === 'expect_text') { await expect(target).toHaveText(step.value); result.assertions++; }
          else if (step.action === 'expect_count') { await expect(target).toHaveCount(step.value); result.assertions++; }
          else throw new Error('Unknown charter action');
        }
        if (!result.assertions) throw new Error('Each scenario needs an observable assertion');
      } catch (error) {
        result.status = 'FAIL';
        result.error = error.message;
      }
      const screenshot = `${index + 1}-${scenario.id}.png`;
      await page.screenshot({ path: boundedFile(path.join(directory, screenshot)), fullPage: true });
      screenshots.push(screenshot);
      results.push(result);
    }
    await context.tracing.stop({ path: boundedFile(path.join(directory, 'trace.zip')) });
    const status = faults.length || results.some(item => item.status !== 'PASS') ? 'FAIL' : 'PASS';
    fs.writeFileSync(boundedFile(path.join(directory, 'browser-result.json')), JSON.stringify({
      status, playwright: policy.playwright, chromium: browser.version(), scenarios: results,
      faults, screenshots, trace: 'trace.zip',
    }, null, 2) + '\n', { mode: 0o600 });
    console.log(JSON.stringify({ status, scenarios: results.length, evidence: 'private local screenshots and trace' }));
    process.exitCode = status === 'PASS' ? 0 : 1;
  } finally {
    if (context) await context.close();
    await browser.close();
  }
}

await run();
