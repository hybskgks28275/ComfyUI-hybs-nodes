import {
  app, setCountWidget,
  applyNodeSize, removeWidgets, installListHooks,
} from "./common/widgets.js";

const CT_LORA_LIST = "HYBS_LoRAList";
const LEGACY_EMPTY_OPTION = "<select LoRA>";
const NONE_OPTION = "NONE";
const ADD_BUTTON_NAME = "add lora";

function isLoRAWidget(widget) {
  return typeof widget?.name === "string" && widget.name.startsWith("lora_");
}

function isEntryWidget(widget) {
  return isLoRAWidget(widget);
}

function isAddButtonWidget(widget) {
  return widget?.name === ADD_BUTTON_NAME;
}

function findEntryWidgets(node) {
  return node.widgets?.filter(isEntryWidget) || [];
}

function isEmptyOption(value) {
  return value === LEGACY_EMPTY_OPTION;
}

function removeEntryWidgets(node) {
  removeWidgets(node, isEntryWidget);
}

function removeAddButton(node) {
  removeWidgets(node, isAddButtonWidget);
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
      .filter((entry) => entry.name && !isEmptyOption(entry.name))
      .map((entry) => (entry.name === NONE_OPTION ? null : entry.name)),
  );
}

function addEntryWidgets(node, selectionWidget, allOptions, entry = {}, index = 0) {
  const name = entry.name || NONE_OPTION;
  const values = [NONE_OPTION, ...allOptions];

  const loraWidget = node.addWidget(
    "combo",
    `lora_${index}`,
    name,
    () => refreshSelection(node, selectionWidget, allOptions),
    { values },
  );
  loraWidget.label = `lora ${index + 1}`;
  loraWidget.options.serialize = false;
  loraWidget.serialize = false;
  return loraWidget;
}

function hasPendingDeleteRow(node) {
  return getEntries(node).some((entry) => entry.index > 0 && entry.name === NONE_OPTION);
}

function addAddButton(node, selectionWidget, allOptions) {
  removeAddButton(node);
  const addButton = node.addWidget("button", ADD_BUTTON_NAME, "add", () => {
    if (hasPendingDeleteRow(node)) {
      return;
    }

    const baseSize = Array.isArray(node.size) ? [node.size[0], node.size[1]] : null;
    removeAddButton(node);
    addEntryWidgets(node, selectionWidget, allOptions, { name: NONE_OPTION }, getEntries(node).length);
    addAddButton(node, selectionWidget, allOptions);
    applyNodeSize(node, "preserve", baseSize);
    app.graph?.setDirtyCanvas?.(true, true);
  });
  addButton.options = addButton.options || {};
  addButton.options.serialize = false;
  addButton.serialize = false;
}

function refreshSelection(node, selectionWidget, allOptions) {
  const baseSize = Array.isArray(node.size) ? [node.size[0], node.size[1]] : null;
  const entries = getEntries(node)
    .filter((entry, index) => {
      if (!entry.name || isEmptyOption(entry.name)) {
        return false;
      }
      return entry.name !== NONE_OPTION || index === 0;
    })
    .map((entry, index) => ({
      name: entry.name,
    }));

  removeEntryWidgets(node);
  removeAddButton(node);
  entries.forEach((entry, index) => addEntryWidgets(node, selectionWidget, allOptions, entry, index));
  if (entries.length === 0) {
    addEntryWidgets(node, selectionWidget, allOptions, { name: NONE_OPTION }, 0);
  }
  addAddButton(node, selectionWidget, allOptions);

  const serializedEntries = entries.length === 0 ? [{ name: NONE_OPTION }] : entries;
  selectionWidget.value = serializeEntries(serializedEntries);
  setCountWidget(node, serializedEntries.length);
  applyNodeSize(node, "preserve", baseSize);
  app.graph?.setDirtyCanvas?.(true, true);
}

function refreshFromSelection(node, selectionWidget, allOptions, mode = "preserve") {
  const baseSize = Array.isArray(node.size) ? [node.size[0], node.size[1]] : null;
  removeEntryWidgets(node);
  removeAddButton(node);

  let selected = [];
  try {
    selected = JSON.parse(selectionWidget.value || "[]");
  } catch (_error) {
    selected = [];
  }

  if (!Array.isArray(selected)) {
    selected = [];
  }

  const restoredEntries = [];
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
      const rowIndex = restoredEntries.length;
      if (!name || (name === NONE_OPTION && rowIndex !== 0)) {
        return;
      }
      addEntryWidgets(node, selectionWidget, allOptions, { name }, rowIndex);
      restoredEntries.push({ name });
    });

  if (restoredEntries.length === 0) {
    addEntryWidgets(node, selectionWidget, allOptions, { name: NONE_OPTION }, 0);
    restoredEntries.push({ name: NONE_OPTION });
  }
  addAddButton(node, selectionWidget, allOptions);
  selectionWidget.value = serializeEntries(restoredEntries);
  setCountWidget(node, restoredEntries.length);
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

    installListHooks(nodeType, (node, selection, mode) => refreshFromSelection(node, selection, allOptions, mode));
  },
});
