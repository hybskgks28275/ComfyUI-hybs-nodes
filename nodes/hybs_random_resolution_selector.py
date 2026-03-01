"""Random resolution selector node."""

from ..hybs_comfy_api import io
from ..hybs_resolution_common import load_resolution_combos, get_resolution_config_mtime


class HYBS_RandomResolutionSelector(io.ComfyNode):
    """Select a deterministic resolution based on seed and combo list."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="HYBS_RandomResolutionSelector",
            display_name="Random Resolution Selector",
            category="HYBS/ResolutionSelector",
            search_aliases=["random resolution", "size by seed", "deterministic size"],
            essentials_category="Utilities/Resolution",
            inputs=[io.Int.Input("seed", default=0, min=0, tooltip="Deterministic pick: index = seed % len(combos)")],
            outputs=[io.Int.Output(display_name="width"), io.Int.Output(display_name="height")],
            description="Selects a (width, height) from a list based on seed. Reloads JSON on every execution."
        )

    @classmethod
    def execute(cls, seed: int) -> io.NodeOutput:
        combos = load_resolution_combos()  # Reload every execution.
        idx = seed % len(combos)
        w, h = combos[idx]
        return io.NodeOutput(w, h)

    @classmethod
    def fingerprint_inputs(cls, seed: int = 0, **kwargs) -> str:
        # Re-run when JSON changes by including its mtime.
        mtime = get_resolution_config_mtime()
        return f"{seed}:{mtime}"
