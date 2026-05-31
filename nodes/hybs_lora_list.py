"""LoRA list node."""

import json
import folder_paths

from ..hybs_comfy_api import io

LOG_PREFIX = '[HYBS]["LoRA List"]'
NONE_OPTION = "NONE"


def _log(message: str) -> None:
    print(f"{LOG_PREFIX} {message}")


class HYBS_LoRAList(io.ComfyNode):
    """Return selected LoRA names as a list."""

    @classmethod
    def _lora_options(cls) -> list[str]:
        return folder_paths.get_filename_list("loras")

    @classmethod
    def _parse_selection(cls, selection) -> list[str | None]:
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
            if value is None:
                name = None
            elif isinstance(value, str):
                name = value.strip()
            elif isinstance(value, dict):
                raw_name = value.get("name")
                name = None if raw_name is None else str(raw_name).strip()
            else:
                continue

            if name == "":
                continue

            parsed.append(name)

        return parsed

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="HYBS_LoRAList",
            display_name="LoRA List",
            category="HYBS/LoRA",
            search_aliases=["lora list", "multiple lora", "lora names"],
            essentials_category="Input/LoRA",
            inputs=[
                io.String.Input(
                    "selection",
                    default="[null]",
                    socketless=True,
                    extra_dict={"all": cls._lora_options(), "none": NONE_OPTION},
                    tooltip="Internal LoRA selection state managed by the frontend widget.",
                ),
            ],
            outputs=[
                io.Custom("LIST").Output(display_name="lora names"),
                io.Int.Output(display_name="count"),
            ],
            description="Return selected LoRA filenames as a list. The first row may be NONE/null.",
        )

    @classmethod
    def validate_inputs(cls, selection="[null]", **kwargs) -> bool | str:
        selected = cls._parse_selection(selection)
        if not selected:
            return "At least one LoRA entry is required."

        available = set(folder_paths.get_filename_list("loras"))
        missing = [
            name
            for name in selected
            if name is not None and name != NONE_OPTION and name not in available
        ]
        if missing:
            return f"Unknown LoRAs: {', '.join(missing)}"

        none_positions = [
            index
            for index, name in enumerate(selected)
            if name is None or name == NONE_OPTION
        ]
        if any(index != 0 for index in none_positions):
            return "NONE is only allowed in the first LoRA row."

        return True

    @classmethod
    def execute(cls, selection="[null]", **kwargs) -> io.NodeOutput:
        selected = cls._parse_selection(selection)
        if not selected:
            raise ValueError("No LoRA entries were provided.")
        if any(
            index != 0 and (name is None or name == NONE_OPTION)
            for index, name in enumerate(selected)
        ):
            raise ValueError("NONE is only allowed in the first LoRA row.")

        normalized = [None if name == NONE_OPTION else name for name in selected]
        _log(f"Selected {len(normalized)} LoRA entries")
        return io.NodeOutput(normalized, len(normalized))
