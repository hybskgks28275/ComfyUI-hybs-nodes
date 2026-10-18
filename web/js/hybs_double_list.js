import { registerNumberList } from "./common/number_list.js";

registerNumberList({
  nodeId: "HYBS_DoubleList",
  extensionName: "HYBS.DoubleList",
  defaultValue: 1.0,
  options: { min: -20.0, max: 20.0, step: 0.05, precision: 3 },
  normalize(value) {
    const number = Number(value ?? 0);
    return Number.isFinite(number) ? number : 0;
  },
});
