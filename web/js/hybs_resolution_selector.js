import { app } from "../../../scripts/app.js";

const NODE_ID = "HYBS_ResolutionSelector";

function attachGroupedSelector(node, entries) {
  const resolution = node.widgets?.find((widget) => widget.name === "resolution");
  if (!resolution || typeof node.addDOMWidget !== "function") return;

  const container = document.createElement("div");
  container.style.cssText = "width:100%;height:36px;box-sizing:border-box;padding:2px 8px;";
  const select = document.createElement("select");
  select.setAttribute("aria-label", "resolution");
  select.style.cssText = "width:100%;height:30px;box-sizing:border-box;border:1px solid var(--border-color,#555);border-radius:4px;background:var(--comfy-input-bg,#222);color:var(--input-text,#ddd);font:inherit;padding:3px 6px;";
  const selectable = new Set();
  for (const [index, entry] of entries.entries()) {
    const option = document.createElement("option");
    if (typeof entry === "string") {
      option.textContent = entry;
      option.value = `__hybs_heading_${index}`;
      option.disabled = true;
      option.style.color = "#888";
    } else if (Array.isArray(entry) && entry.length === 2) {
      option.value = `${entry[0]}x${entry[1]}`;
      option.textContent = `${entry[0]} × ${entry[1]}`;
      selectable.add(option.value);
    } else {
      continue;
    }
    select.appendChild(option);
  }
  container.appendChild(select);

  const sync = () => {
    select.value = resolution.value;
  };
  select.addEventListener("change", (event) => {
    if (!selectable.has(select.value)) {
      sync();
      return;
    }
    resolution.value = select.value;
    resolution.callback?.(resolution.value, app.canvas, node, undefined, event);
    node.graph?.setDirtyCanvas?.(true, true);
  });

  // Keep the original COMBO as the sole serialized input for workflow compatibility.
  const display = node.addDOMWidget("resolution groups", "hybs_resolution_groups", container, {
    serialize: false,
    hideOnZoom: false,
    getMinHeight: () => 36,
    getMaxHeight: () => 36,
    getValue: () => resolution.value,
    setValue(value) {
      if (selectable.has(value)) resolution.value = value;
      sync();
    },
  });
  display.serialize = false;
  resolution.hidden = true;
  resolution.type = "hidden";
  resolution.computeSize = () => [0, -4];
  node._hybsResolutionRefresh = sync;
  sync();
}

app.registerExtension({
  name: "HYBS.ResolutionSelector.Headings",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData?.name !== NODE_ID) return;
    const input = nodeData.input?.required?.resolution || nodeData.input?.optional?.resolution;
    const entries = input?.[1]?.hybs_resolution_entries;
    if (!Array.isArray(entries) || !entries.some((entry) => typeof entry === "string")) return;

    const originalCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function (...args) {
      originalCreated?.apply(this, args);
      attachGroupedSelector(this, entries);
    };
    const originalConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function (...args) {
      originalConfigure?.apply(this, args);
      this._hybsResolutionRefresh?.();
    };
    const originalDraw = nodeType.prototype.onDrawForeground;
    nodeType.prototype.onDrawForeground = function (...args) {
      originalDraw?.apply(this, args);
      this._hybsResolutionRefresh?.();
    };
  },
});
