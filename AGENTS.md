# AGENTS.md

Guidance for automated coding agents working in this repository.

## Repository Overview

- This is a ComfyUI custom node package.
- Python backend nodes live in `nodes/`.
- Shared Python helpers live at the repository root, such as `hybs_comfy_api.py` and `hybs_resolution_common.py`.
- Frontend extensions live in `web/js/`.
- Example configuration files live in `config/`.
- Example workflows live in `workflow/`.

## Development Notes

- Keep changes small and consistent with the existing node style.
- Prefer the ComfyUI V3 schema APIs already used in this repository.
- Preserve compatibility fallbacks around ComfyUI imports unless the task explicitly removes them.
- Do not commit user-local config files; update `*.example` files when documenting new config options.
- If adding a node, register it through the package entrypoint and document it in both `README.md` and `README_ja.md` when user-facing.

## Validation

Run lightweight syntax checks before finishing Python changes:

```powershell
python -m compileall .
```

For frontend-only changes, inspect the affected `web/js/` file and, when possible, test inside ComfyUI because behavior depends on the browser-side ComfyUI app runtime.

## Style

- Use straightforward Python with explicit names.
- Keep comments brief and useful.
- Follow existing category and display-name conventions for nodes.
- Avoid unrelated formatting churn.
