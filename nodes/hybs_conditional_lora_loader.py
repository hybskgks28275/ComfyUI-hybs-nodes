"""Conditional LoRA loader node."""

import os
import re
from typing import Any

from ..hybs_comfy_api import io, resolve_type
from ..hybs_lora_common import apply_lora, lora_token

import folder_paths

LOG_PREFIX = '[HYBS]["Conditional LoRA Loader"]'


def _log(message: str) -> None:
    print(f"{LOG_PREFIX} {message}")


_Model = resolve_type("Model")
_CLIP = resolve_type("CLIP")


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
                    tooltip="Positive prompt matched against TOML trigger regular expressions."
                ),
                io.Combo.Input(
                    "config_toml",
                    options=tomls,
                    tooltip="TOML file under config/ that contains [[lora]] entries."
                ),
            ],
            outputs=[
                _Model.Output(display_name="model", tooltip="MODEL with all matching LoRAs applied."),
                _CLIP.Output(display_name="clip", tooltip="CLIP with all matching LoRAs applied."),
                io.String.Output(display_name="applied loras", tooltip="Space-separated tokens for the applied LoRAs."),
            ],
            description="Conditionally apply LoRAs whose TOML trigger regex matches the positive prompt.",
        )

    @staticmethod
    def _match(positive: str, pattern: str) -> bool:
        if not isinstance(pattern, str) or not pattern:
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
            except ImportError:
                import toml as _toml
                with open(full, "r", encoding="utf-8") as fp:
                    data = _toml.load(fp)
        except Exception as e:
            raise RuntimeError(f"Failed to parse TOML: {e}")
        if not isinstance(data, dict) or "lora" not in data or not isinstance(data["lora"], list):
            raise ValueError("TOML must contain [[lora]] array")
        if not all(isinstance(entry, dict) for entry in data["lora"]):
            raise ValueError("Each LoRA entry must be a table")
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
            try:
                sm = float(ent.get("strength_model", 1.0))
                sc = float(ent.get("strength_clip", 1.0))
            except (TypeError, ValueError):
                _log(f"Skipping LoRA entry #{i}: invalid strengths")
                continue
            if not isinstance(name, str) or not name:
                continue

            matched = cls._match(src, trig)
            _log(f"#{i} matched={matched} trigger={trig!r} name={name!r} sm={sm} sc={sc}")
            if not matched:
                continue

            lora_path = folder_paths.get_full_path("loras", name)
            if not lora_path:
                _log(f"LoRA not found: {name}")
                continue

            try:
                new_model, new_clip, applied = apply_lora(model, clip, lora_path, name, sm, sc, log=_log)
                if applied:
                    _log(f"Applied LoRA: {name} (m={sm}, c={sc})")
                    model, clip = new_model, new_clip
                    applied_any = True
                    applied_tokens.append(lora_token(name, sm, sc))
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
