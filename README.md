# ComfyUI-hybs-nodes

Various custom nodes will be added.

## Nodes

### Resolution Selector

Provides a manual resolution selection node via a dropdown menu.
Allows manual selection of a resolution from `config/resolution_combos.json` (or the default list).

* **Category**: `HYBS/ResolutionSelector`
* **Inputs**:

  * `resolution` (Combo dropdown): A string in the format `"<width>x<height>"`.
* **Outputs**:

  * `width` (INT)
  * `height` (INT)
* **Behavior**:

  1. On startup, loads options from `config/resolution_combos.json`; if missing or invalid, falls back to default list.
  2. Populates the dropdown with `"WxH"` strings for each pair.
  3. Throws a runtime error if an unexpected format is selected.

### Random Resolution Selector

Provides a dynamic resolution selection node based on a seed input.

Outputs a resolution `(width, height)` from a predefined list based on a seed input. It reloads `config/resolution_combos.json` on each execution, so changes to the JSON file take immediate effect.

* **Category**: `HYBS/ResolutionSelector`
* **Inputs**:

  * `seed` (INT): The seed value; same seed always yields the same resolution.
* **Outputs**:

  * `width` (INT)
  * `height` (INT)
* **Behavior**:

  1. On each node execution, attempts to load `config/resolution_combos.json`; if missing, uses the default hardcoded list.
  2. Throws a runtime error if the JSON file exists but is malformed or has invalid format.
  3. Determines the index with `seed % len(combos)` to select the resolution.

### SeedListGenerator

Generates a list of random seed values.

* **Category**: `HYBS/SeedGenerator`
* **Inputs**:

  * `count` (INT): Number of random seeds to generate.
* **Outputs**:

  * `seed list` (LIST)
  * `count` (INT)

### Conditional LoRA Loader

Applies one or more LoRAs only when the incoming **positive** prompt matches regex patterns defined in an external TOML file.

* **Category**: `HYBS/ConditionalLoRALoader`
* **Inputs**:

  * `model` (MODEL)
  * `clip` (CLIP)
  * `positive` (STRING): `forceInput=True`, multiline. Provide the positive prompt **from another node**.
  * `config_toml` (Combo dropdown): Select a `.toml` from `config/`.
* **Outputs**:

  * `model` (MODEL)
  * `clip`  (CLIP)
* **Behavior**:

  1. On each execution, the selected TOML is read from `config/`. The node’s `IS_CHANGED` includes the file’s **mtime**, so saving the TOML triggers re‑execution on the next run.
  2. For each `[[lora]]` entry whose `trigger` (Python‑style regex) matches the **positive** prompt, the LoRA is applied.
  3. If multiple entries match, **all** are applied in order (top → bottom).
  4. LoRA loading tries, in order: `comfy.sd.load_lora` → built‑in `nodes.LoraLoader` → a low‑level fallback (if available). Logs show `matched=...`, `Applied LoRA: ...`, or errors.
* **Important wiring**:

  * Use the **LoRA‑applied** `model`/`clip` outputs from this node downstream.
  * Ensure **CLIP Text Encode** receives the **LoRA‑applied `clip`** (encode **after** applying LoRA). Otherwise the LoRA won’t affect conditioning.

#### TOML format

Place files in `custom_nodes/ComfyUI-hybs-nodes/config/*.toml`. Each file contains an array of `[[lora]]` entries:

```toml
# sample.toml — Conditional LoRA rules (English)
# Each [[lora]] entry is evaluated against the *positive* prompt using a Python-style regex.
# If multiple entries match, they are applied in order (top to bottom).
# `name` is a path relative to your `loras/` directory.

# Example 1: phrase “red dress” (case-insensitive), allowing one or more spaces
[[lora]]
trigger = "(?i)red\\s+dress"
name = "characters/wardrobe/red_dress_lora.safetensors"
strength_model = 1.0
strength_clip  = 1.0

# Example 2: either “nurse” or “white coat” (case-insensitive)
[[lora]]
trigger = "(?i)(nurse|white\\s*coat)"
name = "characters/nurse/nurse_v5.safetensors"
strength_model = 0.8
strength_clip  = 0.8

# Example 3: whole word “wizard” (case-insensitive)
[[lora]]
trigger = "(?i)\\bwizard\\b"
name = "styles/fantasy/wizard_style_v2.safetensors"
strength_model = 0.7
strength_clip  = 0.7

# Example 4: “short hair” but not “short hair cut” (case-insensitive, negative lookahead)
[[lora]]
trigger = "(?i)short\\s+hair(?!\\s*cut)"
name = "attributes/hair/short_hair_v1.safetensors"
strength_model = 0.6
strength_clip  = 0.6
```

*Notes*

* Regex is evaluated with Python’s `re.search`. If you want case‑insensitive matching, add the inline flag `(?i)` at the start of your pattern.
* Backslashes must be escaped in TOML strings (e.g., `\s`, `\b` → `\\s`, `\\b`).
* `name` must include the file extension and is resolved relative to your `loras/` directory.

## Configuration

### Resolution lists (`resolution_combos.json`)

Place your custom resolution list in `config/resolution_combos.json` at the root of the extension (next to `nodes/`). The file **must** contain a non-empty JSON array of integer pairs, e.g.:

```json
[
  [1024, 1024],
  [1088, 1088],
  [1152, 1152],
  [896, 1152],
  [832, 1216]
]
```

* If the file is missing, a built-in default list (1024–2048 squares and representative portrait/landscape) is used.
* If the file is present but invalid (empty array or incorrect format), the node will throw a value error.

### Conditional LoRA rules (TOML)

Place TOML files under `custom_nodes/ComfyUI-hybs-nodes/config/*.toml`. Each file defines a list of rules using a `[[lora]]` array. For each entry:

* `trigger`: **Python-style regex** evaluated against the incoming **positive** prompt.
* `name`: LoRA file path **relative to** your `loras/` directory (subfolders allowed; include the extension, e.g., `.safetensors`).
* `strength_model`, `strength_clip`: LoRA weights (default `1.0` if omitted).
* If multiple entries match, they are **all applied in order** (top → bottom).

**Sample (`config/sample.toml`)**

```toml
# Each [[lora]] entry is evaluated against the *positive* prompt using a Python-style regex.
# If multiple entries match, they are applied in order (top to bottom).
# `name` is a path relative to your `loras/` directory.

# Example 1: phrase “red dress” (case-insensitive), allowing one or more spaces
[[lora]]
trigger = "(?i)red\s+dress"
name = "characters/wardrobe/red_dress_lora.safetensors"
strength_model = 1.0
strength_clip  = 1.0

# Example 2: either “nurse” or “white coat” (case-insensitive)
[[lora]]
trigger = "(?i)(nurse|white\s*coat)"
name = "characters/nurse/nurse_v5.safetensors"
strength_model = 0.8
strength_clip  = 0.8

# Example 3: whole word “wizard” (case-insensitive)
[[lora]]
trigger = "(?i)\bwizard\b"
name = "styles/fantasy/wizard_style_v2.safetensors"
strength_model = 0.7
strength_clip  = 0.7

# Example 4: “short hair” but not “short hair cut” (case-insensitive, negative lookahead)
[[lora]]
trigger = "(?i)short\s+hair(?!\s*cut)"
name = "attributes/hair/short_hair_v1.safetensors"
strength_model = 0.6
strength_clip  = 0.6
```

**Notes**

* Regex is evaluated with Python’s `re.search`. To make it case-insensitive, add the inline flag `(?i)` to your pattern.
* Escape backslashes in TOML strings (e.g., `\s`, `\b`).
* Ensure your routing uses the **LoRA-applied `clip`** for Text Encode downstream, or the LoRA will not affect conditioning.

## Installation

1. **Clone** this repository into your ComfyUI `custom_nodes/` folder:

   ```bash
   cd path/to/ComfyUI/extensions
   git clone https://github.com/hybskgks28275/ComfyUI-hybs-nodes.git
   ```

2. Ensure the directory structure:

   ```text
   ComfyUI/
   └── custom_nodes/
       └── ComfyUI-hybs-nodes/
           ├── config/
           │   ├── lora_condition.toml.example
           │   └── resolution_combos.json.example
           ├── nodes/
           │   ├── hybs_resolution_selector.py
           │   ├── hybs_seed_list_generator.py
           │   └── hybs_conditional_lora_loader.py
           ├── LICENSE
           ├── README.md
           ├── __init__.py
           └── pyproject.toml
   ```

3. **Restart** ComfyUI. The nodes **Resolution Selector**, **Random Resolution Selector** will appear under **HYBS/ResolutionSelector**, and **Conditional LoRA Loader** will appear under **HYBS/ConditionalLoRALoader**.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
