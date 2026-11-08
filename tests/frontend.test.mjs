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
class Element {
  constructor(tag) { this.tagName = tag; this.style = {}; this.children = []; this.events = {}; this.value = ''; }
  setAttribute(name, value) { this[name] = value; }
  appendChild(element) { this.children.push(element); }
  append(...elements) { this.children.push(...elements); }
  replaceChildren(...elements) { this.children = [...elements]; }
  addEventListener(name, listener) { this.events[name] = listener; }
  removeEventListener(name) { delete this.events[name]; }
}
const documentEvents = new Element('document');
const windowEvents = new Element('window');
const context = vm.createContext({
  document: Object.assign(documentEvents, { createElement: (tag) => new Element(tag) }),
  window: windowEvents,
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
assert.equal(extensions.size, 8, 'all eight extension entrypoints register');

const stack = sourceModule(path.join(root, 'hybs_load_lora.js')).namespace;
const tree = stack.loraTree(['NONE', 'animals/cat.safetensors', 'styles/ink/cat.safetensors', 'windows\\nested\\file.safetensors']);
assert.equal(tree.folders.size, 3);
assert.equal(tree.folders.get('styles').folders.get('ink').files[0].name, 'styles/ink/cat.safetensors');
assert.equal(tree.folders.get('windows').folders.get('nested').files[0].name, 'windows\\nested\\file.safetensors');
assert.equal(stack.nextStrength(19.99, 1), 20);
assert.equal(stack.nextStrength(20, 1), 20);
assert.equal(stack.nextStrength(-20, -1), -20);
assert.equal(stack.nextStrength(0.1, 1), 0.11);
const heldButton = new Element('button');
let heldSteps = 0, heldBegins = 0, heldEnds = 0;
const cleanupHold = stack.bindHold(heldButton, () => heldSteps++, () => heldBegins++, () => heldEnds++);
heldButton.events.pointerdown({ button: 0, preventDefault() {}, pointerId: 1 });
assert.equal(heldSteps, 1);
const delay = [...timers]; timers.clear(); delay.forEach(([, fn]) => fn());
for (const fn of timers.values()) { fn(); fn(); }
assert.equal(heldSteps, 3);
heldButton.events.pointercancel();
assert.equal(timers.size, 0);
assert.equal(heldBegins, heldEnds);
heldButton.events.click({ detail: 0 });
assert.equal(heldSteps, 4, 'keyboard activation changes once');
heldButton.events.pointerdown({ button: 0, preventDefault() {}, pointerId: 2 });
windowEvents.events.blur();
assert.equal(timers.size, 0, 'blur cancels repetition');
cleanupHold();
assert.equal(heldBegins, heldEnds);
assert.equal(Object.keys(heldButton.events).length, 0);

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
  addDOMWidget(name, type, element, options) {
    const widget = this.addWidget(type, name, '', () => {}, options);
    widget.element = element;
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

// Headings never become serialized COMBO values, even if an event is dispatched manually.
const headingExtension = extensions.get('HYBS.ResolutionSelector.Headings');
class ResolutionNode extends TestNode {}
await headingExtension.beforeRegisterNodeDef(ResolutionNode, {
  name: 'HYBS_ResolutionSelector', input: { required: { resolution: ['COMBO', {
    hybs_resolution_entries: ['1024 equivalent', [896, 1152], '1280 equivalent', [1280, 1280]],
  }] } },
});
const resolutionNode = new ResolutionNode();
const canonical = resolutionNode.addWidget('combo', 'resolution', '896x1152', () => {});
resolutionNode.onNodeCreated();
const resolutionDisplay = widget(resolutionNode, 'resolution groups');
const select = resolutionDisplay.element.children[0];
assert.equal(select.children[0].disabled, true);
assert.equal(select.children[2].disabled, true);
assert.equal(select.value, '896x1152');
select.value = '__hybs_heading_0'; select.events.change({});
assert.equal(canonical.value, '896x1152');
assert.equal(select.value, '896x1152');
select.value = '1280x1280'; select.events.change({});
assert.equal(canonical.value, '1280x1280');
assert.equal(resolutionDisplay.serialize, false);
assert.equal(canonical.type, 'hidden');
canonical.value = '896x1152'; resolutionNode.onConfigure();
assert.equal(select.value, '896x1152');
class LegacyResolutionNode extends TestNode {}
await headingExtension.beforeRegisterNodeDef(LegacyResolutionNode, {
  name: 'HYBS_ResolutionSelector', input: { required: { resolution: ['COMBO', {
    hybs_resolution_entries: [[896, 1152]],
  }] } },
});
const legacyResolution = new LegacyResolutionNode();
assert.equal(legacyResolution.onNodeCreated, undefined);

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
const stackNode = await nodeFor('HYBS.LoadLoRAStack', 'HYBS_LoadLoRAStack', '[]');
stackNode.addWidget('combo', 'lora_name', 'NONE', () => {}, { values: ['NONE', 'a', 'b'] });
stackNode.addWidget('number', 'strength_model', 1, () => {});
stackNode.addWidget('number', 'strength_clip', 1, () => {});
stackNode.onNodeCreated();
const stackPanel = widget(stackNode, 'hybs_lora_controls').element;
const descendants = (element) => [element, ...element.children.flatMap(descendants)];
const clickStack = (text) => descendants(stackPanel).find(el => el.textContent === text).events.click({ detail: 1 });
clickStack('Add LoRA'); clickStack('Add LoRA'); clickStack('Add LoRA');
assert.equal(JSON.parse(widget(stackNode, 'selection').value).length, 3);
stackNode._hybsLoRAUI.entries[1].lora_name = 'b';
stackNode._hybsLoRAUI.entries[1].strength_model = 0.45;
const stackSwitch = descendants(stackPanel).filter(el => el.role === 'switch')[1];
stackSwitch.events.click({ detail: 1 });
assert.equal(JSON.parse(widget(stackNode, 'selection').value)[1].enabled, false);
clickStack('Remove');
assert.equal(JSON.parse(widget(stackNode, 'selection').value)[0].lora_name, 'b');
assert.equal(JSON.parse(widget(stackNode, 'selection').value)[0].strength_model, 0.45);
const stackSaved = widget(stackNode, 'selection').value;
clickStack('Remove'); clickStack('Remove');
assert.equal(widget(stackNode, 'selection').value, '[]');
assert.equal(widget(stackNode, 'hybs_lora_controls').computeSize()[1], 44);
widget(stackNode, 'selection').value = stackSaved;
stackNode.onConfigure();
assert.equal(stackNode._hybsLoRAUI.entries.length, 2);
assert.equal(stackNode._hybsLoRAUI.entries[0].strength_model, 0.45);
assert.equal(stackNode._hybsLoRAUI.entries[0].enabled, false);
const restoredSwitch = descendants(stackPanel).find(el => el.role === 'switch');
restoredSwitch.events.click({ detail: 1 });
assert.equal(JSON.parse(widget(stackNode, 'selection').value)[0].enabled, true);
assert.equal(JSON.parse(widget(stackNode, 'selection').value)[0].lora_name, 'b');
widget(stackNode, 'selection').value = '';
widget(stackNode, 'lora_name').value = 'a';
widget(stackNode, 'strength_model').value = 0.6;
stackNode.onConfigure();
assert.equal(stackNode._hybsLoRAUI.entries[0].lora_name, 'a');
assert.equal(stackNode._hybsLoRAUI.entries[0].strength_model, 0.6);
assert.equal(stackNode._hybsLoRAUI.entries[0].enabled, true);
stackNode.onRemoved();

console.log('PASS: eight extensions, LoRA stack add/remove/restore/legacy, resolution headings and legacy values, numeric normalization and restore, native counts, user size, row deletion/addition, store cleanup, linked outputs, cascade, same-title group replacement');
