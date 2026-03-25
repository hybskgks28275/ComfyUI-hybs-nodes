"""Diffusion model list node."""

from __future__ import annotations

import json

import folder_paths

from ..hybs_comfy_api import io

LOG_PREFIX = '[HYBS]["Diffusion Model List"]'


def _log(message: str) -> None:
    print(f"{LOG_PREFIX} {message}")


class HYBS_DiffusionModelList(io.ComfyNode):
    """Return selected diffusion model names as a list."""

    @classmethod
    def _diffusion_model_options(cls) -> list[str]:
        return folder_paths.get_filename_list("diffusion_models")

    @classmethod
    def _parse_selection(cls, selection) -> list[str]:
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

        return [value for value in values if isinstance(value, str) and value.strip()]

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="HYBS_DiffusionModelList",
            display_name="Diffusion Model List",
            category="HYBS/Model",
            search_aliases=["model list", "unet list", "multiple model", "diffusion model names"],
            essentials_category="Input/Model",
            inputs=[
                io.String.Input(
                    "selection",
                    default="[]",
                    socketless=True,
                    extra_dict={"all": cls._diffusion_model_options()},
                    tooltip="Internal selection state managed by the frontend widget.",
                ),
            ],
            outputs=[
                io.Custom("LIST").Output(display_name="model names"),
                io.Int.Output(display_name="count"),
            ],
            description="Return selected UNet diffusion model names as a list.",
        )

    @classmethod
    def validate_inputs(cls, selection="[]", **kwargs) -> bool | str:
        selected_names = cls._parse_selection(selection)
        if not selected_names:
            return "At least one diffusion model is required."

        available = set(folder_paths.get_filename_list("diffusion_models"))
        missing = [name for name in selected_names if name not in available]
        if missing:
            return f"Unknown diffusion models: {', '.join(missing)}"
        return True

    @classmethod
    def execute(cls, selection="[]", **kwargs) -> io.NodeOutput:
        selected_names = cls._parse_selection(selection)
        if not selected_names:
            raise ValueError("No diffusion models were provided.")

        _log(f"Selected {len(selected_names)} diffusion models")
        return io.NodeOutput(selected_names, len(selected_names))
