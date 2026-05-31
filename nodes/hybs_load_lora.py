"""Single LoRA loader node."""

from __future__ import annotations

import os

import comfy.utils as utils
import folder_paths

from ..hybs_comfy_api import io

try:
    from comfy import sd
except Exception:
    sd = None

LOG_PREFIX = '[HYBS]["Load LoRA"]'
NONE_OPTION = "NONE"


def _log(message: str) -> None:
    print(f"{LOG_PREFIX} {message}")


def _resolve_type(name: str):
    t = getattr(io, name, None)
    if t is not None:
        return t
    camel = name[:1].upper() + name[1:].lower()
    t = getattr(io, camel, None)
    if t is not None:
        return t
    return io.Custom(name)


_Model = _resolve_type("Model")
_CLIP = _resolve_type("CLIP")


def _lora_options() -> list[str]:
    return [NONE_OPTION, *folder_paths.get_filename_list("loras")]


def _is_none_lora(lora_name) -> bool:
    return lora_name is None or str(lora_name).strip() in ("", NONE_OPTION)


def _apply_lora(model, clip, lora_path: str, lora_name: str, sm: float, sc: float):
    if sd is not None and hasattr(sd, "load_lora"):
        try:
            return (*sd.load_lora(model, clip, lora_path, sm, sc), True)
        except Exception as e:
            _log(f"comfy.sd.load_lora failed: {e}")

    try:
        from nodes import LoraLoader as _BuiltinLoraLoader

        try:
            return (*_BuiltinLoraLoader().load_lora(model, clip, lora_name, sm, sc), True)
        except Exception as e:
            _log(f"nodes.LoraLoader failed: {e}")
    except Exception:
        pass

    try:
        lora = utils.load_torch_file(lora_path, safe_load=True)
        if hasattr(utils, "apply_lora"):
            model = utils.apply_lora(model, lora, sm)
            if clip is not None and sc != 0.0 and hasattr(utils, "apply_lora_to_clip"):
                clip = utils.apply_lora_to_clip(clip, lora, sc)
            return model, clip, True
    except Exception as e:
        _log(f"fallback apply_lora failed: {e}")

    return model, clip, False


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
                _Model.Input("model"),
                _CLIP.Input("clip"),
                io.Combo.Input(
                    "lora_name",
                    options=_lora_options(),
                    default=NONE_OPTION,
                    tooltip="LoRA filename. NONE means no LoRA is applied.",
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
                _Model.Output(display_name="model"),
                _CLIP.Output(display_name="clip"),
                io.String.Output(display_name="applied lora"),
            ],
            description="Apply the selected LoRA. NONE/null returns the input model and clip unchanged.",
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

        new_model, new_clip, applied = _apply_lora(model, clip, lora_path, lora_name, sm, sc)
        if not applied:
            raise RuntimeError(f"Failed to apply LoRA: {lora_name}")

        base = os.path.basename(lora_name)
        stem, _ = os.path.splitext(base)
        token = f"<lora:{stem}:{sm}:{sc}>"
        _log(f"Applied LoRA: {lora_name} (m={sm}, c={sc})")
        return io.NodeOutput(new_model, new_clip, token)
