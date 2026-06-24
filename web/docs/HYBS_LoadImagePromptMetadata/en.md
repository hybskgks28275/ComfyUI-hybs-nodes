# Load Image Prompt Metadata

Loads an image like Load Image and reads positive and negative prompts from embedded ComfyUI `workflow` or `prompt` metadata.

This is intended for img2img/i2i workflows that reuse prompts from a source image. Enter the source workflow node IDs in **positive_node_id** and **negative_node_id**. IDs are blank by default; subgraph IDs such as `82:78` are supported.

The node raises an error when metadata is missing or either ID does not resolve to prompt text. See `workflow/LoadImagePromptMetadata.json` and `workflow/LoadImageSample.png` for an example.

## Outputs

- **IMAGE**: Loaded image.
- **positive**, **negative**: Prompt text from the specified node IDs.
