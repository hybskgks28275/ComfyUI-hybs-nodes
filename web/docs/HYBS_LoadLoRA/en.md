# Load LoRA

Applies one LoRA selected from `models/loras` to a MODEL and CLIP.

`NONE`, `null`, and an empty value mean no LoRA is applied; the input model and CLIP pass through unchanged. This is useful when comparing an unapplied baseline with a LoRA-applied workflow.

## Inputs

- **model**, **clip**: Values to modify.
- **lora_name**: LoRA filename. Defaults to `NONE`.
- **strength_model**: LoRA strength for MODEL.
- **strength_clip**: LoRA strength for CLIP.

## Outputs

- **model**, **clip**: Modified values, or the original values for `NONE`.
- **applied lora**: Applied LoRA token; empty for `NONE`.
