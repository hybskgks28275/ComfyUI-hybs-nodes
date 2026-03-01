"""Conditional LoRA loader node."""

import os
import re
from typing import Any

from ..hybs_comfy_api import io

try:
    from comfy import sd
except Exception:
    sd = None

import folder_paths
import comfy.utils as utils

LOG_PREFIX = "[Conditional LoRA Loader]"


def _log(message: str) -> None:
    print(f"{LOG_PREFIX} {message}")


# ---- Type fallback helpers ---------------------------------------------------
def _resolve_type(name: str):
    """
    Try io.<Name>, then io.<CamelCase>, else fall back to io.Custom(name).
    Keeps sockets link-compatible across API versions.
    """
    t = getattr(io, name, None)
    if t is not None:
        return t
    # e.g. "CLIP" -> "Clip"
    camel = name[:1].upper() + name[1:].lower()
    t = getattr(io, camel, None)
    if t is not None:
        return t
    # final fallback: custom type with the same type-id
    return io.Custom(name)

_Model = _resolve_type("Model")
_CLIP = _resolve_type("CLIP")


# ---- Internal: LoRA applier --------------------------------------------------
def _apply_lora(model, clip, lora_path: str, lora_name: str, sm: float, sc: float):
    # 1) comfy.sd.load_lora
    if sd is not None and hasattr(sd, "load_lora"):
        try:
            m, c = sd.load_lora(model, clip, lora_path, sm, sc)
            return m, c, True
        except Exception as e:
            _log(f"comfy.sd.load_lora failed: {e}")

    # 2) built-in nodes.LoraLoader
    try:
        from nodes import LoraLoader as _BuiltinLoraLoader
        try:
            m, c = _BuiltinLoraLoader().load_lora(model, clip, lora_name, sm, sc)
            return m, c, True
        except Exception as e:
            _log(f"nodes.LoraLoader failed: {e}")
    except Exception:
        pass

    # 3) low-level fallback
    try:
        lora = utils.load_torch_file(lora_path, safe_load=True)
        if hasattr(utils, "apply_lora"):
            model = utils.apply_lora(model, lora, sm)
            if clip is not None and sc != 0.0 and hasattr(utils, "apply_lora_to_clip"):
                clip = utils.apply_lora_to_clip(clip, lora, sc)
            return model, clip, True
    except Exception as e:
        _log(f"fallback apply_lora failed: {e}")

    _log("All loaders failed -> passthrough.")
    return model, clip, False


# ---- Node (V3 schema) --------------------------------------------------------
class HYBS_ConditionalLoRALoader(io.ComfyNode):
    CONFIG_DIR = None

    @classmethod
    def _ensure_config_dir(cls) -> str:
        if cls.CONFIG_DIR is None:
            base = os.path.dirname(os.path.dirname(__file__))
            cls.CONFIG_DIR = os.path.join(base, "config")
            os.makedirs(cls.CONFIG_DIR, exist_ok=True)
        return cls.CONFIG_DIR

    @classmethod
    def _list_toml(cls) -> list[str]:
        cdir = cls._ensure_config_dir()
        files = [f for f in os.listdir(cdir) if f.lower().endswith(".toml")]
        return sorted(files) if files else ["<put .toml in config>"]

    @classmethod
    def define_schema(cls) -> io.Schema:
        tomls = cls._list_toml()
        return io.Schema(
            node_id="HYBS_ConditionalLoRALoader",
            display_name="Conditional LoRA Loader",
            category="HYBS/ConditionalLoRALoader",
            search_aliases=["lora", "regex lora", "conditional lora", "prompt match lora"],
            essentials_category="Loaders/LoRA",
            inputs=[
                _Model.Input("model"),
                _CLIP.Input("clip"),
                io.String.Input(
                    "positive",
                    multiline=True,
                    default="",
                    force_input=True,
                    tooltip="Positive prompt to be matched against regex patterns."
                ),
                io.Combo.Input(
                    "config_toml",
                    options=tomls,
                    tooltip="TOML filename under config/ with [[lora]] entries."
                ),
            ],
            outputs=[
                _Model.Output(display_name="model"),
                _CLIP.Output(display_name="clip"),
                io.String.Output(display_name="applied loras"),
            ],
            description='Conditionally apply LoRAs based on regex matches in the positive. '
                        'Outputs tokens like <lora:"name":m:c> (space-separated).'
        )

    @staticmethod
    def _match(positive: str, pattern: str) -> bool:
        if not pattern:
            return False
        try:
            return re.search(pattern, positive or "") is not None
        except re.error as e:
            _log(f"Invalid regex in TOML: {e}")
            return False

    @classmethod
    def _load_toml(cls, fname: str) -> list[dict[str, Any]]:
        full = os.path.join(cls._ensure_config_dir(), fname)
        if not os.path.isfile(full):
            raise FileNotFoundError(full)
        try:
            try:
                import tomllib as _toml  # py311+
                with open(full, "rb") as fp:
                    data = _toml.load(fp)
            except Exception:
                import toml as _toml
                with open(full, "r", encoding="utf-8") as fp:
                    data = _toml.load(fp)
        except Exception as e:
            raise RuntimeError(f"Failed to parse TOML: {e}")
        if not isinstance(data, dict) or "lora" not in data or not isinstance(data["lora"], list):
            raise ValueError("TOML must contain [[lora]] array")
        return data["lora"]

    @classmethod
    def execute(
        cls,
        model,
        clip,
        positive: str,
        config_toml: str
    ) -> io.NodeOutput:
        try:
            entries = cls._load_toml(config_toml)
        except Exception as e:
            _log(f"TOML load error: {e}")
            return io.NodeOutput(model, clip, "")

        src = positive or ""
        applied_any = False
        applied_tokens = []

        for i, ent in enumerate(entries):
            trig = ent.get("trigger", "")
            name = ent.get("name", "")
            sm = float(ent.get("strength_model", 1.0))
            sc = float(ent.get("strength_clip", 1.0))

            matched = cls._match(src, trig)
            _log(f"#{i} matched={matched} trigger={trig!r} name={name!r} sm={sm} sc={sc}")
            if not matched:
                continue

            lora_path = folder_paths.get_full_path("loras", name)
            if not lora_path:
                _log(f"LoRA not found: {name}")
                continue

            try:
                new_model, new_clip, applied = _apply_lora(model, clip, lora_path, name, sm, sc)
                if applied:
                    _log(f"Applied LoRA: {name} (m={sm}, c={sc})")
                    model, clip = new_model, new_clip
                    applied_any = True
                    # Build token with filename (no extension, no quotes)
                    base = os.path.basename(name)
                    stem, _ = os.path.splitext(base)
                    token = f"<lora:{stem}:{sm}:{sc}>"
                    applied_tokens.append(token)
                else:
                    _log(f"Failed to apply LoRA: {name}")
            except Exception as e:
                _log(f"Exception while applying LoRA {name!r}: {e}")

        if not applied_any:
            _log("No LoRA applied (passthrough)")

        applied_str = " ".join(applied_tokens) if applied_tokens else ""
        return io.NodeOutput(model, clip, applied_str)

    @classmethod
    def fingerprint_inputs(cls, config_toml=None, **kwargs) -> str:
        try:
            base = cls._ensure_config_dir()
            path = os.path.join(base, config_toml) if config_toml else None
            mtime = os.path.getmtime(path) if path and os.path.isfile(path) else 0
        except Exception:
            mtime = 0
        return f"{config_toml}:{mtime}"
