import { app } from "../../scripts/app.js";

const CT_ADVANCE = "HYBS_LoadImagePromptMetadataAdvance";
const HIDDEN_WIDGET_SIZE = [0, -4];
const BASE_OUTPUTS = 1;
const MAX_PROMPTS = 20;

function isNodeIdWidget(widget) {
  return typeof widget?.name === "string" && widget.name.startsWith("node_id_");
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

function findNodeIdWidgets(node) {
  return node.widgets?.filter(isNodeIdWidget) || [];
}

function getSelectedNodeIds(node) {
  return findNodeIdWidgets(node)
    .map((widget) => String(widget.value || "").trim())
    .filter((value) => value);
}

function parseSelectionJson(value) {
  try {
    const parsed = JSON.parse(value || "[]");
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.map((item) => String(item || "").trim()).filter((item) => item);
  } catch (_error) {
    return [];
  }
}

function getStoredSelection(node, selectionWidget) {
  const fromWidget = parseSelectionJson(selectionWidget?.value);
  if (fromWidget.length) {
    return fromWidget;
  }

  return parseSelectionJson(node.properties?.prompt_node_ids);
}

function storeSelection(node, selectionWidget, selected = null) {
  const values = selected || getSelectedNodeIds(node);
  selectionWidget.value = JSON.stringify(values);
  node.properties = node.properties || {};
  node.properties.prompt_node_ids = selectionWidget.value;
  return values;
}

function orderWidgets(node) {
  if (!Array.isArray(node.widgets)) {
    return;
  }

  const imageWidget = findWidget(node, "image");
  const nodeIdWidgets = findNodeIdWidgets(node);
  const rest = node.widgets.filter((widget) => widget !== imageWidget && !isNodeIdWidget(widget));

  node.widgets.length = 0;
  if (imageWidget) {
    node.widgets.push(imageWidget);
  }
  node.widgets.push(...nodeIdWidgets, ...rest);
}

function resetWidgetLayout(node) {
  orderWidgets(node);
  for (const widget of node.widgets || []) {
    delete widget.y;
    delete widget.last_y;
    delete widget.computedHeight;
  }
}

function syncPromptOutputs(node, desiredCount) {
  if (!Array.isArray(node.outputs)) {
    return;
  }

  let linkedPromptCount = 0;
  for (let i = BASE_OUTPUTS; i < node.outputs.length; i += 1) {
    const links = node.outputs[i]?.links;
    if (Array.isArray(links) && links.length > 0) {
      linkedPromptCount = Math.max(linkedPromptCount, i - BASE_OUTPUTS + 1);
    }
  }

  const count = Math.max(1, linkedPromptCount, Math.min(MAX_PROMPTS, desiredCount));

  while (node.outputs.length > BASE_OUTPUTS + count) {
    const output = node.outputs[node.outputs.length - 1];
    const links = output?.links;
    if (Array.isArray(links) && links.length > 0) {
      break;
    }
    node.outputs.pop();
  }

  while (node.outputs.length < BASE_OUTPUTS + count) {
    const index = node.outputs.length - BASE_OUTPUTS + 1;
    node.addOutput(`prompt_${index}`, "STRING");
  }

  for (let i = 0; i < count; i += 1) {
    const output = node.outputs[BASE_OUTPUTS + i];
    if (!output) {
      continue;
    }
    output.name = `prompt_${i + 1}`;
    output.type = "STRING";
  }
}

function schedulePromptOutputSync(node, desiredCount) {
  setTimeout(() => {
    try {
      syncPromptOutputs(node, desiredCount);
      app.graph?.setDirtyCanvas?.(true, true);
    } catch (error) {
      console.warn("[HYBS] Failed to sync prompt outputs", error);
    }
  }, 0);
}

function applyNodeSize(node, mode = "preserve", baseSize = null) {
  if (!Array.isArray(node.size) || typeof node.computeSize !== "function") {
    return;
  }

  resetWidgetLayout(node);
  const computedSize = node.computeSize();
  const currentWidth = baseSize?.[0] || node.size[0] || computedSize[0];
  const currentHeight = baseSize?.[1] || node.size[1] || computedSize[1];
  const targetHeight = mode === "compact" ? computedSize[1] : Math.max(currentHeight, computedSize[1]);
  node.setSize([currentWidth, targetHeight]);
}

function addNodeIdWidget(node, selectionWidget, value = "") {
  const index = findNodeIdWidgets(node).length;
  const widget = node.addWidget(
    "string",
    `node_id_${index}`,
    value,
    () => refreshSelection(node, selectionWidget),
  );

  widget.label = `node id ${index + 1}`;
  widget.options = widget.options || {};
  widget.options.serialize = false;
  return widget;
}

function refreshSelection(node, selectionWidget) {
  const baseSize = Array.isArray(node.size) ? [node.size[0], node.size[1]] : null;
  const selected = [];
  let widgetIndex = 0;
  let promptIndex = 0;

  while (widgetIndex < node.widgets.length) {
    const widget = node.widgets[widgetIndex];
    if (!isNodeIdWidget(widget)) {
      widgetIndex += 1;
      continue;
    }

    const value = String(widget.value || "").trim();
    if (!value) {
      node.widgets.splice(widgetIndex, 1);
      continue;
    }

    widget.name = `node_id_${promptIndex}`;
    widget.label = `node id ${promptIndex + 1}`;
    widget.value = value;
    selected.push(value);
    widgetIndex += 1;
    promptIndex += 1;
  }

  addNodeIdWidget(node, selectionWidget, "");
  storeSelection(node, selectionWidget, selected);
  orderWidgets(node);
  schedulePromptOutputSync(node, selected.length + 1);
  applyNodeSize(node, "preserve", baseSize);
  app.graph?.setDirtyCanvas?.(true, true);
}

function refreshFromSelection(node, selectionWidget, mode = "preserve") {
  const baseSize = Array.isArray(node.size) ? [node.size[0], node.size[1]] : null;
  let widgetIndex = 0;
  while (widgetIndex < node.widgets.length) {
    const widget = node.widgets[widgetIndex];
    if (isNodeIdWidget(widget)) {
      node.widgets.splice(widgetIndex, 1);
      continue;
    }
    widgetIndex += 1;
  }

  const selected = getStoredSelection(node, selectionWidget);

  for (const value of selected) {
    const normalized = String(value || "").trim();
    if (normalized) {
      addNodeIdWidget(node, selectionWidget, normalized);
    }
  }

  addNodeIdWidget(node, selectionWidget, "");
  const stored = storeSelection(
    node,
    selectionWidget,
    selected.filter((value) => String(value || "").trim()),
  );
  orderWidgets(node);
  schedulePromptOutputSync(node, stored.length + 1);
  applyNodeSize(node, mode, baseSize);
  app.graph?.setDirtyCanvas?.(true, true);
}

function syncStoredSelectionOnly(node) {
  const selectionWidget = findWidget(node, "selection");
  if (!selectionWidget) {
    return [];
  }

  const selected = getSelectedNodeIds(node);
  if (selected.length) {
    return storeSelection(node, selectionWidget, selected);
  }

  const stored = getStoredSelection(node, selectionWidget);
  if (stored.length && findNodeIdWidgets(node).length <= 1) {
    refreshFromSelection(node, selectionWidget, "preserve");
    return stored;
  }

  return storeSelection(node, selectionWidget, selected);
}

app.registerExtension({
  name: "HYBS.LoadImagePromptMetadataAdvance",

  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData?.name !== CT_ADVANCE) {
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
      refreshFromSelection(this, selectionWidget, "compact");
    };

    const originalOnConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function (...args) {
      originalOnConfigure?.apply(this, args);
      const selectionWidget = findWidget(this, "selection");
      if (!selectionWidget) {
        return;
      }
      hideWidget(selectionWidget);
      refreshFromSelection(this, selectionWidget, "preserve");
    };

    const originalOnResize = nodeType.prototype.onResize;
    nodeType.prototype.onResize = function (size) {
      originalOnResize?.apply(this, [size]);
      resetWidgetLayout(this);
    };

    const originalOnSerialize = nodeType.prototype.onSerialize;
    nodeType.prototype.onSerialize = function (...args) {
      syncStoredSelectionOnly(this);
      return originalOnSerialize?.apply(this, args);
    };

    const originalOnDrawForeground = nodeType.prototype.onDrawForeground;
    nodeType.prototype.onDrawForeground = function (...args) {
      const selected = syncStoredSelectionOnly(this);
      if (selected.length !== this._hybsLastSelectedCount) {
        this._hybsLastSelectedCount = selected.length;
        schedulePromptOutputSync(this, selected.length + 1);
      }
      return originalOnDrawForeground?.apply(this, args);
    };
  },
});
