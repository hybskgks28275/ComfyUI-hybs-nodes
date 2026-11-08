# Load LoRA Stack

Select a LoRA from a folder tree and apply it to MODEL, TE (CLIP), or both.
Category: `HYBS/LoRA`. Node ID: `HYBS_LoadLoRAStack`.

MODEL and TE / CLIP strength controls are displayed side by side. Each row has an `ON / OFF` switch that keeps its filename, strengths and position while disabling application. Disabled rows load no file and contribute no applied token. Switch states are saved/restored; rows from older workflows default to ON.

- Connect `model`, `clip`, or both. Each connection is optional; a disconnected output is `None`.
- Click the LoRA button to open the folder tree. Expand folders or search folders / filenames. Search results keep the folder hierarchy. The full relative path is preserved, including when filenames repeat in different folders.
- The default `NONE` applies no LoRA and passes connected inputs through. No file or enable toggle is required.
- Set MODEL and TE / CLIP strengths independently from -20 to 20. Click ± for 0.01 steps; hold for repeated changes after 350 ms. Releasing, canceling the pointer, or leaving the window stops repetition. Values can also be typed directly.
- `applied lora` returns applied `<lora:name:model_strength:clip_strength>` tokens separated by spaces, or an empty string when unused. The strength for a disconnected input is zero. Rows with both effective strengths at zero load no file.
- Click `Add LoRA` to add rows; use `Remove` on any row to delete it. Each row has independent MODEL and TE strengths. LoRAs apply from top to bottom, including duplicate selections. Removing all rows passes inputs through. Row count, selections and strengths are saved/restored; older single-row workflows remain supported. The existing `Load LoRA` node remains available.

Restart ComfyUI and reload the browser after installing the extension. Workflow files keep the selected relative path and numeric strengths. The frontend controls are backed by ordinary serializable inputs, which are also available through the API.
