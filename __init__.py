import traceback
from comfy_api.latest import ComfyExtension, io

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
    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        nodes: list[type[io.ComfyNode]] = []

        def _safe_add(import_path: str, names: list[str]):
            try:
                mod = __import__(import_path, fromlist=names)
                for n in names:
                    nodes.append(getattr(mod, n))
                print(f"[HYBS] Loaded: {import_path} {names}")
            except Exception:
                print(f"[HYBS] Import failed: {import_path} {names}")
                traceback.print_exc()
        
        _safe_add("custom_nodes.ComfyUI-hybs-nodes.nodes.hybs_resolution_selector", ["HYBS_ResolutionSelector"])
        _safe_add("custom_nodes.ComfyUI-hybs-nodes.nodes.hybs_random_resolution_selector", ["HYBS_RandomResolutionSelector"])
        _safe_add("custom_nodes.ComfyUI-hybs-nodes.nodes.hybs_seed_list_generator", ["HYBS_SeedListGenerator"])
        _safe_add("custom_nodes.ComfyUI-hybs-nodes.nodes.hybs_conditional_lora_loader", ["HYBS_ConditionalLoRALoader"])
        _safe_add("custom_nodes.ComfyUI-hybs-nodes.nodes.hybs_group_bypasser_nodes", [
            "HYBS_GroupBypasser_Parent",
            "HYBS_GroupBypasser_Child",
            "HYBS_GroupBypasser_Panel",
        ])

        return nodes

async def comfy_entrypoint() -> ComfyExtension:
    return HybsNodesExtension()