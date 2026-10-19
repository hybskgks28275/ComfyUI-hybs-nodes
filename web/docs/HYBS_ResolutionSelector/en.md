# Resolution Selector

Selects one resolution from `config/resolution_combos.json` and outputs its width and height. If the file is missing, the built-in defaults are used.

## Configuration

Copy `config/resolution_combos.json.example` to `config/resolution_combos.json` and edit it. Each string is a display-only heading; each positive integer pair is a selectable resolution. Headings appear greyed out and cannot be selected by mouse or keyboard in either the classic renderer or Nodes 2.0.

```json
[
  "1024 x 1024 equivalent",
  [896, 1152],
  [1152, 896],
  [1024, 1024],
  "1280 x 1280 equivalent",
  [1120, 1440],
  [1440, 1120],
  [1280, 1280]
]
```

At least one resolution pair is required. Existing pair-only files continue to work. The sample includes 1024, 1280, 1536, 1792 and 2048 equivalent groups. Restart ComfyUI and reload the browser after changing the list to refresh this selector.

## Inputs and outputs

- **resolution**: Selected `<width>x<height>` value. Headings are never stored as values.
- **width**, **height**: Selected integer dimensions.

Existing workflows retain the same input name and saved value format. Heading text is a label supplied by the configuration, rather than an automatically calculated classification.
