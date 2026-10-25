import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { serve, pageURL } from '../core/render/serve.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const tempBase = process.env.LEMO_TEST_TEMP || os.tmpdir();
const temp = fs.mkdtempSync(path.join(tempBase, 'lemo-render-中文 空格-'));
test.after(() => fs.rmSync(temp, { recursive: true, force: true }));

test('HTTP serving handles Unicode, spaces, mounted projects and traversal', async () => {
  const library = path.join(temp, '风格 库');
  const film = path.join(temp, '用户 影片');
  fs.mkdirSync(library);
  fs.mkdirSync(film);
  fs.writeFileSync(path.join(library, '中文 模块.js'), 'export const title = "中文";');
  fs.writeFileSync(path.join(film, 'index.html'), '<p>中文影片</p>');
  const server = await serve(library);
  try {
    const filmURL = pageURL(library, server.port, film);
    const response = await fetch(filmURL);
    assert.equal(response.status, 200);
    assert.match(response.headers.get('content-type'), /charset=utf-8/);
    assert.equal(await response.text(), '<p>中文影片</p>');
    const module = await fetch(`http://127.0.0.1:${server.port}/${encodeURIComponent('中文 模块.js')}`);
    assert.equal(module.status, 200);
    assert.equal(await module.text(), 'export const title = "中文";');
    const escaped = await fetch(`http://127.0.0.1:${server.port}/%2e%2e%2foutside.txt`);
    assert.equal(escaped.status, 403);
    const malformed = await fetch(`http://127.0.0.1:${server.port}/%zz`);
    assert.equal(malformed.status, 400);
  } finally {
    await new Promise(resolve => server.server.close(resolve));
  }
});

const toolsReady = fs.existsSync(path.join(root, 'node_modules', 'playwright-core'))
  && spawnSync('ffmpeg', ['-version'], { windowsHide: true }).status === 0
  && spawnSync('ffprobe', ['-version'], { windowsHide: true }).status === 0;

test('render CLIs create usable video, stills and cues in a Unicode project path', {
  skip: toolsReady ? false : 'Install the core tools with tools/setup-codex.ps1 first',
  timeout: 90000,
}, async () => {
  const { chromium } = await import('playwright-core');
  assert.ok(process.env.PLAYWRIGHT_CHROME || fs.existsSync(chromium.executablePath()),
    'Install the headless browser, or set PLAYWRIGHT_BROWSERS_PATH / PLAYWRIGHT_CHROME');
  const film = path.join(temp, '我的 测试片 #1');
  fs.mkdirSync(film);
  fs.writeFileSync(path.join(film, 'index.html'), `<!doctype html><meta charset="utf-8">
<style>html,body{margin:0;overflow:hidden;background:#101e30}canvas{display:block}</style>
<canvas></canvas><script type="module">
import { clamp } from '/core/lib.js';
const c=document.querySelector('canvas');c.width=innerWidth;c.height=innerHeight;
const x=c.getContext('2d');window.DUR=2;window.EV=[{t:0.5,type:'ding'}];
window.TEXTS=()=>[{id:'title',text:'OK',x0:20,y0:20,x1:140,y1:70}];
window.render=t=>{x.fillStyle='#101e30';x.fillRect(0,0,c.width,c.height);
x.fillStyle='#e9b648';x.fillRect(20+clamp(t/2,0,1)*100,100,60,30);
x.fillStyle='#ffffff';x.font='32px sans-serif';x.fillText('OK',20,55)};
window.READY=true;window.render(0);
</script>`);
  const run = (script, args) => execFileSync(process.execPath, [path.join(root, 'core', 'render', script), film, ...args], {
    cwd: root, windowsHide: true, timeout: 60000, encoding: 'utf8',
  });
  run('events.mjs', ['--size', '320x180']);
  assert.deepEqual(JSON.parse(fs.readFileSync(path.join(film, 'events.json'), 'utf8')),
    { dur: 2, ev: [{ t: 0.5, type: 'ding' }] });
  run('still.mjs', ['0.5', '--size', '320x180']);
  assert.ok(fs.statSync(path.join(film, 'stills', 't_0.5.jpg')).size > 1000);
  assert.match(run('readcheck.mjs', ['--size', '320x180']), /OK\s+title/);
  const output = path.join(film, "成片 '高清 #1.mp4");
  run('video.mjs', ['--size', '320x180', '--fps', '12', '--workers', '2', '--out', output]);
  // Re-render to an existing output too: Windows must replace it without a rename or lock failure.
  run('video.mjs', ['--size', '320x180', '--fps', '12', '--workers', '2', '--out', output]);
  const probe = JSON.parse(execFileSync('ffprobe', ['-v', 'error', '-show_streams', '-show_format', '-of', 'json', output], {
    windowsHide: true, encoding: 'utf8',
  }));
  const video = probe.streams.find(s => s.codec_type === 'video');
  assert.equal(video.width, 320);
  assert.equal(video.height, 180);
  assert.equal(Number(video.nb_frames), 24);
  assert.ok(Math.abs(Number(probe.format.duration) - 2) < 0.1);
  assert.ok(!fs.existsSync(output + '.lock'));
  assert.equal(fs.readdirSync(film).filter(n => n.includes('_segs-')).length, 0);
});
