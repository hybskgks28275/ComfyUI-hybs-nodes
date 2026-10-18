"""Resolution selector node."""

from ..hybs_comfy_api import io
from ..hybs_resolution_common import load_resolution_entries


class HYBS_ResolutionSelector(io.ComfyNode):
    """Select a fixed resolution from configured combos."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        entries = load_resolution_entries()  # Loaded on schema build.
        options = [f"{entry[0]}x{entry[1]}" for entry in entries if not isinstance(entry, str)]
        display_entries = [entry if isinstance(entry, str) else list(entry) for entry in entries]
        return io.Schema(
            node_id="HYBS_ResolutionSelector",
            display_name="Resolution Selector",
            category="HYBS/ResolutionSelector",
            search_aliases=["resolution", "size", "width", "height"],
            essentials_category="Utilities/Resolution",
            inputs=[io.Combo.Input(
                "resolution", options=options,
                extra_dict={"hybs_resolution_entries": display_entries},
                tooltip="Resolution pair loaded from config/resolution_combos.json. Text entries are non-selectable headings.",
            )],
            outputs=[io.Int.Output(display_name="width", tooltip="Width of the selected resolution."), io.Int.Output(display_name="height", tooltip="Height of the selected resolution.")],
            description="Select a resolution from predefined combos loaded from JSON on startup.",
        )

    @classmethod
    def execute(cls, resolution: str) -> io.NodeOutput:
        w, h = map(int, resolution.split("x"))
        return io.NodeOutput(w, h)
