"""Comfy API import compatibility helpers for V3 custom nodes."""

from __future__ import annotations

import traceback

try:
    from comfy_api.latest import ComfyExtension, io
except Exception as exc:  # pragma: no cover - runtime compatibility path
    print(f"[HYBS] comfy_api.latest import failed, fallback to comfy_api: {exc}")
    traceback.print_exc()
    from comfy_api import ComfyExtension, io

__all__ = ["ComfyExtension", "io"]
