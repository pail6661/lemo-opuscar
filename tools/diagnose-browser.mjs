// Keep JavaScript in a file: Windows PowerShell 5.1 strips embedded quotes in node -e arguments.
import { chromium } from 'playwright-core';
import { EXE, ARGS } from '../core/render/browser.mjs';

let browser;
try {
  browser = await chromium.launch({ executablePath: EXE, args: ARGS });
  const version = browser.version();
  await browser.close();
  browser = undefined;
  console.log(JSON.stringify({ installed: true, version, error: null }));
} catch (error) {
  console.log(JSON.stringify({ installed: false, version: null, error: error.message.split('\n')[0] }));
} finally {
  if (browser) await browser.close().catch(() => {});
}
