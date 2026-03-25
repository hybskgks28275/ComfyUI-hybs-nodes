import { app } from "../../scripts/app.js";

const CT_DIFFUSION_MODEL_LIST = "HYBS_DiffusionModelList";
const EMPTY_OPTION = "none";
const HIDDEN_WIDGET_SIZE = [0, -4];

function isModelWidget(widget) {
  return typeof widget?.name === "string" && widget.name.startsWith("model_");
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

function findModelWidgets(node) {
  return node.widgets?.filter(isModelWidget) || [];
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

function addModelWidget(node, selectionWidget, allOptions, value = EMPTY_OPTION) {
  const index = findModelWidgets(node).length;
  const widget = node.addWidget(
    "combo",
    `model_${index}`,
    value,
    () => refreshSelection(node, selectionWidget, allOptions),
    { values: [EMPTY_OPTION, ...allOptions] },
  );

  widget.label = `model ${index + 1}`;
  widget.options.serialize = false;
  return widget;
}

function refreshSelection(node, selectionWidget, allOptions) {
  const baseSize = Array.isArray(node.size) ? [node.size[0], node.size[1]] : null;
  const selected = [];
  let widgetIndex = 0;
  let comboIndex = 0;

  while (widgetIndex < node.widgets.length) {
    const widget = node.widgets[widgetIndex];
    if (!isModelWidget(widget)) {
      widgetIndex += 1;
      continue;
    }

    if (widget.value === EMPTY_OPTION) {
      node.widgets.splice(widgetIndex, 1);
      continue;
    }

    widget.name = `model_${comboIndex}`;
    widget.label = `model ${comboIndex + 1}`;
    selected.push(widget.value);
    widgetIndex += 1;
    comboIndex += 1;
  }

  addModelWidget(node, selectionWidget, allOptions, EMPTY_OPTION);
  selectionWidget.value = JSON.stringify(selected);
  applyNodeSize(node, "preserve", baseSize);
  app.graph?.setDirtyCanvas?.(true, true);
}

function refreshFromSelection(node, selectionWidget, allOptions, mode = "preserve") {
  const baseSize = Array.isArray(node.size) ? [node.size[0], node.size[1]] : null;
  let widgetIndex = 0;
  while (widgetIndex < node.widgets.length) {
    const widget = node.widgets[widgetIndex];
    if (isModelWidget(widget)) {
      node.widgets.splice(widgetIndex, 1);
      continue;
    }
    widgetIndex += 1;
  }

  let selected = [];
  try {
    selected = JSON.parse(selectionWidget.value || "[]");
  } catch (_error) {
    selected = [];
  }

  if (!Array.isArray(selected)) {
    selected = [];
  }

  for (const value of selected) {
    addModelWidget(node, selectionWidget, allOptions, value);
  }

  addModelWidget(node, selectionWidget, allOptions, EMPTY_OPTION);
  selectionWidget.value = JSON.stringify(selected);
  applyNodeSize(node, mode, baseSize);
  app.graph?.setDirtyCanvas?.(true, true);
}

app.registerExtension({
  name: "HYBS.DiffusionModelList",

  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData?.name !== CT_DIFFUSION_MODEL_LIST) {
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
