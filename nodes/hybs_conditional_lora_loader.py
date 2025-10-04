import os
import re
from comfy_api.latest import io

try:
    from comfy import sd
except Exception:
    sd = None

import folder_paths
import comfy.utils as utils


# ---- Type fallback helpers ---------------------------------------------------
def _resolve_type(name: str):
    """
    Try io.<Name> (exact), then io.<Name in CamelCase>, and finally fall back
    to a custom V3 type with the same name (so sockets stay link-compatible).
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
_CLIP  = _resolve_type("CLIP")


# ---- Internal: LoRA applier --------------------------------------------------
def _apply_lora(model, clip, lora_path: str, lora_name: str, sm: float, sc: float):
    # 1) comfy.sd.load_lora
    if sd is not None and hasattr(sd, "load_lora"):
        try:
            m, c = sd.load_lora(model, clip, lora_path, sm, sc)
            return m, c, True
        except Exception as e:
            print(f"[Conditional LoRA Loader] comfy.sd.load_lora failed: {e}")

    # 2) built-in nodes.LoraLoader
    try:
        from nodes import LoraLoader as _BuiltinLoraLoader
        try:
            m, c = _BuiltinLoraLoader().load_lora(model, clip, lora_name, sm, sc)
            return m, c, True
        except Exception as e:
            print(f"[Conditional LoRA Loader] nodes.LoraLoader failed: {e}")
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
        print(f"[Conditional LoRA Loader] fallback apply_lora failed: {e}")

    print("[Conditional LoRA Loader] All loaders failed -> passthrough.")
    return model, clip, False


# ---- Node (V3 schema) --------------------------------------------------------
class HYBS_ConditionalLoRALoader(io.ComfyNode):
    CONFIG_DIR = None

    @classmethod
    def _ensure_config_dir(cls):
        if cls.CONFIG_DIR is None:
            base = os.path.dirname(os.path.dirname(__file__))
            cls.CONFIG_DIR = os.path.join(base, "config")
            os.makedirs(cls.CONFIG_DIR, exist_ok=True)
        return cls.CONFIG_DIR

    @classmethod
    def _list_toml(cls):
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
            ],
            description="Conditionally apply one or more LoRAs based on regex matches in the positive prompt."
        )

    @staticmethod
    def _match(positive: str, pattern: str) -> bool:
        if not pattern:
            return False
        try:
            return re.search(pattern, positive or "") is not None
        except re.error as e:
            print(f"[Conditional LoRA Loader] Invalid regex in TOML: {e}")
            return False

    @classmethod
    def _load_toml(cls, fname: str):
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
            print(f"[Conditional LoRA Loader] TOML load error: {e}")
            return io.NodeOutput(model, clip)

        src = positive or ""
        applied_any = False

        for i, ent in enumerate(entries):
            trig = ent.get("trigger", "")
            name = ent.get("name", "")
            sm = float(ent.get("strength_model", 1.0))
            sc = float(ent.get("strength_clip", 1.0))

            matched = cls._match(src, trig)
            print(f"[Conditional LoRA Loader] #{i} matched={matched} trigger={trig!r} name={name!r} sm={sm} sc={sc}")
            if not matched:
                continue

            lora_path = folder_paths.get_full_path("loras", name)
            if not lora_path:
                print(f"[Conditional LoRA Loader] LoRA not found: {name}")
                continue

            try:
                new_model, new_clip, applied = _apply_lora(model, clip, lora_path, name, sm, sc)
                if applied:
                    print(f"[Conditional LoRA Loader] Applied LoRA: {name} (m={sm}, c={sc})")
                    model, clip = new_model, new_clip
                    applied_any = True
                else:
                    print(f"[Conditional LoRA Loader] Failed to apply LoRA: {name}")
            except Exception as e:
                print(f"[Conditional LoRA Loader] Exception while applying LoRA {name!r}: {e}")

        if not applied_any:
            print("[Conditional LoRA Loader] No LoRA applied (passthrough)")

        return io.NodeOutput(model, clip)

    @classmethod
    def fingerprint_inputs(cls, config_toml=None, **kwargs):
        try:
            base = cls._ensure_config_dir()
            path = os.path.join(base, config_toml) if config_toml else None
            mtime = os.path.getmtime(path) if path and os.path.isfile(path) else 0
        except Exception:
            mtime = 0
        return f"{config_toml}:{mtime}"
