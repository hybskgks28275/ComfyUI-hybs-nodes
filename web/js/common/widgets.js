import { app } from "../../../../scripts/app.js";

export { app };

export function findWidget(node, name) {
  return node.widgets?.find((widget) => widget?.name === name);
}

export function hideWidget(widget) {
  if (!widget) return;
  widget.hidden = true;
  widget.type = "hidden";
  widget.computeSize = () => [0, -4];
}

export function removeWidget(node, widget) {
  if (!node.widgets?.includes(widget)) return;
  if (typeof node.removeWidget === "function") {
    node.removeWidget(widget);
  } else {
    widget.onRemove?.();
    node.widgets.splice(node.widgets.indexOf(widget), 1);
  }
}

export function removeWidgets(node, predicate) {
  for (const widget of [...(node.widgets || [])]) {
    if (predicate(widget)) removeWidget(node, widget);
  }
}

export function ensureCountWidget(node) {
  let widget = findWidget(node, "selected count");
  if (!widget) {
    widget = node.addWidget("number", "selected count", 0, () => {}, {
      read_only: true, disabled: true, serialize: false, precision: 0,
    });
    widget.serialize = false;
  }
  return widget;
}

export function setCountWidget(node, count) {
  ensureCountWidget(node).value = count;
}

export function resetWidgetLayout(node) {
  for (const widget of node.widgets || []) {
    delete widget.y;
    delete widget.last_y;
    delete widget.computedHeight;
  }
}

function isSize(size) {
  return size?.length === 2 && Number.isFinite(size[0]) && Number.isFinite(size[1]);
}

export function saveUserSize(node, size) {
  if (!node._hybsApplyingSize && isSize(size)) node._hybsUserSize = [size[0], size[1]];
}

export function applyNodeSize(node, mode = "preserve", baseSize = null) {
  if (!isSize(node.size) || typeof node.computeSize !== "function") return;
  resetWidgetLayout(node);
  const computed = node.computeSize();
  const stored = node._hybsUserSize;
  const width = stored?.[0] || baseSize?.[0] || node.size[0] || computed[0];
  const height = mode === "compact" ? computed[1] :
    Math.max(stored?.[1] || baseSize?.[1] || node.size[1] || computed[1], computed[1]);
  node._hybsApplyingSize = true;
  try {
    node.setSize([width, height]);
  } finally {
    node._hybsApplyingSize = false;
  }
}

function queueInitialCompact(node) {
  const baseSize = isSize(node.size) ? [...node.size] : null;
  node._hybsCompactTimers = [0, 100, 300].map((delay) => setTimeout(() => {
    if (node._hybsUserSize) return;
    applyNodeSize(node, "compact", baseSize);
    app.graph?.setDirtyCanvas?.(true, true);
  }, delay));
}

export function installListHooks(nodeType, refresh) {
  const originalCreated = nodeType.prototype.onNodeCreated;
  nodeType.prototype.onNodeCreated = function (...args) {
    originalCreated?.apply(this, args);
    const selection = findWidget(this, "selection");
    if (!selection) return;
    hideWidget(selection);
    ensureCountWidget(this);
    refresh(this, selection, "compact");
    this._hybsNeedsInitialCompact = true;
    queueInitialCompact(this);
  };
  const originalConfigure = nodeType.prototype.onConfigure;
  nodeType.prototype.onConfigure = function (...args) {
    originalConfigure?.apply(this, args);
    const selection = findWidget(this, "selection");
    if (!selection) return;
    hideWidget(selection);
    ensureCountWidget(this);
    refresh(this, selection, "preserve");
  };
  const originalResize = nodeType.prototype.onResize;
  nodeType.prototype.onResize = function (size) {
    originalResize?.apply(this, [size]);
    saveUserSize(this, size);
    resetWidgetLayout(this);
  };
  const originalDraw = nodeType.prototype.onDrawForeground;
  nodeType.prototype.onDrawForeground = function (...args) {
    if (this._hybsNeedsInitialCompact) {
      this._hybsNeedsInitialCompact = false;
      if (!this._hybsUserSize) applyNodeSize(this, "compact");
    }
    return originalDraw?.apply(this, args);
  };
  const originalRemoved = nodeType.prototype.onRemoved;
  nodeType.prototype.onRemoved = function (...args) {
    for (const timer of this._hybsCompactTimers || []) clearTimeout(timer);
    this._hybsCompactTimers = [];
    return originalRemoved?.apply(this, args);
  };
}
