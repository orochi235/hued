#!/usr/bin/env node
// Drives the `hued map` page in headless Chrome and screenshots each state, so the page can be
// looked at without opening a browser by hand.
//
//   node scripts/map-shot/shoot.mjs [<out dir>]      (default: out/map-shot, emptied first)
//
// Needs Node 22+ (built-in WebSocket) and Chrome; set CHROME to its path if it is not the macOS default.
import { spawn } from 'node:child_process';
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const repo = resolve(here, '..', '..');
const out = resolve(process.argv[2] || join(repo, 'out', 'map-shot'));
const chromePath = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const WIDTH = 1200, HEIGHT = 1500;
const STEPS = 8;
let step = 0;
const say = what => console.log(`${++step}/${STEPS} ${what}`);
const sleep = ms => new Promise(done => setTimeout(done, ms));

function firstLine(stream, pattern, label) {
  return new Promise((done, fail) => {
    let seen = '';
    const timer = setTimeout(() => fail(new Error(`${label}: no match for ${pattern} in:\n${seen}`)), 30000);
    stream.on('data', chunk => {
      seen += chunk;
      const hit = seen.match(pattern);
      if (hit) { clearTimeout(timer); done(hit[0]); }
    });
  });
}

const work = mkdtempSync(join(tmpdir(), 'hued-map-shot-'));
const children = [];
async function cleanup() {
  // Chrome keeps writing its profile until it has exited; removing the directory before then fails.
  await Promise.all(children.map(child => new Promise(done => {
    if (child.exitCode !== null || child.signalCode !== null) return done();
    child.once('exit', done);
    child.kill();
  })));
  rmSync(work, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
}

async function main() {
  rmSync(out, { recursive: true, force: true });
  mkdirSync(out, { recursive: true });

  const fixture = JSON.parse(readFileSync(join(here, 'fixture.json'), 'utf8'));
  for (const [name, config] of Object.entries(fixture)) {
    mkdirSync(join(work, 'src', name), { recursive: true });
    writeFileSync(join(work, 'src', name, '.hued'),
      Object.entries(config).map(([k, v]) => `${k}=${v}\n`).join(''));
  }
  const target = join(work, 'src', 'newrepo');
  mkdirSync(target);

  say('starting hued map');
  const map = spawn(join(repo, 'bin', 'hued'), ['map', '--no-open'],
    { cwd: target, env: { ...process.env, HUED_TTY: '/dev/null' } });
  children.push(map);
  map.stdout.setEncoding('utf8');
  let mapLog = '';
  map.stdout.on('data', chunk => { mapLog += chunk; });
  map.stderr.on('data', chunk => { mapLog += chunk; });
  const exited = new Promise(done => map.on('exit', code => done(code)));
  const url = await firstLine(map.stdout, /http:\/\/127\.0\.0\.1:\d+\/\?t=\S+/, 'hued map');

  say('starting Chrome');
  const chrome = spawn(chromePath, ['--headless=new', '--remote-debugging-port=0', '--no-first-run',
    '--hide-scrollbars', `--user-data-dir=${join(work, 'chrome')}`, 'about:blank']);
  children.push(chrome);
  chrome.stderr.setEncoding('utf8');
  const endpoint = await firstLine(chrome.stderr, /ws:\/\/\S+/, 'Chrome');

  const socket = new WebSocket(endpoint);
  await new Promise((done, fail) => { socket.onopen = done; socket.onerror = () => fail(new Error('no DevTools socket')); });
  const waiting = new Map(), problems = [];
  let nextId = 0;
  socket.onmessage = event => {
    const message = JSON.parse(event.data);
    if (message.id && waiting.has(message.id)) {
      const { done, fail } = waiting.get(message.id);
      waiting.delete(message.id);
      message.error ? fail(new Error(message.error.message)) : done(message.result);
    } else if (message.method === 'Runtime.exceptionThrown') {
      problems.push(message.params.exceptionDetails.exception?.description || message.params.exceptionDetails.text);
    } else if (message.method === 'Log.entryAdded' && message.params.entry.level === 'error') {
      problems.push(`${message.params.entry.text} ${message.params.entry.url || ''}`);
    }
  };
  const send = (method, params = {}, sessionId) => new Promise((done, fail) => {
    const id = ++nextId;
    waiting.set(id, { done, fail });
    socket.send(JSON.stringify({ id, method, params, sessionId }));
  });

  const { targetId } = await send('Target.createTarget', { url: 'about:blank' });
  const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true });
  const page = (method, params) => send(method, params, sessionId);
  await page('Page.enable');
  await page('Runtime.enable');
  await page('Log.enable');
  await page('Emulation.setDeviceMetricsOverride',
    { width: WIDTH, height: HEIGHT, deviceScaleFactor: 2, mobile: false });

  const evaluate = async expression => {
    const { result, exceptionDetails } = await page('Runtime.evaluate', { expression, returnByValue: true });
    if (exceptionDetails) throw new Error(exceptionDetails.exception?.description || exceptionDetails.text);
    return result.value;
  };
  const shoot = async name => {
    const { data } = await page('Page.captureScreenshot', { format: 'png' });
    writeFileSync(join(out, name), Buffer.from(data, 'base64'));
  };
  const click = async (x, y) => {
    for (const type of ['mousePressed', 'mouseReleased']) {
      await page('Input.dispatchMouseEvent', { type, x, y, button: 'left', clickCount: 1 });
    }
  };
  const center = selector => evaluate(`(() => {
    const r = document.querySelector(${JSON.stringify(selector)}).getBoundingClientRect();
    return [r.left + r.width / 2, r.top + r.height / 2, r.left, r.top, r.width, r.height];
  })()`);

  say('page loaded, glyphs drawn');
  await page('Page.navigate', { url });
  await sleep(5000);
  await shoot('1-loaded.png');

  say('clicked the map, picked a symbol');
  const [, , left, top, width, height] = await center('#map');
  await click(left + width * 0.62, top + height * 0.55);
  await sleep(800);
  await evaluate(`document.getElementById('sym').focus()`);
  await page('Input.insertText', { text: 'brain' });
  await sleep(2500);
  await shoot('2-clicked.png');

  say('dark only, a suggested gap selected');
  const [dx, dy] = await center('input[name=band][value=dark]');
  await click(dx, dy);
  await sleep(300);
  const [sx, sy] = await center('#gaps .swatch');
  await click(sx, sy);
  await sleep(300);
  await shoot('3-dark.png');

  say('accent2 picked from a typed hex');
  const [ax, ay] = await center('.slot[data-slot=accent2]');
  await click(ax, ay);
  await evaluate(`document.getElementById('hex').focus()`);
  await page('Input.insertText', { text: '#ccff00' });
  await sleep(600);
  await shoot('4-accent.png');
  const copied = await evaluate(`(() => {
    const range = document.createRange();
    range.selectNodeContents(document.getElementById('term'));
    getSelection().removeAllRanges();
    getSelection().addRange(range);
    return getSelection().toString();
  })()`);
  if (!/^hued set \S/.test(copied) || copied.includes('\n')) problems.push(`preview copies as ${JSON.stringify(copied)}`);
  console.log(`preview copies as: ${copied}`);

  say('back on background, click swatches follow it');
  const [bx, by] = await center('.slot[data-slot=background]');
  await click(bx, by);
  await sleep(600);
  await shoot('5-slot.png');

  say('used it');
  const [ux, uy] = await center('#use');
  await click(ux, uy);
  await sleep(1000);
  await shoot('6-written.png');
  const code = await Promise.race([exited, sleep(5000).then(() => 'still running')]);

  socket.close();
  console.log(`hued map exit: ${code}`);
  console.log(mapLog.replaceAll(work, '<tmp>').trimEnd());
  const written = join(target, '.hued');
  console.log(existsSync(written) ? readFileSync(written, 'utf8').trimEnd() : 'no .hued written');
  console.log(problems.length ? `page errors:\n${problems.join('\n')}` : 'page errors: none');
  return code === 0 && !problems.length && existsSync(written) ? 0 : 1;
}

main().then(
  code => cleanup().then(() => process.exit(code)),
  error => { console.error(error.stack || error); return cleanup().then(() => process.exit(1)); },
);
