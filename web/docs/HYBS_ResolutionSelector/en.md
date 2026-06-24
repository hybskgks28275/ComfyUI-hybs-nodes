# Resolution Selector

Selects one resolution from `config/resolution_combos.json` and outputs its `width` and `height`.

If the file is unavailable, the built-in default resolution list is used.

## Inputs

- **resolution**: Resolution in `<width>x<height>` format.

## Outputs

- **width**: Selected width.
- **height**: Selected height.

## Configuration

Edit `config/resolution_combos.json` with a non-empty array of integer width/height pairs:

```json
[
  [1024, 1024],
  [1152, 896],
  [896, 1152]
]
```
