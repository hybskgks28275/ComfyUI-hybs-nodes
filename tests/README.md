# Regression tests

These tests use Python's standard library and Node.js. They do not load models or require a ComfyUI installation.

```sh
python -m unittest discover -s tests -v
node --experimental-vm-modules tests/frontend.test.mjs
```

The frontend harness models the Nodes 2.0 widget store, including same-name value preservation and explicit widget removal. It covers restored selections, row addition/deletion, user sizing, connected prompt outputs and Group Bypasser callbacks. The Python tests cover selection decoding, LoRA fallback order and failure behavior, prompt ID resolution and browser import paths derived from `WEB_DIRECTORY`.

For runtime validation, also load all node schemas in ComfyUI and test the affected widgets in the browser. The lightweight tests do not replace a real renderer or exercise model inference.

Per-row ON/OFF regression checks cover skipping disabled files, preserving active rows, retaining selections and strengths after toggle/restore, and defaulting older workflows to ON.

Load LoRA Stack coverage includes empty selection, zero strengths, MODEL-only / TE-only / combined loading, ordered multiple-row application, invalid rows, missing files and application failure. Frontend checks cover row addition/deletion, zero rows, restore and legacy workflows, folder-tree construction with Windows paths, strength bounds, held-button repetition, keyboard activation and cancellation cleanup.
