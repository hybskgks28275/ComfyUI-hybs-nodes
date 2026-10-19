import { registerNumberList } from "./common/number_list.js";

registerNumberList({
  nodeId: "HYBS_IntList",
  extensionName: "HYBS.IntList",
  defaultValue: 1,
  options: { min: -2147483648, max: 2147483647, step: 1, precision: 0 },
  normalize(value) {
    const number = Number(value ?? 0);
    return Number.isFinite(number) ? Math.trunc(number) : 0;
  },
});
