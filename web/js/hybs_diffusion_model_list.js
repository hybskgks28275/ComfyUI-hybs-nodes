import {
  app, setCountWidget,
  applyNodeSize, removeWidgets, installListHooks,
} from "./common/widgets.js";

const CT_DIFFUSION_MODEL_LIST = "HYBS_DiffusionModelList";
const EMPTY_OPTION = "none";

function isModelWidget(widget) {
  return typeof widget?.name === "string" && widget.name.startsWith("model_");
}

function findModelWidgets(node) {
  return node.widgets?.filter(isModelWidget) || [];
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
  widget.serialize = false;
  return widget;
}

function refreshSelection(node, selectionWidget, allOptions) {
  const selected = findModelWidgets(node)
    .map((widget) => widget.value)
    .filter((value) => value !== EMPTY_OPTION);
  selectionWidget.value = JSON.stringify(selected);
  refreshFromSelection(node, selectionWidget, allOptions);
}

function refreshFromSelection(node, selectionWidget, allOptions, mode = "preserve") {
  const baseSize = Array.isArray(node.size) ? [node.size[0], node.size[1]] : null;
  removeWidgets(node, isModelWidget);

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
  setCountWidget(node, selected.length);
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

    installListHooks(nodeType, (node, selection, mode) => refreshFromSelection(node, selection, allOptions, mode));
  },
});
