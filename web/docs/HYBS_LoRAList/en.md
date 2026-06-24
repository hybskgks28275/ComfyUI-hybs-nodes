# LoRA List

Creates a LIST of LoRA filenames selected from `models/loras`.

The first row can be `NONE` as an unapplied comparison baseline and is returned as `null`. Use **add lora** to add rows. Selecting `NONE` in the second or later row removes that row. Use Double List as a separate strength list when comparing multiple LoRAs.

## Outputs

- **lora names**: Selected filenames in row order; the initial `NONE` is `null`.
- **count**: Number of entries, including the baseline.
