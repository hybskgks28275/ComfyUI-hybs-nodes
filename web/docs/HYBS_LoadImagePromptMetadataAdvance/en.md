# Load Image Prompt Metadata Advance

Loads an image and extracts prompt text from any number of source workflow node IDs.

Use this for img2img/i2i workflows that need more than the positive and negative prompts. The widget starts with one node-ID row and grows as rows are filled. Blank rows are ignored, and up to 20 IDs can be specified.

The node raises an error when no ID is supplied, metadata is missing, or any supplied ID does not resolve to prompt text.

## Outputs

- **IMAGE**: Loaded image.
- **prompt_1** through **prompt_20**: Prompt text in the specified node-ID order. Unused outputs are empty strings.
