import re
import os
from typing import Tuple

try:
    from comfy import sd  # 標準APIがあれば優先使用
except Exception:
    sd = None

import folder_paths
import comfy.utils as utils


# --- 内部: LoRA適用ローダー（複数の方法を順に試す） ---
def _load_lora(model, clip, lora_path: str, lora_name: str, strength_model: float, strength_clip: float):
    # 1) comfy.sd.load_lora
    if sd is not None and hasattr(sd, "load_lora"):
        try:
            m, c = sd.load_lora(model, clip, lora_path, strength_model, strength_clip)
            return m, c, True
        except Exception as e:
            print(f"[Conditional LoRA Loader] comfy.sd.load_lora failed: {e}")

    # 2) 標準ノード nodes.LoraLoader を直接呼ぶ
    try:
        from nodes import LoraLoader as _BuiltinLoraLoader
        try:
            m, c = _BuiltinLoraLoader().load_lora(model, clip, lora_name, strength_model, strength_clip)
            return m, c, True
        except Exception as e:
            print(f"[Conditional LoRA Loader] nodes.LoraLoader failed: {e}")
    except Exception:
        pass

    # 3) 低レベル適用（環境によっては存在しない）
    try:
        lora = utils.load_torch_file(lora_path, safe_load=True)
        if hasattr(utils, "apply_lora"):
            model = utils.apply_lora(model, lora, strength_model)
            if clip is not None and strength_clip != 0.0 and hasattr(utils, "apply_lora_to_clip"):
                clip = utils.apply_lora_to_clip(clip, lora, strength_clip)
            return model, clip, True
    except Exception as e:
        print(f"[Conditional LoRA Loader] fallback apply_lora failed: {e}")

    print("[Conditional LoRA Loader] All loaders failed -> passthrough.")
    return model, clip, False


class HYBS_ConditionalLoRALoader:
    """
    TOML 外部設定で複数 LoRA を条件適用するローダー。
    """

    CONFIG_DIR = None

    @classmethod
    def _ensure_config_dir(cls):
        if cls.CONFIG_DIR is None:
            base = os.path.dirname(os.path.dirname(__file__))  # .../ComfyUI-hybs-nodes/
            cls.CONFIG_DIR = os.path.join(base, "config")
            os.makedirs(cls.CONFIG_DIR, exist_ok=True)
        return cls.CONFIG_DIR

    @classmethod
    def _list_toml(cls):
        cdir = cls._ensure_config_dir()
        files = [f for f in os.listdir(cdir) if f.lower().endswith('.toml')]
        return sorted(files) if files else ["<put .toml in config>"]

    @classmethod
    def INPUT_TYPES(cls):
        tomls = cls._list_toml()
        return {
            "required": {
                "model": ("MODEL",),
                "clip": ("CLIP",),
                "positive": ("STRING", {"forceInput": True, "multiline": True, "default": ""}),
                "config_toml": (tomls, {"default": tomls[0]}),
            }
        }

    RETURN_TYPES = ("MODEL", "CLIP")
    RETURN_NAMES = ("model", "clip")
    FUNCTION = "conditional_lora_loader"
    CATEGORY = "HYBS/ConditionalLoRALoader"
    OUTPUT_NODE = False

    # --- 内部: マッチ判定（ComfyUIの意図に合わせて大文字小文字は特に操作しない） ---
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
                import tomllib as _toml  # Python 3.11+
                data = _toml.loads(open(full, 'rb').read())
            except Exception:
                import toml as _toml  # pip install toml
                data = _toml.loads(open(full, 'r', encoding='utf-8').read())
        except Exception as e:
            raise RuntimeError(f"Failed to parse TOML: {e}")
        if not isinstance(data, dict) or 'lora' not in data or not isinstance(data['lora'], list):
            raise ValueError("TOML must contain [[lora]] array")
        return data['lora']

    def conditional_lora_loader(self,
                                model, clip,
                                positive: str,
                                config_toml: str,
                                ) -> Tuple[object, object]:
        """ComfyUI 実行関数: 条件が一致したエントリの LoRA を順に適用"""
        try:
            entries = self._load_toml(config_toml)
        except Exception as e:
            print(f"[Conditional LoRA Loader] TOML load error: {e}")
            return (model, clip)

        applied_any = False
        for i, ent in enumerate(entries):
            trig = ent.get('trigger', '')
            name = ent.get('name', '')
            sm = float(ent.get('strength_model', 1.0))
            sc = float(ent.get('strength_clip', 1.0))

            matched = self._match(positive, trig)
            print(f"[Conditional LoRA Loader] #{i} matched={matched} trigger='{trig}' name='{name}' sm={sm} sc={sc}")
            if not matched:
                continue

            lora_path = folder_paths.get_full_path("loras", name)
            if not lora_path:
                print(f"[Conditional LoRA Loader] LoRA not found: {name}")
                continue

            try:
                new_model, new_clip, applied = _load_lora(model, clip, lora_path, name, sm, sc)
                if applied:
                    print(f"[Conditional LoRA Loader] Applied LoRA: {name} (m={sm}, c={sc})")
                    model, clip = new_model, new_clip
                    applied_any = True
                else:
                    print(f"[Conditional LoRA Loader] Failed to apply LoRA: {name}")
            except Exception as e:
                print(f"[Conditional LoRA Loader] Exception while applying LoRA '{name}': {e}")

        if not applied_any:
            print("[Conditional LoRA Loader] No LoRA applied (passthrough)")
        return (model, clip)

    @classmethod
    def IS_CHANGED(cls, config_toml=None, **kwargs):
        """TOML の更新時刻（mtime）を鍵に含め、ファイル更新で再実行させる。"""
        try:
            base = cls._ensure_config_dir()
            path = os.path.join(base, config_toml) if config_toml else None
            mtime = os.path.getmtime(path) if path and os.path.isfile(path) else 0
        except Exception:
            mtime = 0
        key = (config_toml, mtime)
        return str(hash(key))


NODE_CLASS_MAPPINGS = {
    "Conditional LoRA Loader": HYBS_ConditionalLoRALoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Conditional LoRA Loader": "Conditional LoRA Loader",
}