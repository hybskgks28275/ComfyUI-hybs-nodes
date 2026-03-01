"""ComfyUI-hybs-nodes extension entrypoint."""

from .hybs_comfy_api import ComfyExtension, io

print("[HYBS] __init__.py import start")

WEB_DIRECTORY = "./web/js"

# v3 nodes
from .nodes.hybs_resolution_selector import HYBS_ResolutionSelector
from .nodes.hybs_random_resolution_selector import HYBS_RandomResolutionSelector
from .nodes.hybs_seed_list_generator import HYBS_SeedListGenerator
from .nodes.hybs_conditional_lora_loader import HYBS_ConditionalLoRALoader
from .nodes.hybs_group_bypasser_nodes import (
    HYBS_GroupBypasser_Parent,
    HYBS_GroupBypasser_Child,
    HYBS_GroupBypasser_Panel,
)

class HybsNodesExtension(ComfyExtension):
    """Comfy extension wrapper for HYBS custom nodes."""

    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [
            HYBS_ResolutionSelector,
            HYBS_RandomResolutionSelector,
            HYBS_SeedListGenerator,
            HYBS_ConditionalLoRALoader,
            HYBS_GroupBypasser_Parent,
            HYBS_GroupBypasser_Child,
            HYBS_GroupBypasser_Panel,
        ]


async def comfy_entrypoint() -> ComfyExtension:
    return HybsNodesExtension()
