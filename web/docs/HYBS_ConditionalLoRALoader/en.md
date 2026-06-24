# Conditional LoRA Loader

Applies every `[[lora]]` entry in the selected TOML file whose `trigger` regular expression matches the `positive` prompt. Matching entries are applied in file order.

Connect the returned `model` and `clip` to downstream nodes. Text encoding should happen after this node so the encoded conditioning uses the modified CLIP.

## Inputs

- **model**, **clip**: Base model and CLIP.
- **positive**: Prompt evaluated by each `trigger` pattern.
- **config_toml**: A TOML file from `config/`.

Each `[[lora]]` entry accepts `trigger`, `name`, `strength_model`, and `strength_clip`. Pattern matching uses Python `re.search`.

## Configuration

Place TOML files under `config/`. Escape backslashes in TOML strings such as `\\s` and `\\b`.

```toml
[[lora]]
trigger = "(?i)red\\s+dress"
name = "characters/wardrobe/red_dress_lora.safetensors"
strength_model = 1.0
strength_clip = 1.0
```

## Outputs

- **model**, **clip**: Values after every matching LoRA is applied.
- **applied loras**: Space-separated `<lora:name:model_strength:clip_strength>` tokens.
