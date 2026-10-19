"""Decode the selection payload shared by dynamic list nodes."""

import json


def selection_values(selection) -> list:
    if isinstance(selection, dict):
        values = selection.get("selected", [])
    elif isinstance(selection, str):
        try:
            values = json.loads(selection)
        except json.JSONDecodeError:
            return []
    else:
        return []
    return values if isinstance(values, list) else []
