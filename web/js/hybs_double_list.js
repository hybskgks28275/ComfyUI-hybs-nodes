import { app } from "../../scripts/app.js";

const CT_DOUBLE_LIST = "HYBS_DoubleList";
const HIDDEN_WIDGET_SIZE = [0, -4];
const COUNT_WIDGET_NAME = "selected count";
const CONTROL_WIDGET_NAMES = new Set(["add value", "remove value"]);

function isValueWidget(widget) {
  return typeof widget?.name === "string" && widget.name.startsWith("value_");
}

function isControlWidget(widget) {
  return typeof widget?.name === "string" && CONTROL_WIDGET_NAMES.has(widget.name);
}

function findWidget(node, name) {
  return node.widgets?.find((widget) => widget?.name === name);
}

function hideWidget(widget) {
  if (!widget) {
    return;
  }
  widget.hidden = true;
  widget.type = "hidden";
  widget.computeSize = () => HIDDEN_WIDGET_SIZE;
}

function findValueWidgets(node) {
  return node.widgets?.filter(isValueWidget) || [];
}

function findCountWidget(node) {
  return findWidget(node, COUNT_WIDGET_NAME);
}

function ensureCountWidget(node) {
  let widget = findCountWidget(node);
  if (widget) {
    return widget;
  }

  widget = {
    name: COUNT_WIDGET_NAME,
    type: "hybs_count_display",
    value: 0,
    options: { serialize: false },
    computeSize: (width) => [width, 24],
    draw(ctx, _node, width, y, height) {
      const margin = 15;
      const textY = y + Math.floor(height * 0.68);
      ctx.save();
      ctx.fillStyle = "rgba(255,255,255,0.08)";
      ctx.fillRect(margin, y + 2, Math.max(0, width - margin * 2), height - 4);
      ctx.fillStyle = "#aaa";
      ctx.font = "12px sans-serif";
      ctx.textAlign = "left";
      ctx.fillText("count", margin + 8, textY);
      ctx.fillStyle = "#fff";
      ctx.textAlign = "right";
      ctx.fillText(String(this.value ?? 0), width - margin - 8, textY);
      ctx.restore();
    },
  };
  node.widgets = node.widgets || [];
  node.widgets.push(widget);
  return widget;
}

function setCountWidget(node, count) {
  const widget = ensureCountWidget(node);
  widget.value = count;
}

function resetWidgetLayout(node) {
  for (const widget of node.widgets || []) {
    delete widget.y;
    delete widget.last_y;
    delete widget.computedHeight;
  }
}

function getStoredUserSize(node) {
  if (!Array.isArray(node._hybsUserSize) || node._hybsUserSize.length !== 2) {
    return null;
  }
  return node._hybsUserSize;
}

function saveUserSize(node, size) {
  if (!Array.isArray(size) || size.length !== 2) {
    return;
  }
  node._hybsUserSize = [size[0], size[1]];
}

function applyNodeSize(node, mode = "preserve", baseSize = null) {
  if (!Array.isArray(node.size) || typeof node.computeSize !== "function") {
    return;
  }

  resetWidgetLayout(node);
  const computedSize = node.computeSize();
  const storedSize = getStoredUserSize(node);
  const currentWidth =
    storedSize?.[0] || baseSize?.[0] || node.size[0] || computedSize[0];
  let targetHeight = computedSize[1];

  if (mode === "preserve") {
    const currentHeight =
      storedSize?.[1] || baseSize?.[1] || node.size[1] || computedSize[1];
    targetHeight = Math.max(currentHeight, computedSize[1]);
  }

  node.setSize([currentWidth, targetHeight]);
}

function queueInitialCompact(node) {
  if (node._hybsInitialCompactQueued) {
    return;
  }
  node._hybsInitialCompactQueued = true;
  const baseSize = Array.isArray(node.size) ? [node.size[0], node.size[1]] : null;

  const compact = () => {
    applyNodeSize(node, "compact", baseSize);
    app.graph?.setDirtyCanvas?.(true, true);
  };

  setTimeout(compact, 0);
  setTimeout(compact, 100);
  setTimeout(compact, 300);
}

function getValues(node) {
  return findValueWidgets(node).map((widget) => Number(widget.value ?? 0));
}

function storeSelection(node, selectionWidget) {
  const values = getValues(node).map((value) => (Number.isFinite(value) ? value : 0.0));
  selectionWidget.value = JSON.stringify(values);
  setCountWidget(node, values.length);
  return values;
}

function removeValueWidgets(node) {
  let widgetIndex = 0;
  while (widgetIndex < node.widgets.length) {
    const widget = node.widgets[widgetIndex];
    if (isValueWidget(widget)) {
      node.widgets.splice(widgetIndex, 1);
      continue;
    }
    widgetIndex += 1;
  }
}

function removeControlWidgets(node) {
  let widgetIndex = 0;
  while (widgetIndex < node.widgets.length) {
    const widget = node.widgets[widgetIndex];
    if (isControlWidget(widget)) {
      node.widgets.splice(widgetIndex, 1);
      continue;
    }
    widgetIndex += 1;
  }
}

function addControlWidgets(node, selectionWidget) {
  removeControlWidgets(node);

  const addButton = node.addWidget("button", "add value", "add", () => addValue(node, selectionWidget));
  addButton.options = addButton.options || {};
  addButton.options.serialize = false;

  const removeButton = node.addWidget("button", "remove value", "remove", () => removeLastValue(node, selectionWidget));
  removeButton.options = removeButton.options || {};
  removeButton.options.serialize = false;
}

function addValueWidget(node, selectionWidget, value = 1.0) {
  const index = findValueWidgets(node).length;
  const widget = node.addWidget(
    "number",
    `value_${index}`,
    Number.isFinite(Number(value)) ? Number(value) : 1.0,
    () => {
      storeSelection(node, selectionWidget);
      app.graph?.setDirtyCanvas?.(true, true);
    },
    { min: -20.0, max: 20.0, step: 0.05, precision: 3 },
  );
  widget.label = `value ${index + 1}`;
  widget.options.serialize = false;
  return widget;
}

function refreshFromSelection(node, selectionWidget, mode = "preserve") {
  const baseSize = Array.isArray(node.size) ? [node.size[0], node.size[1]] : null;
  removeValueWidgets(node);
  removeControlWidgets(node);

  let values = [];
  try {
    values = JSON.parse(selectionWidget.value || "[1.0]");
  } catch (_error) {
    values = [1.0];
  }
  if (!Array.isArray(values) || values.length === 0) {
    values = [1.0];
  }

  values.forEach((value) => addValueWidget(node, selectionWidget, value));
  addControlWidgets(node, selectionWidget);
  storeSelection(node, selectionWidget);
  applyNodeSize(node, mode, baseSize);
  app.graph?.setDirtyCanvas?.(true, true);
}

function addValue(node, selectionWidget) {
  const baseSize = Array.isArray(node.size) ? [node.size[0], node.size[1]] : null;
  removeControlWidgets(node);
  addValueWidget(node, selectionWidget, 1.0);
  addControlWidgets(node, selectionWidget);
  storeSelection(node, selectionWidget);
  applyNodeSize(node, "preserve", baseSize);
  app.graph?.setDirtyCanvas?.(true, true);
}

function removeLastValue(node, selectionWidget) {
  const widgets = findValueWidgets(node);
  if (widgets.length <= 1) {
    return;
  }

  const baseSize = Array.isArray(node.size) ? [node.size[0], node.size[1]] : null;
  const last = widgets[widgets.length - 1];
  const index = node.widgets.indexOf(last);
  if (index >= 0) {
    node.widgets.splice(index, 1);
  }
  addControlWidgets(node, selectionWidget);
  storeSelection(node, selectionWidget);
  applyNodeSize(node, "preserve", baseSize);
  app.graph?.setDirtyCanvas?.(true, true);
}

app.registerExtension({
  name: "HYBS.DoubleList",

  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData?.name !== CT_DOUBLE_LIST) {
      return;
    }

    const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function (...args) {
      originalOnNodeCreated?.apply(this, args);
      const selectionWidget = findWidget(this, "selection");
      if (!selectionWidget) {
        return;
      }
      hideWidget(selectionWidget);
      ensureCountWidget(this);
      refreshFromSelection(this, selectionWidget, "compact");
      this._hybsNeedsInitialCompact = true;
      queueInitialCompact(this);
    };

    const originalOnConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function (...args) {
      originalOnConfigure?.apply(this, args);
      const selectionWidget = findWidget(this, "selection");
      if (!selectionWidget) {
        return;
      }
      hideWidget(selectionWidget);
      ensureCountWidget(this);
      refreshFromSelection(this, selectionWidget, "preserve");
    };

    const originalOnResize = nodeType.prototype.onResize;
    nodeType.prototype.onResize = function (size) {
      originalOnResize?.apply(this, [size]);
      saveUserSize(this, size);
      resetWidgetLayout(this);
    };

    const originalOnDrawForeground = nodeType.prototype.onDrawForeground;
    nodeType.prototype.onDrawForeground = function (...args) {
      if (this._hybsNeedsInitialCompact) {
        this._hybsNeedsInitialCompact = false;
        applyNodeSize(this, "compact");
      }
      return originalOnDrawForeground?.apply(this, args);
    };
  },
});
