from ..hybs_comfy_api import io
from ..hybs_resolution_common import load_resolution_combos

class HYBS_ResolutionSelector(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        combos = load_resolution_combos()  # load at startup
        options = [f"{w}x{h}" for (w, h) in combos]
        return io.Schema(
            node_id="HYBS_ResolutionSelector",
            display_name="Resolution Selector",
            category="HYBS/ResolutionSelector",
            search_aliases=["resolution", "size", "width", "height"],
            essentials_category="Utilities/Resolution",
            inputs=[io.Combo.Input("resolution", options=options)],
            outputs=[io.Int.Output(display_name="width"), io.Int.Output(display_name="height")],
            description="Select a resolution from predefined combos (loaded from JSON on startup)."
        )

    @classmethod
    def execute(cls, resolution: str) -> io.NodeOutput:
        w, h = map(int, resolution.split("x"))
        return io.NodeOutput(w, h)
