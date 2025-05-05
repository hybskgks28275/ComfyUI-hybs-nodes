# ComfyUI-hybs-nodes

Various custom nodes will be added.

## Nodes

### Resolution Selector

Provides a manual resolution selection node via a dropdown menu.
Allows manual selection of a resolution from a dropdown menu populated from `config/resolution_combos.json` (or the default list).

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

## Configuration

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

## Installation

1. **Clone** this repository into your ComfyUI `custom_nodes/` folder:

   ```bash
   cd path/to/ComfyUI/extensions
   git clone https://github.com/hybskgks28275/ComfyUI-hybs-nodes.git
   ```

2. Ensure the directory structure:

   ```text
   ComfyUI/
   └── extensions/
       └── ComfyUI-hybs-nodes/
           ├── config/
           │   └── resolution_combos.json.example
           ├── nodes/
           │   └── hybs_resolution_selector.py
           ├── LICENSE
           ├── README.md
           ├── __init__.py
           └── pyproject.toml
   ```

3. **Restart** ComfyUI. The nodes **Resolution Selector** **Random Resolution Selector** and will appear under the **HYBS/ResolutionSelector** category.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.