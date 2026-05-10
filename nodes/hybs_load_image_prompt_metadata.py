"""Load an image and extract prompts from embedded ComfyUI workflow metadata."""

from __future__ import annotations

import json
import os
from typing import Any

import numpy as np
import torch
from PIL import Image, ImageOps, ImageSequence, UnidentifiedImageError

import comfy.model_management
import node_helpers
import folder_paths

from ..hybs_comfy_api import io

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


def _decode_metadata_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        for encoding in ("utf-8", "utf-16", "latin-1"):
            try:
                return value.decode(encoding).strip("\x00")
            except UnicodeDecodeError:
                continue
    return None


def _coerce_json(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value

    text = _decode_metadata_value(value)
    if not text:
        return None

    candidates = [text]
    if "\x00" in text:
        candidates.extend(part for part in text.split("\x00") if part.strip())

    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate or candidate[0] not in "[{":
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    return None


def _find_json_metadata(metadata: dict[str, Any], preferred_keys: tuple[str, ...]) -> dict[str, Any] | None:
    for key in preferred_keys:
        value = _coerce_json(metadata.get(key))
        if isinstance(value, dict):
            return value

    return None


def _find_workflow(metadata: dict[str, Any]) -> dict[str, Any] | None:
    preferred_keys = ("workflow", "Workflow", "comfyui_workflow", "ComfyUI Workflow")
    workflow = _find_json_metadata(metadata, preferred_keys)
    if isinstance(workflow, dict) and "nodes" in workflow:
        return workflow

    for value in metadata.values():
        workflow = _coerce_json(value)
        if isinstance(workflow, dict) and "nodes" in workflow:
            return workflow

    return None


def _find_prompt(metadata: dict[str, Any]) -> dict[str, Any] | None:
    preferred_keys = ("prompt", "Prompt")
    prompt = _find_json_metadata(metadata, preferred_keys)
    if isinstance(prompt, dict):
        return prompt

    return None


def _iter_nodes(workflow: dict[str, Any]):
    stack = [workflow]
    while stack:
        current = stack.pop()
        nodes = current.get("nodes", [])
        if isinstance(nodes, list):
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                yield node
                for subgraph_key in ("subgraph", "workflow"):
                    subgraph = node.get(subgraph_key)
                    if isinstance(subgraph, dict):
                        stack.append(subgraph)

        definitions = current.get("definitions", {})
        subgraphs = definitions.get("subgraphs") if isinstance(definitions, dict) else None
        if isinstance(subgraphs, list):
            stack.extend(subgraph for subgraph in subgraphs if isinstance(subgraph, dict))


def _first_string(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for item in value.values():
            found = _first_string(item)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = _first_string(item)
            if found:
                return found
    return ""


def _normalize_node_id(node_id: Any) -> str:
    return str(node_id or "").strip()


def _node_id_matches(actual_id: Any, target_id: str) -> bool:
    actual = _normalize_node_id(actual_id)
    if not actual or not target_id:
        return False
    return actual == target_id or actual == target_id.rsplit(":", 1)[-1]


def _prompt_from_workflow_id(workflow: dict[str, Any] | None, node_id: Any) -> str:
    target_id = _normalize_node_id(node_id)
    if not workflow or not target_id:
        return ""

    for node in _iter_nodes(workflow):
        if not _node_id_matches(node.get("id"), target_id):
            continue

        widgets_values = node.get("widgets_values", [])
        prompt = _first_string(widgets_values)
        if prompt:
            return prompt

        return _first_string(node.get("properties", {}))

    return ""


def _prompt_from_api_prompt_id(prompt: dict[str, Any] | None, node_id: Any) -> str:
    target_id = _normalize_node_id(node_id)
    if not prompt or not target_id:
        return ""

    node = prompt.get(target_id)
    if not isinstance(node, dict):
        matches = [
            value
            for key, value in prompt.items()
            if _normalize_node_id(key).rsplit(":", 1)[-1] == target_id
        ]
        node = matches[0] if len(matches) == 1 else None

    if not isinstance(node, dict):
        return ""

    inputs = node.get("inputs", {})
    if isinstance(inputs, dict):
        text = inputs.get("text")
        if isinstance(text, str):
            return text

        prompt_text = _first_string(inputs)
        if prompt_text:
            return prompt_text

    return ""


def _prompt_from_id(workflow: dict[str, Any] | None, prompt: dict[str, Any] | None, node_id: Any) -> str:
    result = _prompt_from_workflow_id(workflow, node_id)
    if result:
        return result
    return _prompt_from_api_prompt_id(prompt, node_id)


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

class HYBS_LoadImagePromptMetadata(io.ComfyNode):
    """Load an image and return prompt strings from embedded workflow metadata."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        image_input_kwargs = {
            "options": _image_options(),
            "tooltip": "Image file from ComfyUI's input folder.",
        }
        if hasattr(io, "UploadType"):
            image_input_kwargs["upload"] = io.UploadType.image
        if hasattr(io, "FolderType"):
            image_input_kwargs["image_folder"] = io.FolderType.input

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
                    tooltip="Node ID to read as the positive prompt. Subgraph IDs like 82:78 are also supported.",
                ),
                io.String.Input(
                    "negative_node_id",
                    default="",
                    tooltip="Node ID to read as the negative prompt. Subgraph IDs like 82:78 are also supported.",
                ),
            ],
            outputs=[
                io.Image.Output(display_name="IMAGE"),
                io.String.Output(display_name="positive"),
                io.String.Output(display_name="negative"),
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
        image_path = _get_annotated_path(image)

        try:
            with node_helpers.pillow(Image.open, image_path) as img:
                metadata = _extract_image_metadata(img)
                workflow = _find_workflow(metadata)
                prompt = _find_prompt(metadata)
                output_image = _load_image_tensor(img)
        except UnidentifiedImageError as exc:
            raise ValueError(f"Could not load image: {image}") from exc

        if workflow is None and prompt is None:
            raise ValueError(f"No ComfyUI workflow or prompt metadata found in {image!r}")

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
        if isinstance(selection, dict):
            values = selection.get("selected", [])
        elif isinstance(selection, str):
            try:
                values = json.loads(selection)
            except json.JSONDecodeError:
                values = []
        else:
            values = []

        if not isinstance(values, list):
            return []

        return [_normalize_node_id(value) for value in values if _normalize_node_id(value)]

    @classmethod
    def define_schema(cls) -> io.Schema:
        image_input_kwargs = {
            "options": _image_options(),
            "tooltip": "Image file from ComfyUI's input folder.",
        }
        if hasattr(io, "UploadType"):
            image_input_kwargs["upload"] = io.UploadType.image
        if hasattr(io, "FolderType"):
            image_input_kwargs["image_folder"] = io.FolderType.input

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
                io.Image.Output(display_name="IMAGE"),
                *[
                    io.String.Output(display_name=f"prompt_{index}")
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

        if not cls._parse_selection(selection):
            return "At least one prompt node ID is required."
        if len(cls._parse_selection(selection)) > ADVANCED_MAX_PROMPTS:
            return f"Prompt node IDs must be {ADVANCED_MAX_PROMPTS} or fewer."

        return True

    @classmethod
    def execute(cls, image: str, selection="[]") -> io.NodeOutput:
        node_ids = cls._parse_selection(selection)
        if not node_ids:
            raise ValueError("At least one prompt node ID is required.")
        if len(node_ids) > ADVANCED_MAX_PROMPTS:
            raise ValueError(f"Prompt node IDs must be {ADVANCED_MAX_PROMPTS} or fewer.")

        image_path = _get_annotated_path(image)

        try:
            with node_helpers.pillow(Image.open, image_path) as img:
                metadata = _extract_image_metadata(img)
                workflow = _find_workflow(metadata)
                prompt = _find_prompt(metadata)
                output_image = _load_image_tensor(img)
        except UnidentifiedImageError as exc:
            raise ValueError(f"Could not load image: {image}") from exc

        if workflow is None and prompt is None:
            raise ValueError(f"No ComfyUI workflow or prompt metadata found in {image!r}")

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
