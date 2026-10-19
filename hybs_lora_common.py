"""LoRA application fallbacks shared by both loader nodes."""

import os

import comfy.utils as utils

try:
    from comfy import sd
except Exception:
    sd = None


def lora_token(name: str, strength_model: float, strength_clip: float) -> str:
    stem = os.path.splitext(os.path.basename(name))[0]
    return f"<lora:{stem}:{strength_model}:{strength_clip}>"


def apply_lora(model, clip, lora_path, lora_name, sm, sc, *, log):
    if sd is not None and hasattr(sd, "load_lora"):
        try:
            result_model, result_clip = sd.load_lora(model, clip, lora_path, sm, sc)
            return result_model, result_clip, True
        except Exception as exc:
            log(f"comfy.sd.load_lora failed: {exc}")

    try:
        from nodes import LoraLoader
    except Exception:
        LoraLoader = None
    if LoraLoader is not None:
        try:
            result_model, result_clip = LoraLoader().load_lora(model, clip, lora_name, sm, sc)
            return result_model, result_clip, True
        except Exception as exc:
            log(f"nodes.LoraLoader failed: {exc}")

    try:
        lora = utils.load_torch_file(lora_path, safe_load=True)
        if hasattr(utils, "apply_lora"):
            result_model = utils.apply_lora(model, lora, sm)
            result_clip = clip
            if clip is not None and sc != 0.0 and hasattr(utils, "apply_lora_to_clip"):
                result_clip = utils.apply_lora_to_clip(clip, lora, sc)
            return result_model, result_clip, True
    except Exception as exc:
        log(f"fallback apply_lora failed: {exc}")

    return model, clip, False
