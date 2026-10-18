"""Load an image and extract prompts from embedded ComfyUI workflow metadata."""

from __future__ import annotations

import os
from typing import Any

import numpy as np
import torch
from PIL import Image, ImageOps, ImageSequence, UnidentifiedImageError

import comfy.model_management
import node_helpers
import folder_paths

from ..hybs_comfy_api import io
from ..hybs_selection import selection_values
from ..hybs_prompt_metadata import (
    _find_workflow, _find_prompt, _prompt_from_id, _normalize_node_id,
)

LOG_PREFIX = '[HYBS]["Load Image Prompt Metadata"]'
ADVANCED_MAX_PROMPTS = 20


def _log(message: str) -> None:
    print(f"{LOG_PREFIX} {message}")


def _image_options() -> list[str]:
    input_dir = folder_paths.get_input_directory()
    files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
    files = folder_paths.filter_files_content_types(files, ["image"])
    return sorted(files) if files else ["<put images in input>"]


def _get_annotated_path(filename: str) -> str:
    if hasattr(folder_paths, "get_annotated_filepath"):
        return folder_paths.get_annotated_filepath(filename)
    return os.path.join(folder_paths.get_input_directory(), filename)


def _extract_image_metadata(image: Image.Image) -> dict[str, Any]:
    metadata: dict[str, Any] = dict(getattr(image, "info", {}) or {})

    try:
        exif = image.getexif()
    except Exception:
        exif = None

    if exif:
        for key, value in exif.items():
            metadata[str(key)] = value

    return metadata


def _load_image_tensor(image: Image.Image) -> torch.Tensor:
    output_images = []
    width = None
    height = None
    dtype = comfy.model_management.intermediate_dtype()
    excluded_formats = ["MPO"]

    for frame in ImageSequence.Iterator(image):
        frame = node_helpers.pillow(ImageOps.exif_transpose, frame)

        if frame.mode == "I":
            frame = frame.point(lambda i: i * (1 / 255))

        frame = frame.convert("RGB")
        if not output_images:
            width, height = frame.size
        elif frame.size != (width, height):
            continue

        array = np.asarray(frame).astype(np.float32) / 255.0
        tensor = torch.from_numpy(array)[None,].to(dtype=dtype)
        output_images.append(tensor)

        if getattr(image, "format", None) in excluded_formats:
            break

    if not output_images:
        raise ValueError("No image frames could be loaded.")

    if len(output_images) > 1:
        return torch.cat(output_images, dim=0)

    return output_images[0]

def _image_input_kwargs() -> dict[str, Any]:
    kwargs = {
        "options": _image_options(),
        "tooltip": "Image from ComfyUI's input folder that contains workflow or prompt metadata.",
    }
    if hasattr(io, "UploadType"):
        kwargs["upload"] = io.UploadType.image
    if hasattr(io, "FolderType"):
        kwargs["image_folder"] = io.FolderType.input
    return kwargs


def _load_image_with_metadata(image: str):
    try:
        with node_helpers.pillow(Image.open, _get_annotated_path(image)) as img:
            metadata = _extract_image_metadata(img)
            workflow = _find_workflow(metadata)
            prompt = _find_prompt(metadata)
            output_image = _load_image_tensor(img)
    except UnidentifiedImageError as exc:
        raise ValueError(f"Could not load image: {image}") from exc
    if workflow is None and prompt is None:
        raise ValueError(f"No ComfyUI workflow or prompt metadata found in {image!r}")
    return output_image, workflow, prompt


class HYBS_LoadImagePromptMetadata(io.ComfyNode):
    """Load an image and return prompt strings from embedded workflow metadata."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        image_input_kwargs = _image_input_kwargs()

        return io.Schema(
            node_id="HYBS_LoadImagePromptMetadata",
            display_name="Load Image Prompt Metadata",
            category="HYBS/LoadImage",
            search_aliases=["load image", "metadata", "workflow", "prompt", "positive", "negative"],
            essentials_category="Input/Image",
            inputs=[
                io.Combo.Input("image", **image_input_kwargs),
                io.String.Input(
                    "positive_node_id",
                    default="",
                    tooltip="Node ID to read as the positive prompt. Subgraph IDs such as 82:78 are supported.",
                ),
                io.String.Input(
                    "negative_node_id",
                    default="",
                    tooltip="Node ID to read as the negative prompt. Subgraph IDs such as 82:78 are supported.",
                ),
            ],
            outputs=[
                io.Image.Output(display_name="IMAGE", tooltip="Loaded image."),
                io.String.Output(display_name="positive", tooltip="Prompt text read from positive_node_id."),
                io.String.Output(display_name="negative", tooltip="Prompt text read from negative_node_id."),
            ],
            description="Load an image and extract positive/negative prompts from embedded ComfyUI workflow metadata by node ID.",
        )

    @classmethod
    def validate_inputs(cls, image: str, **kwargs) -> bool | str:
        if not image or image.startswith("<"):
            return "Select an image from the input folder."

        path = _get_annotated_path(image)
        if not os.path.isfile(path):
            return f"Image not found: {image}"

        return True

    @classmethod
    def execute(cls, image: str, positive_node_id: str, negative_node_id: str) -> io.NodeOutput:
        output_image, workflow, prompt = _load_image_with_metadata(image)

        positive = _prompt_from_id(workflow, prompt, positive_node_id)
        negative = _prompt_from_id(workflow, prompt, negative_node_id)
        missing = []
        if not positive:
            missing.append(f"positive node ID {positive_node_id!r}")
        if not negative:
            missing.append(f"negative node ID {negative_node_id!r}")
        if missing:
            raise ValueError(f"Could not extract prompt text for: {', '.join(missing)}")

        return io.NodeOutput(output_image, positive, negative)

    @classmethod
    def fingerprint_inputs(cls, image=None, **kwargs) -> str:
        try:
            path = _get_annotated_path(image) if image else None
            mtime = os.path.getmtime(path) if path and os.path.isfile(path) else 0
        except Exception:
            mtime = 0
        return f"{image}:{mtime}"


class HYBS_LoadImagePromptMetadataAdvance(io.ComfyNode):
    """Load an image and return any number of prompt strings by node ID."""

    @classmethod
    def _parse_selection(cls, selection) -> list[str]:
        values = selection_values(selection)

        return [_normalize_node_id(value) for value in values if _normalize_node_id(value)]

    @classmethod
    def define_schema(cls) -> io.Schema:
        image_input_kwargs = _image_input_kwargs()

        return io.Schema(
            node_id="HYBS_LoadImagePromptMetadataAdvance",
            display_name="Load Image Prompt Metadata Advance",
            category="HYBS/LoadImage",
            search_aliases=["load image", "metadata", "workflow", "prompt", "node id", "advanced"],
            essentials_category="Input/Image",
            inputs=[
                io.Combo.Input("image", **image_input_kwargs),
                io.String.Input(
                    "selection",
                    default="[]",
                    socketless=True,
                    tooltip="Internal prompt node ID list managed by the frontend widget.",
                ),
            ],
            outputs=[
                io.Image.Output(display_name="IMAGE", tooltip="Loaded image."),
                *[
                    io.String.Output(display_name=f"prompt_{index}", tooltip=f"Prompt text read from node ID {index}.")
                    for index in range(1, ADVANCED_MAX_PROMPTS + 1)
                ],
            ],
            description="Load an image and extract any number of prompt strings from embedded ComfyUI workflow metadata by node ID.",
        )

    @classmethod
    def validate_inputs(cls, image: str, selection="[]", **kwargs) -> bool | str:
        base_validation = HYBS_LoadImagePromptMetadata.validate_inputs(image=image)
        if base_validation is not True:
            return base_validation

        node_ids = cls._parse_selection(selection)
        if not node_ids:
            return "At least one prompt node ID is required."
        if len(node_ids) > ADVANCED_MAX_PROMPTS:
            return f"Prompt node IDs must be {ADVANCED_MAX_PROMPTS} or fewer."

        return True

    @classmethod
    def execute(cls, image: str, selection="[]") -> io.NodeOutput:
        node_ids = cls._parse_selection(selection)
        if not node_ids:
            raise ValueError("At least one prompt node ID is required.")
        if len(node_ids) > ADVANCED_MAX_PROMPTS:
            raise ValueError(f"Prompt node IDs must be {ADVANCED_MAX_PROMPTS} or fewer.")

        output_image, workflow, prompt = _load_image_with_metadata(image)

        prompts = []
        missing = []
        for node_id in node_ids:
            prompt_text = _prompt_from_id(workflow, prompt, node_id)
            if prompt_text:
                prompts.append(prompt_text)
            else:
                missing.append(node_id)

        if missing:
            joined_missing = ", ".join(repr(node_id) for node_id in missing)
            raise ValueError(f"Could not extract prompt text for node ID(s): {joined_missing}")

        prompt_outputs = prompts[:ADVANCED_MAX_PROMPTS]
        prompt_outputs.extend([""] * (ADVANCED_MAX_PROMPTS - len(prompt_outputs)))

        return io.NodeOutput(output_image, *prompt_outputs)

    @classmethod
    def fingerprint_inputs(cls, image=None, **kwargs) -> str:
        return HYBS_LoadImagePromptMetadata.fingerprint_inputs(image=image, **kwargs)
