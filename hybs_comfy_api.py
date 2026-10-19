"""Comfy API import compatibility helpers for V3 custom nodes."""

from __future__ import annotations

import traceback

LOG_PREFIX = '[HYBS]["ComfyAPI"]'

try:
    from comfy_api.latest import ComfyExtension, io
except Exception as exc:  # pragma: no cover - runtime compatibility path
    print(f"{LOG_PREFIX} comfy_api.latest import failed, fallback to comfy_api: {exc}")
    traceback.print_exc()
    from comfy_api import ComfyExtension, io

def resolve_type(name: str):
    """Keep socket type compatibility across Comfy API versions."""
    for candidate in (name, name[:1].upper() + name[1:].lower()):
        resolved = getattr(io, candidate, None)
        if resolved is not None:
            return resolved
    return io.Custom(name)


__all__ = ["ComfyExtension", "io", "resolve_type"]
