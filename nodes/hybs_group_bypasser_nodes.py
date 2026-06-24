"""Backend marker nodes for Group Bypasser frontend UI."""

from ..hybs_comfy_api import io

_ANY = io.Custom("ANY")


class HYBS_GroupBypasser_Parent(io.ComfyNode):
    """Cascade source marker node."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="HYBS_GroupBypasser_Parent",
            display_name="Group Bypass Parent",
            category="HYBS/GroupBypasser",
            search_aliases=["group bypass parent", "cascade parent", "group marker parent"],
            essentials_category="Workflow/Control",
            inputs=[],
            outputs=[
                _ANY.Output(display_name="to_children", tooltip="UI-only link to Group Bypass Child from_parent."),
            ],
            description="Frontend-only cascade source marker. Backend no-op.",
        )

    @classmethod
    def execute(cls) -> io.NodeOutput:
        # Backend no-op marker.
        return io.NodeOutput(None)


class HYBS_GroupBypasser_Child(io.ComfyNode):
    """Cascade target marker node."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="HYBS_GroupBypasser_Child",
            display_name="Group Bypass Child",
            category="HYBS/GroupBypasser",
            search_aliases=["group bypass child", "cascade child", "group marker child"],
            essentials_category="Workflow/Control",
            inputs=[
                _ANY.Input("from_parent", tooltip="UI-only link from a Group Bypass Parent or another Child."),
            ],
            outputs=[
                _ANY.Output(display_name="to_children", tooltip="UI-only link to the next Group Bypass Child."),
            ],
            description="Frontend-controlled cascade target marker. Backend passes through its input.",
        )

    @classmethod
    def execute(cls, from_parent=None) -> io.NodeOutput:
        return io.NodeOutput(from_parent)


class HYBS_GroupBypasser_Panel(io.ComfyNode):
    """Frontend-only group bypass panel node."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="HYBS_GroupBypasser_Panel",
            display_name="Group Bypasser",
            category="HYBS/GroupBypasser",
            search_aliases=["group bypass", "panel", "group toggle", "cascade toggle"],
            essentials_category="Workflow/Control",
            inputs=[],
            outputs=[],
            description="Frontend-only panel for controlling group bypass states. Backend no-op.",
        )

    @classmethod
    def execute(cls) -> io.NodeOutput:
        return io.NodeOutput()
