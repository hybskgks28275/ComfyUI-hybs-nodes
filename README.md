# ComfyUI-hybs-nodes

Custom nodes for ComfyUI, including resolution utilities, conditional LoRA loading, and group bypass control.

## Compatibility

- Backend: V3 schema (`ComfyNode`, `Schema`, `ComfyExtension`, `comfy_entrypoint`)
- Frontend: Nodes 2.0 metadata-ready (`display_name`, `description`, `category`, `search_aliases`, `essentials_category`)
- API import fallback: `comfy_api.latest` -> `comfy_api`

## Nodes

### Resolution Selector

- Category: `HYBS/ResolutionSelector`
- Inputs:
  - `resolution` (COMBO): `"<width>x<height>"`
- Outputs:
  - `width` (INT)
  - `height` (INT)
- Behavior:
  - Loads options from `config/resolution_combos.json` (fallback to built-in defaults if file is missing).
  - Returns the selected width/height pair.

### Random Resolution Selector

- Category: `HYBS/ResolutionSelector`
- Inputs:
  - `seed` (INT)
- Outputs:
  - `width` (INT)
  - `height` (INT)
- Behavior:
  - Reloads `config/resolution_combos.json` on every execution.
  - Selects by `seed % len(combos)`.
  - Fingerprint includes config mtime, so file updates trigger re-execution.

### Seed List Generator

- Category: `HYBS/SeedGenerator`
- Inputs:
  - `count` (INT)
- Outputs:
  - `seed list` (LIST)
  - `count` (INT)
- Behavior:
  - Generates `count` random 32-bit seed values.

### Conditional LoRA Loader

- Category: `HYBS/ConditionalLoRALoader`
- Inputs:
  - `model` (MODEL)
  - `clip` (CLIP)
  - `positive` (STRING, multiline, `forceInput=True`)
  - `config_toml` (COMBO, from `config/*.toml`)
- Outputs:
  - `model` (MODEL)
  - `clip` (CLIP)
  - `applied loras` (STRING)
- Behavior:
  - Reads selected TOML each execution.
  - Applies all matching `[[lora]]` entries in order.
  - Loader fallback order:
    1. `comfy.sd.load_lora`
    2. built-in `nodes.LoraLoader`
    3. low-level fallback (`comfy.utils`)
- Wiring note:
  - Use LoRA-applied `model`/`clip` outputs downstream.
  - Text encoding must happen after LoRA application.

### Group Bypasser

Category for all nodes below: `HYBS/GroupBypasser`

#### Group Bypasser (Panel)

- Inputs: none
- Outputs: none
- Behavior:
  - Shows all groups in main graph + subgraphs.
  - Toggles group bypass state from one panel.
  - Supports order customization (`auto` / `custom` + drag-and-drop editor).
  - If a group contains a parent marker node, toggling can cascade to child-linked groups.

#### Group Bypass Parent

- Inputs: none
- Outputs:
  - `to_children` (ANY)
- Behavior:
  - Marker node for cascade root.
  - Backend no-op.

#### Group Bypass Child

- Inputs:
  - `from_parent` (ANY)
- Outputs:
  - `to_children` (ANY)
- Behavior:
  - Marker node for cascade target.
  - Supports child-to-child chaining.
  - Backend passes input through.

## Configuration

### `config/resolution_combos.json`

Non-empty array of integer pairs:

```json
[
  [1024, 1024],
  [1152, 896],
  [896, 1152]
]
```

### `config/*.toml` for Conditional LoRA

```toml
[[lora]]
trigger = "(?i)red\\s+dress"
name = "characters/wardrobe/red_dress_lora.safetensors"
strength_model = 1.0
strength_clip  = 1.0
```

Notes:
- Matching uses Python `re.search`.
- Escape backslashes in TOML strings (`\\s`, `\\b`, etc.).

## Installation

Install this extension using either method below.

### Option 1: ComfyUI Manager (Registry)

1. Open ComfyUI Manager.
2. In Custom Nodes Manager, search for `ComfyUI-hybs-nodes`.
3. Install it.
4. Restart ComfyUI.

### Option 2: Manual install

1. Clone into `ComfyUI/custom_nodes/`:

```bash
cd path/to/ComfyUI/custom_nodes
git clone https://github.com/hybskgks28275/ComfyUI-hybs-nodes.git
```

2. Install Python dependencies:
   - `pip install -r requirements.txt`

3. Restart ComfyUI.

## License

MIT. See [LICENSE](LICENSE).
