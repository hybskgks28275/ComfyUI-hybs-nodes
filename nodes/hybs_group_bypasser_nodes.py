from comfy_api.latest import io

_ANY = io.Custom("ANY")

class HYBS_GroupBypasser_Parent(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="HYBS_GroupBypasser_Parent",
            display_name="Group Bypass Parent",
            category="HYBS/GroupBypasser",
            inputs=[],
            outputs=[
                _ANY.Output(display_name="to_children"),
            ],
            description="Frontend-only marker node for cascade bypass. Backend no-op.",
        )

    @classmethod
    def execute(cls):
        # Backend no-op: output nothing meaningful (marker only)
        return io.NodeOutput(None)


class HYBS_GroupBypasser_Child(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="HYBS_GroupBypasser_Child",
            display_name="Group Bypass Child",
            category="HYBS/GroupBypasser",
            inputs=[
                _ANY.Input("from_parent", tooltip="UI only. Link marker."),
            ],
            outputs=[
                _ANY.Output(display_name="to_children"),
            ],
            description="Frontend-controlled marker. Backend is pass-through.",
        )

    @classmethod
    def execute(cls, from_parent=None):
        return io.NodeOutput(from_parent)


class HYBS_GroupBypasser_Panel(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="HYBS_GroupBypasser_Panel",
            display_name="Group Bypasser",
            category="HYBS/GroupBypasser",
            inputs=[],
            outputs=[],
            description="Frontend-only panel. Backend no-op.",
        )

    @classmethod
    def execute(cls):
        return io.NodeOutput()