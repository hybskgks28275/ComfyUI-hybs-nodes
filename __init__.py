from comfy_api.latest import ComfyExtension, io

# v3 nodes
from .nodes.hybs_resolution_selector import HYBS_ResolutionSelector
from .nodes.hybs_random_resolution_selector import HYBS_RandomResolutionSelector
from .nodes.hybs_seed_list_generator import HYBS_SeedListGenerator
from .nodes.hybs_conditional_lora_loader import HYBS_ConditionalLoRALoader

class HybsNodesExtension(ComfyExtension):
    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [
            HYBS_ResolutionSelector,
            HYBS_RandomResolutionSelector,      # ★ 追加
            HYBS_SeedListGenerator,
            HYBS_ConditionalLoRALoader,
        ]

async def comfy_entrypoint() -> ComfyExtension:
    return HybsNodesExtension()