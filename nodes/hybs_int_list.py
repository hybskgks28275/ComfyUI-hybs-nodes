"""Integer list node."""

from __future__ import annotations

import json

from ..hybs_comfy_api import io

LOG_PREFIX = '[HYBS]["Int List"]'


def _log(message: str) -> None:
    print(f"{LOG_PREFIX} {message}")


class HYBS_IntList(io.ComfyNode):
    """Return integer values as a list."""

    @classmethod
    def _parse_selection(cls, selection) -> list[int]:
        if isinstance(selection, dict):
            values = selection.get("selected", [])
        elif isinstance(selection, str):
            try:
                values = json.loads(selection)
            except json.JSONDecodeError:
                values = []
        else:
            values = []

        if not isinstance(values, list):
            return []

        parsed = []
        for value in values:
            try:
                parsed.append(int(value))
            except (TypeError, ValueError):
                continue
        return parsed

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="HYBS_IntList",
            display_name="Int List",
            category="HYBS/List",
            search_aliases=["int list", "integer list", "seed list", "number list"],
            essentials_category="Input/List",
            inputs=[
                io.String.Input(
                    "selection",
                    default="[1]",
                    socketless=True,
                    tooltip="Internal integer list state managed by the frontend widget.",
                ),
            ],
            outputs=[
                io.Custom("LIST").Output(display_name="int list"),
                io.Int.Output(display_name="count"),
            ],
            description="Return editable integer values as a list.",
        )

    @classmethod
    def validate_inputs(cls, selection="[1]", **kwargs) -> bool | str:
        if not cls._parse_selection(selection):
            return "At least one integer value is required."
        return True

    @classmethod
    def execute(cls, selection="[1]", **kwargs) -> io.NodeOutput:
        values = cls._parse_selection(selection)
        if not values:
            raise ValueError("No integer values were provided.")

        _log(f"Selected {len(values)} integer values")
        return io.NodeOutput(values, len(values))
