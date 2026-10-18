"""Single LoRA loader node."""

from __future__ import annotations

import folder_paths

from ..hybs_comfy_api import io, resolve_type
from ..hybs_lora_common import apply_lora, lora_token

LOG_PREFIX = '[HYBS]["Load LoRA"]'
NONE_OPTION = "NONE"


def _log(message: str) -> None:
    print(f"{LOG_PREFIX} {message}")


_Model = resolve_type("Model")
_CLIP = resolve_type("CLIP")


def _lora_options() -> list[str]:
    return [NONE_OPTION, *folder_paths.get_filename_list("loras")]


def _is_none_lora(lora_name) -> bool:
    return lora_name is None or str(lora_name).strip() in ("", NONE_OPTION)


class HYBS_LoadLoRA(io.ComfyNode):
    """Apply a selected LoRA, or pass through when NONE/null is selected."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="HYBS_LoadLoRA",
            display_name="Load LoRA",
            category="HYBS/LoRA",
            search_aliases=["load lora", "lora loader", "hybs lora loader"],
            essentials_category="Loaders/LoRA",
            inputs=[
                _Model.Input("model", tooltip="MODEL to receive the LoRA."),
                _CLIP.Input("clip", tooltip="CLIP to receive the LoRA."),
                io.Combo.Input(
                    "lora_name",
                    options=_lora_options(),
                    default=NONE_OPTION,
                    tooltip="LoRA filename. NONE leaves the input model and CLIP unchanged.",
                ),
                io.Float.Input(
                    "strength_model",
                    default=1.0,
                    min=-20.0,
                    max=20.0,
                    step=0.05,
                    tooltip="LoRA strength for MODEL.",
                ),
                io.Float.Input(
                    "strength_clip",
                    default=1.0,
                    min=-20.0,
                    max=20.0,
                    step=0.05,
                    tooltip="LoRA strength for CLIP.",
                ),
            ],
            outputs=[
                _Model.Output(display_name="model", tooltip="MODEL after the LoRA is applied."),
                _CLIP.Output(display_name="clip", tooltip="CLIP after the LoRA is applied."),
                io.String.Output(display_name="applied lora", tooltip="Applied LoRA token, or an empty string for NONE."),
            ],
            description="Apply the selected LoRA. NONE/null returns the input model and CLIP unchanged.",
        )

    @classmethod
    def validate_inputs(cls, lora_name=NONE_OPTION, **kwargs) -> bool | str:
        if _is_none_lora(lora_name):
            return True
        if lora_name not in folder_paths.get_filename_list("loras"):
            return f"Unknown LoRA: {lora_name}"
        return True

    @classmethod
    def execute(
        cls,
        model,
        clip,
        lora_name=NONE_OPTION,
        strength_model=1.0,
        strength_clip=1.0,
        **kwargs,
    ) -> io.NodeOutput:
        if _is_none_lora(lora_name):
            _log("No LoRA selected (passthrough)")
            return io.NodeOutput(model, clip, "")

        sm = float(strength_model)
        sc = float(strength_clip)
        lora_path = folder_paths.get_full_path("loras", lora_name)
        if not lora_path:
            raise FileNotFoundError(f"LoRA not found: {lora_name}")

        new_model, new_clip, applied = apply_lora(model, clip, lora_path, lora_name, sm, sc, log=_log)
        if not applied:
            raise RuntimeError(f"Failed to apply LoRA: {lora_name}")

        token = lora_token(lora_name, sm, sc)
        _log(f"Applied LoRA: {lora_name} (m={sm}, c={sc})")
        return io.NodeOutput(new_model, new_clip, token)
