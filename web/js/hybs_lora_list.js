import { app } from "../../scripts/app.js";

const CT_LORA_LIST = "HYBS_LoRAList";
const EMPTY_OPTION = "<select LoRA>";
const NONE_OPTION = "NONE";
const HIDDEN_WIDGET_SIZE = [0, -4];
const COUNT_WIDGET_NAME = "selected count";

function isLoRAWidget(widget) {
  return typeof widget?.name === "string" && widget.name.startsWith("lora_");
}

function isEntryWidget(widget) {
  return isLoRAWidget(widget);
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

function findEntryWidgets(node) {
  return node.widgets?.filter(isEntryWidget) || [];
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

function removeEntryWidgets(node) {
  let widgetIndex = 0;
  while (widgetIndex < node.widgets.length) {
    const widget = node.widgets[widgetIndex];
    if (isEntryWidget(widget)) {
      node.widgets.splice(widgetIndex, 1);
      continue;
    }
    widgetIndex += 1;
  }
}

function getEntries(node) {
  const entries = [];
  for (const widget of node.widgets || []) {
    if (!isLoRAWidget(widget)) {
      continue;
    }

    const index = Number(widget.name.slice("lora_".length));
    const name = String(widget.value || "").trim();
    entries.push({ index, name });
  }

  return entries.sort((a, b) => a.index - b.index);
}

function serializeEntries(entries) {
  return JSON.stringify(
    entries
      .filter((entry) => entry.name && entry.name !== EMPTY_OPTION)
      .map((entry) => (entry.name === NONE_OPTION ? null : entry.name)),
  );
}

function addEntryWidgets(node, selectionWidget, allOptions, entry = {}, index = 0) {
  const name = entry.name || EMPTY_OPTION;
  const values = index === 0
    ? [EMPTY_OPTION, NONE_OPTION, ...allOptions]
    : [EMPTY_OPTION, ...allOptions];

  const loraWidget = node.addWidget(
    "combo",
    `lora_${index}`,
    name,
    () => refreshSelection(node, selectionWidget, allOptions),
    { values },
  );
  loraWidget.label = `lora ${index + 1}`;
  loraWidget.options.serialize = false;
  return loraWidget;
}

function refreshSelection(node, selectionWidget, allOptions) {
  const baseSize = Array.isArray(node.size) ? [node.size[0], node.size[1]] : null;
  const entries = getEntries(node)
    .filter((entry, index) => {
      if (!entry.name || entry.name === EMPTY_OPTION) {
        return false;
      }
      return entry.name !== NONE_OPTION || index === 0;
    })
    .map((entry, index) => ({
      name: entry.name,
    }));

  removeEntryWidgets(node);
  entries.forEach((entry, index) => addEntryWidgets(node, selectionWidget, allOptions, entry, index));
  addEntryWidgets(node, selectionWidget, allOptions, {}, entries.length);

  selectionWidget.value = serializeEntries(entries);
  setCountWidget(node, entries.length);
  applyNodeSize(node, "preserve", baseSize);
  app.graph?.setDirtyCanvas?.(true, true);
}

function refreshFromSelection(node, selectionWidget, allOptions, mode = "preserve") {
  const baseSize = Array.isArray(node.size) ? [node.size[0], node.size[1]] : null;
  removeEntryWidgets(node);

  let selected = [];
  try {
    selected = JSON.parse(selectionWidget.value || "[]");
  } catch (_error) {
    selected = [];
  }

  if (!Array.isArray(selected)) {
    selected = [];
  }

  selected
    .map((entry) => {
      if (entry === null) {
        return { name: NONE_OPTION };
      }
      if (typeof entry === "string") {
        return { name: entry };
      }
      if (entry && typeof entry === "object") {
        return { name: entry.name };
      }
      return null;
    })
    .filter((entry) => entry && typeof entry === "object")
    .forEach((entry, index) => {
      const name = String(entry.name || "").trim();
      if (!name || (name === NONE_OPTION && index !== 0)) {
        return;
      }
      addEntryWidgets(node, selectionWidget, allOptions, { name }, index);
    });

  addEntryWidgets(node, selectionWidget, allOptions, {}, getEntries(node).length);
  selectionWidget.value = serializeEntries(getEntries(node));
  setCountWidget(node, JSON.parse(selectionWidget.value || "[]").length);
  applyNodeSize(node, mode, baseSize);
  app.graph?.setDirtyCanvas?.(true, true);
}

app.registerExtension({
  name: "HYBS.LoRAList",

  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData?.name !== CT_LORA_LIST) {
      return;
    }

    const allOptions =
      nodeData?.input?.required?.selection?.[1]?.all ||
      nodeData?.input?.optional?.selection?.[1]?.all ||
      [];

    const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function (...args) {
      originalOnNodeCreated?.apply(this, args);
      const selectionWidget = findWidget(this, "selection");
      if (!selectionWidget) {
        return;
      }
      hideWidget(selectionWidget);
      ensureCountWidget(this);
      refreshFromSelection(this, selectionWidget, allOptions, "compact");
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
      refreshFromSelection(this, selectionWidget, allOptions, "preserve");
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
