// Run with: node --experimental-vm-modules tests/frontend.test.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../web/js');
const extensions = new Map();
const timers = new Map();
let timerId = 0;
const graph = {
  _nodes: [], _groups: [], links: {}, setDirtyCanvas() {},
  getNodeById(id) { return this._nodes.find((node) => node.id === id); },
};
const app = { graph, registerExtension(extension) { extensions.set(extension.name, extension); } };
const context = vm.createContext({
  LiteGraph: { ALWAYS: 0 }, console, Date,
  setTimeout(fn) { const id = ++timerId; timers.set(id, fn); return id; },
  clearTimeout(id) { timers.delete(id); },
  setInterval(fn) { const id = ++timerId; timers.set(id, fn); return id; },
  clearInterval(id) { timers.delete(id); },
});
const appModule = new vm.SyntheticModule(['app'], function () { this.setExport('app', app); }, { context });
const modules = new Map();
function sourceModule(filename) {
  if (!modules.has(filename)) {
    modules.set(filename, new vm.SourceTextModule(fs.readFileSync(filename, 'utf8'), { context, identifier: filename }));
  }
  return modules.get(filename);
}
for (const filename of fs.readdirSync(root).filter((name) => name.endsWith('.js'))) {
  const module = sourceModule(path.join(root, filename));
  await module.link((specifier, parent) => {
    const resolved = path.resolve(path.dirname(parent.identifier), specifier);
    if (resolved.endsWith(path.join('scripts', 'app.js'))) return appModule;
    assert.ok(resolved.startsWith(root + path.sep), `Import escapes extension root: ${resolved}`);
    return sourceModule(resolved);
  });
  await module.evaluate();
}
assert.equal(extensions.size, 6, 'all six extension entrypoints register');

class TestNode {
  constructor(selection = '[]') {
    this.widgets = [];
    this.store = new Map();
    this.outputs = Array.from({ length: 21 }, (_, i) => ({ name: i ? `prompt_${i}` : 'IMAGE', links: [] }));
    this.properties = {};
    this.size = [300, 240];
    this.graph = graph;
    this.id = graph._nodes.length + 100;
    this.addWidget('string', 'selection', selection, () => {});
    this.onNodeCreated?.();
    graph._nodes.push(this);
    this.onAdded?.();
  }
  addWidget(type, name, initial, callback, options = {}) {
    // Nodes 2.0 preserves same-name values until removeWidget unregisters them.
    let state = this.store.get(name);
    if (!state) { state = { value: initial }; this.store.set(name, state); }
    const widget = { type, name, callback, options };
    Object.defineProperty(widget, 'value', { get() { return state.value; }, set(value) { state.value = value; } });
    this.widgets.push(widget);
    return widget;
  }
  removeWidget(widget) { this.store.delete(widget.name); this.widgets.splice(this.widgets.indexOf(widget), 1); }
  computeSize() { return [300, this.widgets.filter((w) => !w.hidden).length * 30 + 40]; }
  setSize(size) { this.size = size; this.onResize?.(size); }
  addOutput(name, type) { this.outputs.push({ name, type, links: [] }); }
  removeOutput(index) { this.outputs.splice(index, 1); }
}
async function nodeFor(extensionName, nodeId, selection) {
  class Node extends TestNode {}
  Node.prototype.comfyClass = nodeId;
  await extensions.get(extensionName).beforeRegisterNodeDef(Node, {
    name: nodeId, input: { required: { selection: ['STRING', { all: ['a', 'b', 'c'] }] } },
  });
  return new Node(selection);
}
const widget = (node, name) => node.widgets.find((w) => w.name === name);
function change(node, name, value) { const w = widget(node, name); assert.ok(w, name); w.value = value; w.callback(value); }
function assertNoLeaks(node) {
  assert.equal(node.store.size, node.widgets.length, 'widget store and live list stay aligned');
  assert.equal(new Set(node.widgets.map((w) => w.name)).size, node.widgets.length, 'widget names stay unique');
}
function flushTimeouts() {
  const pending = [...timers]; timers.clear();
  for (const [, fn] of pending) fn();
}

for (const [kind, id, values, expected] of [
  ['Double', 'HYBS_DoubleList', '[0,1.25,-2.5]', [0, 1.25, -2.5]],
  ['Int', 'HYBS_IntList', '[0,1.8,-2.5]', [0, 1, -2]],
]) {
  const node = await nodeFor(`HYBS.${kind}List`, id, values);
  assert.deepEqual(JSON.parse(widget(node, 'selection').value), expected);
  assert.equal(widget(node, 'selected count').value, 3);
  assert.equal(widget(node, 'selected count').options.read_only, true);
  assert.equal(widget(node, 'selected count').options.disabled, true);
  change(node, 'add value', 'add');
  assert.equal(JSON.parse(widget(node, 'selection').value).length, 4);
  change(node, 'remove value', 'remove');
  assert.deepEqual(JSON.parse(widget(node, 'selection').value), expected);
  change(node, 'value_0', Infinity);
  assert.equal(JSON.parse(widget(node, 'selection').value)[0], 0);
  widget(node, 'selection').value = '[9,8]'; node.onConfigure();
  assert.deepEqual(JSON.parse(widget(node, 'selection').value), [9, 8]);
  assert.equal(widget(node, 'value_0').value, 9, 'configure replaces store values');
  assert.equal(widget(node, 'value_0').serialize, false);
  node.setSize([500, 600]); flushTimeouts();
  assert.deepEqual(Array.from(node.size), [500, 600], "delayed compact preserves manual resize");
  assert.deepEqual(Array.from(node._hybsUserSize), [500, 600], 'internal resizing preserves user dimensions');
  assertNoLeaks(node);
  node.onRemoved();
}

const models = await nodeFor('HYBS.DiffusionModelList', 'HYBS_DiffusionModelList', '["a","b"]');
change(models, 'model_0', 'none');
assert.equal(widget(models, 'model_0').value, 'b', 'removing first row keeps the second row value');
assert.deepEqual(JSON.parse(widget(models, 'selection').value), ['b']);
change(models, 'model_1', 'c');
assert.deepEqual(JSON.parse(widget(models, 'selection').value), ['b', 'c']);
assertNoLeaks(models); models.onRemoved();

const loras = await nodeFor('HYBS.LoRAList', 'HYBS_LoRAList', '[null,"a","b"]');
change(loras, 'lora_1', 'NONE');
assert.deepEqual(JSON.parse(widget(loras, 'selection').value), [null, 'b']);
assert.equal(widget(loras, 'lora_1').value, 'b');
change(loras, 'add lora', 'add');
change(loras, 'lora_2', 'c');
assert.deepEqual(JSON.parse(widget(loras, 'selection').value), [null, 'b', 'c']);
assertNoLeaks(loras);
widget(loras, 'selection').value = '["",null,"a", "", "b"]'; loras.onConfigure();
assert.deepEqual(JSON.parse(widget(loras, 'selection').value), [null, 'a', 'b']);
assert.equal(widget(loras, 'lora_1').value, 'a');
assert.equal(widget(loras, 'lora_2').value, 'b');
assertNoLeaks(loras); loras.onRemoved();

const prompts = await nodeFor('HYBS.LoadImagePromptMetadataAdvance', 'HYBS_LoadImagePromptMetadataAdvance', '["10","20"]');
change(prompts, 'node_id_0', '');
assert.equal(widget(prompts, 'node_id_0').value, '20');
assert.deepEqual(JSON.parse(widget(prompts, 'selection').value), ['20']);
prompts.outputs[4].links = [123]; flushTimeouts();
assert.equal(prompts.outputs.length, 5, 'connected output slots remain intact');
assertNoLeaks(prompts); prompts.onRemoved();

// Same-title group replacement used to keep callbacks bound to the removed group.
const parent = { id: 1, comfyClass: 'HYBS_GroupBypasser_Parent', outputs: [{ links: [1] }], mode: 0 };
const child = { id: 2, comfyClass: 'HYBS_GroupBypasser_Child', outputs: [{ links: [] }], mode: 0 };
graph._nodes = [parent, child];
graph.links = new Map([[1, { target_id: 2 }]]);
graph._groups = [
  { title: 'Parent', _nodes: [parent], recomputeInsideNodes() {} },
  { title: 'Child', _nodes: [child], recomputeInsideNodes() {} },
];
const panel = await nodeFor('HYBS.GroupBypasser.PanelOnly', 'HYBS_GroupBypasser_Panel', '[]');
change(panel, '[Main] Parent (cascade)', true);
assert.equal(parent.mode, 4); assert.equal(child.mode, 4);
assert.equal(widget(panel, '[Main] Child').value, true);
change(panel, '[Main] Parent (cascade)', false);
assert.equal(parent.mode, 0); assert.equal(child.mode, 0);
const replacement = { id: 3, mode: 0 };
graph._groups[1] = { title: 'Child', _nodes: new Set([replacement]), recomputeInsideNodes() {} };
panel._hybsPoll();
change(panel, '[Main] Child', true);
assert.equal(replacement.mode, 4); assert.equal(child.mode, 0);
panel.onRemoved();
console.log('PASS: six extensions, numeric normalization and restore, native counts, user size, row deletion/addition, store cleanup, linked outputs, cascade, same-title group replacement');
