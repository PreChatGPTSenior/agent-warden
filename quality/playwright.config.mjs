import { createRequire } from 'node:module';
const require = createRequire(new URL('./browser/package.json', import.meta.url));
const { defineConfig } = require('@playwright/test');
if (!process.env.TASK_TEST_DIR || !process.env.UI_URL || !process.env.TASK_EVIDENCE_DIR) throw new Error('Explicit isolated task paths and URL are required');
export default defineConfig({ testDir: process.env.TASK_TEST_DIR, outputDir: process.env.TASK_EVIDENCE_DIR, workers: 1, retries: 0, forbidOnly: true, timeout: 45000, use: { baseURL: process.env.UI_URL, trace: 'on', screenshot: 'on', video: 'off' }, reporter: [['junit', { outputFile: process.env.PLAYWRIGHT_JUNIT_OUTPUT_FILE }]] });
