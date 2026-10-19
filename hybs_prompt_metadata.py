"""Pure helpers for extracting prompts from ComfyUI metadata."""

import json
from typing import Any


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
    return "" if node_id is None else str(node_id).strip()


def _node_id_matches(actual_id: Any, target_id: str) -> bool:
    actual = _normalize_node_id(actual_id)
    if not actual or not target_id:
        return False
    return actual == target_id or actual == target_id.rsplit(":", 1)[-1]


def _prompt_from_workflow_id(workflow: dict[str, Any] | None, node_id: Any) -> str:
    target_id = _normalize_node_id(node_id)
    if not workflow or not target_id:
        return ""

    nodes = list(_iter_nodes(workflow))
    exact = [node for node in nodes if _normalize_node_id(node.get("id")) == target_id]
    matches = exact or [node for node in nodes if _node_id_matches(node.get("id"), target_id)]
    if len(matches) != 1:
        return ""
    node = matches[0]
    return _first_string(node.get("widgets_values", [])) or _first_string(node.get("properties", {}))


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


