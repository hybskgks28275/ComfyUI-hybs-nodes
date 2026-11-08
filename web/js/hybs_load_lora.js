import { app, findWidget, hideWidget } from "./common/widgets.js";

const NODE_ID = "HYBS_LoadLoRAStack";
const NONE = "NONE";

export function loraTree(names) {
  const root = { folders: new Map(), files: [] };
  for (const name of names) {
    if (typeof name !== "string" || !name || name === NONE) continue;
    const parts = name.replaceAll("\\", "/").split("/");
    let branch = root;
    for (const folder of parts.slice(0, -1)) {
      if (!branch.folders.has(folder)) branch.folders.set(folder, { folders: new Map(), files: [] });
      branch = branch.folders.get(folder);
    }
    branch.files.push({ label: parts.at(-1), name });
  }
  return root;
}

export function nextStrength(value, direction) {
  return Math.max(-20, Math.min(20, Math.round((Number(value) + direction * 0.01) * 100) / 100));
}

function button(label, action) {
  const element = document.createElement("button");
  element.type = "button";
  element.textContent = label;
  element.style.cssText = "cursor:pointer;padding:5px 9px;color:inherit;background:var(--comfy-input-bg,#333);border:1px solid var(--border-color,#666);border-radius:4px;";
  if (action) element.addEventListener("click", action);
  return element;
}

function pickLoRA(node, source, commit) {
  node._hybsLoRAUI.closePicker?.();
  const dialog = document.createElement("dialog");
  dialog.setAttribute("aria-label", "Choose LoRA by folder");
  dialog.style.cssText = "width:min(640px,85vw);max-height:80vh;padding:16px;background:var(--comfy-menu-bg,#222);color:var(--input-text,#eee);border:1px solid #666;border-radius:8px;";
  const heading = document.createElement("h3");
  heading.textContent = "LoRA — folders";
  const search = document.createElement("input");
  search.type = "search";
  search.placeholder = "Search folders / filenames…";
  search.setAttribute("aria-label", "Search LoRA folders and filenames");
  search.style.cssText = "box-sizing:border-box;width:100%;padding:8px;margin:8px 0;";
  const tree = document.createElement("div");
  tree.style.cssText = "overflow:auto;max-height:50vh;min-height:100px;";
  const close = () => {
    dialog.remove();
    if (node._hybsLoRAUI?.closePicker === close) node._hybsLoRAUI.closePicker = null;
  };
  node._hybsLoRAUI.closePicker = close;
  const choose = (name) => { commit(source, name); close(); };
  const none = button("NONE — no LoRA", () => choose(NONE));
  const cancel = button("Close", close);
  cancel.style.marginLeft = "8px";
  const render = () => {
    tree.replaceChildren();
    const options = typeof source.options?.values === "function" ? source.options.values() : source.options?.values || [];
    const query = search.value.trim().toLocaleLowerCase();
    const names = options.filter((name) => String(name).toLocaleLowerCase().includes(query));
    const root = loraTree(names);
    const selected = String(source.value).replaceAll("\\", "/");
    const append = (parent, branch, prefix = "") => {
      for (const [folder, child] of [...branch.folders].sort(([a], [b]) => a.localeCompare(b))) {
        const path = `${prefix}${folder}/`;
        const details = document.createElement("details");
        details.open = Boolean(query) || selected.startsWith(path);
        const summary = document.createElement("summary");
        summary.textContent = folder;
        summary.style.cssText = "cursor:pointer;padding:6px 0;";
        const children = document.createElement("div");
        children.style.cssText = "margin-left:18px;border-left:1px solid #555;padding-left:10px;";
        details.append(summary, children);
        parent.append(details);
        append(children, child, path);
      }
      for (const file of branch.files.sort((a, b) => a.label.localeCompare(b.label))) {
        const entry = button(file.label, () => choose(file.name));
        entry.title = file.name;
        entry.style.cssText += "display:block;text-align:left;width:100%;margin:3px 0;overflow-wrap:anywhere;";
        entry.setAttribute("aria-pressed", String(source.value === file.name));
        if (source.value === file.name) entry.style.borderColor = "#7ab5ff";
        parent.append(entry);
      }
    };
    append(tree, root);
    if (!root.folders.size && !root.files.length) tree.textContent = "No LoRA files found.";
  };
  search.addEventListener("input", render);
  dialog.addEventListener("cancel", (event) => { event.preventDefault(); close(); });
  dialog.addEventListener("click", (event) => { if (event.target === dialog) close(); });
  dialog.append(heading, none, cancel, search, tree);
  document.body.append(dialog);
  render();
  dialog.showModal();
  search.focus();
}

// A hold is one undoable edit. Pointer capture handles release outside the button.
export function bindHold(element, change, begin, end) {
  let delay = null;
  let interval = null;
  let active = false;
  const stop = () => {
    clearTimeout(delay);
    clearInterval(interval);
    delay = interval = null;
    if (active) { active = false; end(); }
  };
  const down = (event) => {
    if (event.button !== 0) return;
    event.preventDefault();
    stop();
    active = true;
    begin();
    element.setPointerCapture?.(event.pointerId);
    change();
    delay = setTimeout(() => { interval = setInterval(change, 60); }, 350);
  };
  const visibility = () => { if (document.hidden) stop(); };
  const click = (event) => {
    // Keyboard / assistive activation has no preceding pointerdown.
    if (event.detail === 0) { begin(); try { change(); } finally { end(); } }
  };
  element.addEventListener("pointerdown", down);
  element.addEventListener("pointerup", stop);
  element.addEventListener("pointercancel", stop);
  element.addEventListener("lostpointercapture", stop);
  element.addEventListener("click", click);
  window.addEventListener("blur", stop);
  document.addEventListener("visibilitychange", visibility);
  return () => {
    stop();
    element.removeEventListener("pointerdown", down);
    element.removeEventListener("pointerup", stop);
    element.removeEventListener("pointercancel", stop);
    element.removeEventListener("lostpointercapture", stop);
    element.removeEventListener("click", click);
    window.removeEventListener("blur", stop);
    document.removeEventListener("visibilitychange", visibility);
  };
}

function installUI(node) {
  if (node._hybsLoRAUI) return;
  const lora = findWidget(node, "lora_name");
  const strengths = [findWidget(node, "strength_model"), findWidget(node, "strength_clip")];
  const selection = findWidget(node, "selection");
  if (!lora || !selection || strengths.some((widget) => !widget)) return;
  const state = node._hybsLoRAUI = { cleanups: [], sync: [], entries: [], snapshot: null };
  const readEntries = () => {
    if (!selection.value) return [{ lora_name: lora.value || NONE, strength_model: strengths[0].value, strength_clip: strengths[1].value, enabled: true }];
    try {
      const entries = JSON.parse(selection.value);
      if (!Array.isArray(entries)) throw new Error("Expected an array");
      return entries.map((entry) => ({ lora_name: entry.lora_name || NONE, strength_model: Number(entry.strength_model ?? 1), strength_clip: Number(entry.strength_clip ?? 1), enabled: entry.enabled !== false }));
    } catch (error) {
      console.error("[HYBS] Invalid LoRA stack:", error);
      return [];
    }
  };
  const save = () => {
    selection.value = JSON.stringify(state.entries);
    state.snapshot = selection.value;
    selection.callback?.(selection.value);
    const first = state.entries[0];
    lora.value = first?.enabled === false ? NONE : first?.lora_name || NONE;
    strengths[0].value = first?.strength_model ?? 1;
    strengths[1].value = first?.strength_clip ?? 1;
  };
  const dirty = () => node.graph?.setDirtyCanvas?.(true, true);
  const begin = () => node.graph?.beforeChange?.();
  const end = () => { node.graph?.afterChange?.(); dirty(); };
  const setValue = (widget, value) => {
    widget.value = value;
    widget.callback?.(value, app.canvas, node, undefined, undefined);
    state.sync.forEach((sync) => sync());
    dirty();
  };
  const commit = (widget, value) => { begin(); try { setValue(widget, value); } finally { end(); } };
  const panel = document.createElement("div");
  panel.style.cssText = "display:flex;flex-direction:column;gap:8px;padding:6px;box-sizing:border-box;color:var(--input-text,#eee);font:12px sans-serif;";
  panel.addEventListener("pointerdown", (event) => event.stopPropagation());
  let ui;
  let height = 44;
  const resize = () => {
    height = 44 + state.entries.length * 88;
    if (ui) node.setSize([Math.max(node.size[0], 480), node.computeSize()[1]]);
    dirty();
  };
  const editRows = (edit) => {
    state.closePicker?.();
    state.cleanups.forEach((cleanup) => cleanup());
    state.cleanups = [];
    begin();
    try { edit(); save(); render(); } finally { end(); }
  };
  const render = () => {
    state.closePicker?.();
    state.cleanups.forEach((cleanup) => cleanup());
    state.cleanups = [];
    state.sync = [];
    panel.replaceChildren();
    const toolbar = document.createElement("div");
    toolbar.style.cssText = "display:flex;align-items:center;gap:8px;";
    const count = document.createElement("span");
    count.textContent = `LoRAs: ${state.entries.length}`;
    toolbar.append(count, button("Add LoRA", () => editRows(() => state.entries.push({ lora_name: NONE, strength_model: 1, strength_clip: 1, enabled: true }))));
    panel.append(toolbar);
    state.entries.forEach((entry, entryIndex) => {
      const proxy = (key) => ({
        get value() { return entry[key]; },
        set value(value) { entry[key] = value; save(); },
        options: lora.options,
      });
      const rowLora = proxy("lora_name");
      const rowStrengths = [proxy("strength_model"), proxy("strength_clip")];
      const enabled = proxy("enabled");
      const toggle = button("", () => commit(enabled, !enabled.value));
      toggle.setAttribute("role", "switch");
      toggle.setAttribute("aria-label", `Enable LoRA ${entryIndex + 1}`);
      toggle.style.minWidth = "44px";
      const picker = button("", () => pickLoRA(node, rowLora, commit));
      picker.style.cssText += "text-align:left;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-height:30px;";
      state.sync.push(() => { picker.textContent = `LoRA ${entryIndex + 1}: ${rowLora.value || NONE}`; picker.title = String(rowLora.value || NONE); });
      const header = document.createElement("div");
      header.style.cssText = "display:flex;gap:6px;align-items:center;";
      picker.style.flex = "1";
      picker.style.minWidth = "0";
      const remove = button("Remove", () => editRows(() => state.entries.splice(entryIndex, 1)));
      remove.setAttribute("aria-label", `Remove LoRA ${entryIndex + 1}`);
      header.append(toggle, picker, remove);
      panel.append(header);
      const strengthGroup = document.createElement("div");
      strengthGroup.style.cssText = "display:grid;grid-template-columns:1fr 1fr;gap:12px;";
      panel.append(strengthGroup);
      state.sync.push(() => {
        toggle.textContent = enabled.value ? "ON" : "OFF";
        toggle.setAttribute("aria-checked", String(enabled.value));
        toggle.style.background = enabled.value ? "#246544" : "var(--comfy-input-bg,#333)";
        strengthGroup.style.opacity = enabled.value ? "1" : "0.5";
        picker.style.opacity = enabled.value ? "1" : "0.5";
      });
      rowStrengths.forEach((widget, index) => {
        const row = document.createElement("div");
        row.style.cssText = "display:flex;align-items:center;gap:4px;min-width:0;";
        const label = document.createElement("label");
        const controlLabel = index === 0 ? "MODEL strength" : "TE / CLIP strength";
        label.textContent = index === 0 ? "MODEL" : "TE / CLIP";
        label.title = controlLabel;
        label.style.cssText = "flex:1;white-space:nowrap;font-size:11px;";
        const input = document.createElement("input");
        input.type = "number";
        input.min = "-20";
        input.max = "20";
        input.step = "0.01";
        input.setAttribute("aria-label", controlLabel);
        input.style.cssText = "width:65px;box-sizing:border-box;padding:4px;";
        const sync = () => { if (document.activeElement !== input) input.value = Number(widget.value).toFixed(2); };
        state.sync.push(sync);
        input.addEventListener("change", () => {
          if (!input.value.trim() || !Number.isFinite(input.valueAsNumber)) { input.value = Number(widget.value).toFixed(2); return; }
          const value = Math.max(-20, Math.min(20, Math.round(input.valueAsNumber * 100) / 100));
          commit(widget, value);
          input.value = value.toFixed(2);
        });
        const minus = button("−");
        const plus = button("+");
        for (const [element, direction] of [[minus, -1], [plus, 1]]) {
          element.setAttribute("aria-label", `${direction < 0 ? "Decrease" : "Increase"} ${controlLabel}`);
          element.style.padding = "4px 7px";
          element.style.touchAction = "none";
          state.cleanups.push(bindHold(element, () => setValue(widget, nextStrength(widget.value, direction)), begin, end));
        }
        row.append(label, minus, input, plus);
        strengthGroup.append(row);
      });
    });
    state.sync.forEach((sync) => sync());
    resize();
  };
  // Keep the backend widgets and their order for workflow/API serialization.
  [lora, ...strengths, selection].forEach(hideWidget);
  ui = node.addDOMWidget("hybs_lora_controls", "hybs_lora_controls", panel, { serialize: false });
  ui.serialize = false;
  ui.computeSize = () => [450, height];
  ui.options = { ...ui.options, serialize: false, getMinHeight: () => height, getMaxHeight: () => height };
  state.restore = () => {
    state.entries = readEntries();
    // Leave legacy workflows untouched until the first edit.
    state.snapshot = selection.value;
    render();
  };
  state.refresh = () => {
    if (selection.value !== state.snapshot) state.restore();
    else state.sync.forEach((sync) => sync());
  };
  state.restore();
}

app.registerExtension({
  name: "HYBS.LoadLoRAStack",
  beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== NODE_ID) return;
    const created = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function (...args) {
      const result = created?.apply(this, args);
      installUI(this);
      return result;
    };
    const configured = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function (...args) {
      const result = configured?.apply(this, args);
      installUI(this);
      this._hybsLoRAUI?.restore();
      return result;
    };
    const draw = nodeType.prototype.onDrawBackground;
    nodeType.prototype.onDrawBackground = function (...args) {
      const result = draw?.apply(this, args);
      this._hybsLoRAUI?.refresh();
      return result;
    };
    const removed = nodeType.prototype.onRemoved;
    nodeType.prototype.onRemoved = function (...args) {
      this._hybsLoRAUI?.closePicker?.();
      this._hybsLoRAUI?.cleanups.forEach((cleanup) => cleanup());
      return removed?.apply(this, args);
    };
  },
});
