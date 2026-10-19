import {
  app, setCountWidget,
  applyNodeSize, removeWidget, removeWidgets, installListHooks,
} from "./widgets.js";

export function registerNumberList({ nodeId, extensionName, defaultValue, options, normalize }) {
  const CONTROL_WIDGET_NAMES = new Set(["add value", "remove value"]);

  function isValueWidget(widget) {
    return typeof widget?.name === "string" && widget.name.startsWith("value_");
  }

  function isControlWidget(widget) {
    return typeof widget?.name === "string" && CONTROL_WIDGET_NAMES.has(widget.name);
  }

  function findValueWidgets(node) {
    return node.widgets?.filter(isValueWidget) || [];
  }

  function getValues(node) {
    return findValueWidgets(node).map((widget) => normalize(widget.value));
  }

  function storeSelection(node, selectionWidget) {
    const values = getValues(node);
    selectionWidget.value = JSON.stringify(values);
    setCountWidget(node, values.length);
    return values;
  }

  function removeValueWidgets(node) {
    removeWidgets(node, isValueWidget);
  }

  function removeControlWidgets(node) {
    removeWidgets(node, isControlWidget);
  }

  function addControlWidgets(node, selectionWidget) {
    removeControlWidgets(node);

    const addButton = node.addWidget("button", "add value", "add", () => addValue(node, selectionWidget));
    addButton.options = addButton.options || {};
    addButton.options.serialize = false;
    addButton.serialize = false;

    const removeButton = node.addWidget("button", "remove value", "remove", () => removeLastValue(node, selectionWidget));
    removeButton.options = removeButton.options || {};
    removeButton.options.serialize = false;
    removeButton.serialize = false;
  }

  function addValueWidget(node, selectionWidget, value = defaultValue) {
    const index = findValueWidgets(node).length;
    const widget = node.addWidget(
      "number",
      `value_${index}`,
      normalize(value),
      () => {
        widget.value = normalize(widget.value);
        storeSelection(node, selectionWidget);
        app.graph?.setDirtyCanvas?.(true, true);
      },
      { ...options },
    );
    widget.label = `value ${index + 1}`;
    widget.options.serialize = false;
    widget.serialize = false;
    return widget;
  }

  function refreshFromSelection(node, selectionWidget, mode = "preserve") {
    const baseSize = Array.isArray(node.size) ? [node.size[0], node.size[1]] : null;
    removeValueWidgets(node);
    removeControlWidgets(node);

    let values = [];
    try {
      values = JSON.parse(selectionWidget.value || JSON.stringify([defaultValue]));
    } catch (_error) {
      values = [defaultValue];
    }
    if (!Array.isArray(values) || values.length === 0) {
      values = [defaultValue];
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
    addValueWidget(node, selectionWidget, defaultValue);
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
      removeWidget(node, last);
    }
    addControlWidgets(node, selectionWidget);
    storeSelection(node, selectionWidget);
    applyNodeSize(node, "preserve", baseSize);
    app.graph?.setDirtyCanvas?.(true, true);
  }

  app.registerExtension({
    name: extensionName,

    async beforeRegisterNodeDef(nodeType, nodeData) {
      if (nodeData?.name !== nodeId) {
        return;
      }

      installListHooks(nodeType, refreshFromSelection);
    },
  });

}
