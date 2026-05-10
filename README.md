# ComfyUI-hybs-nodes

Custom nodes for ComfyUI, including resolution utilities, conditional LoRA loading, and group bypass control.

[日本語はこちら](README_ja.md)

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

### Diffusion Model List

- Category: `HYBS/Model`
- Inputs:
  - `model` (COMBO, auto-growing)
- Outputs:
  - `model names` (LIST)
  - `count` (INT)
- Behavior:
  - Uses dropdowns populated from the `models/unet` folder.
  - Starts with one dropdown and adds another as models are selected.
  - Returns the selected UNet filenames as a list.
  - `count` increases only for dropdowns with an actual model selected.
  - `model names` keeps the same order as the visible dropdowns.
  - For ComfyLab `XY Plot`, use `model names` as the label source and pair it with a standard ComfyUI diffusion model node as needed.

### Load Image Prompt Metadata

- Category: `HYBS/LoadImage`
- Inputs:
  - `image` (COMBO/upload): image from the ComfyUI input folder
  - `positive_node_id` (STRING): node ID to read as the positive prompt
  - `negative_node_id` (STRING): node ID to read as the negative prompt
- Outputs:
  - `IMAGE`
  - `positive` (STRING)
  - `negative` (STRING)
- Behavior:
  - Loads the selected image like a Load Image node.
  - Reads embedded ComfyUI workflow metadata when present.
  - Useful for img2img/i2i workflows where you want to reuse the prompt embedded in a source image.
  - Finds nodes by `id` and returns the first string in each node's `widgets_values`.
  - Also reads the execution `prompt` metadata format by node ID, using `inputs.text` when present.
  - Node IDs are intentionally blank by default; enter the positive/negative prompt node IDs from the source workflow.
  - Subgraph IDs such as `82:78` are supported.
  - Raises an error when workflow/prompt metadata is missing or the specified IDs do not resolve to prompt text.
- Sample:
  - Open `workflow/LoadImagePromptMetadata.json`.
  - Use `workflow/LoadImageSample.png` as the sample source image.
  - The sample image contains embedded prompt metadata that can be read by node ID.

### Load Image Prompt Metadata Advance

- Category: `HYBS/LoadImage`
- Inputs:
  - `image` (COMBO/upload): image from the ComfyUI input folder
  - `node id 1`, `node id 2`, ...: prompt node IDs, starting with one row and growing as you fill them
- Outputs:
  - `IMAGE`
  - `prompt_1`, `prompt_2`, ... (STRING): individual prompt outputs that grow with the node ID rows
- Behavior:
  - Use this when img2img/i2i workflows need to read more than positive/negative from source-image metadata.
  - Each node ID is resolved the same way as `Load Image Prompt Metadata`.
  - Blank rows are ignored, and an empty row plus its `prompt_#` output is kept at the end for adding the next prompt node ID.
  - Up to 20 prompt node IDs can be used.
  - Raises an error when no prompt node ID is provided, metadata is missing, or any specified ID does not resolve to prompt text.

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
