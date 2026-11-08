"""Single LoRA loader node."""

from __future__ import annotations

import folder_paths
import json
import math

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


class HYBS_LoadLoRAStack(io.ComfyNode):
    """Apply a variable-length LoRA stack to MODEL, TE (CLIP), or both."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="HYBS_LoadLoRAStack",
            display_name="Load LoRA Stack",
            category="HYBS/LoRA",
            search_aliases=["load lora model", "load lora te", "lora loader", "hybs lora"],
            essentials_category="Loaders/LoRA",
            inputs=[
                _Model.Input("model", optional=True, tooltip="Optional MODEL to receive the LoRA."),
                _CLIP.Input("clip", optional=True, tooltip="Optional text encoder (TE / CLIP) to receive the LoRA."),
                io.Combo.Input("lora_name", options=_lora_options(), default=NONE_OPTION,
                               tooltip="Select a LoRA in the folder tree. NONE passes inputs through."),
                io.Float.Input("strength_model", default=1.0, min=-20.0, max=20.0, step=0.01,
                               tooltip="MODEL strength. Hold + or - to change continuously."),
                io.Float.Input("strength_clip", default=1.0, min=-20.0, max=20.0, step=0.01,
                               tooltip="TE / CLIP strength. Hold + or - to change continuously."),
                io.String.Input("selection", default="", socketless=True, optional=True,
                                tooltip="Ordered JSON LoRA stack, managed by the frontend. An empty array applies no LoRA."),
            ],
            outputs=[
                _Model.Output(display_name="model", tooltip="Modified MODEL, or None if disconnected."),
                _CLIP.Output(display_name="clip (TE)", tooltip="Modified TE / CLIP, or None if disconnected."),
                io.String.Output(display_name="applied lora", tooltip="Applied LoRA token, or empty when unused."),
            ],
            description="Add, remove or toggle LoRA rows and apply enabled rows in order to MODEL, TE (CLIP), or both. An empty or disabled stack passes inputs through.",
        )

    @classmethod
    def _entries(cls, selection, lora_name, strength_model, strength_clip):
        if selection is None or selection == "":
            entries = [dict(lora_name=lora_name, strength_model=strength_model, strength_clip=strength_clip)]
        else:
            entries = json.loads(selection) if isinstance(selection, str) else selection
        if not isinstance(entries, list):
            raise ValueError("LoRA stack must be a JSON array.")
        parsed = []
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                raise ValueError(f"LoRA row {index + 1} must be an object.")
            name = entry.get("lora_name", NONE_OPTION)
            if name is not None and not isinstance(name, str):
                raise ValueError(f"LoRA row {index + 1} must have a string filename.")
            enabled = entry.get("enabled", True)
            if not isinstance(enabled, bool):
                raise ValueError(f"LoRA row {index + 1} enabled must be a boolean.")
            sm = float(entry.get("strength_model", 1.0))
            sc = float(entry.get("strength_clip", 1.0))
            if not all(math.isfinite(value) and -20 <= value <= 20 for value in (sm, sc)):
                raise ValueError(f"LoRA row {index + 1} strengths must be finite and between -20 and 20.")
            parsed.append((name, sm, sc, enabled))
        return parsed

    @classmethod
    def validate_inputs(cls, lora_name=NONE_OPTION, strength_model=1.0, strength_clip=1.0,
                        selection="", **kwargs) -> bool | str:
        try:
            entries = cls._entries(selection, lora_name, strength_model, strength_clip)
        except (ValueError, TypeError) as exc:
            return str(exc)
        for name, _, _, enabled in entries:
            if not enabled:
                continue
            result = HYBS_LoadLoRA.validate_inputs(lora_name=name)
            if result is not True:
                return result
        return True

    @classmethod
    def execute(cls, model=None, clip=None, lora_name=NONE_OPTION,
                strength_model=1.0, strength_clip=1.0, selection="", **kwargs) -> io.NodeOutput:
        tokens = []
        for name, sm, sc, enabled in cls._entries(selection, lora_name, strength_model, strength_clip):
            sm = sm if model is not None else 0.0
            sc = sc if clip is not None else 0.0
            if not enabled or _is_none_lora(name) or (sm == 0.0 and sc == 0.0):
                continue
            path = folder_paths.get_full_path("loras", name)
            if not path:
                raise FileNotFoundError(f"LoRA not found: {name}")
            model, clip, applied = apply_lora(model, clip, path, name, sm, sc, log=_log)
            if not applied:
                raise RuntimeError(f"Failed to apply LoRA: {name}")
            tokens.append(lora_token(name, sm, sc))
        return io.NodeOutput(model, clip, " ".join(tokens))
