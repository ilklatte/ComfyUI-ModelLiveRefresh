import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const source = fs.readFileSync('web/model_live_refresh.js', 'utf8')
  .replace(/^import .*;\n/gm, '');
let extension;
let handler;
let calls = 0;
const app = {
  registerExtension(value) { extension = value; },
  async refreshComboInNodes() { calls++; },
};
const api = { addEventListener(type, fn) { assert.equal(type, 'model_live_refresh.changed'); handler = fn; } };
vm.runInNewContext(source, { app, api, setTimeout, clearTimeout, console });
extension.setup();
handler();
handler();
await new Promise(resolve => setTimeout(resolve, 500));
assert.equal(calls, 1, 'bursty filesystem events should produce one refresh');
console.log('frontend refresh event test passed');
