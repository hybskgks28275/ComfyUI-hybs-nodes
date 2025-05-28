import random
from typing import List

class HYBS_SeedListGenerator:

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                 # seed数
                "count": ("INT", {"default": 1, "min": 1, "max": 0xffffffffffffffff})
            }
        }
    
    RETURN_TYPES = ("LIST", "INT",)
    RETURN_NAMES = ("seed list", "count",)
    FUNCTION = "seed_list_generator"
    CATEGORY = "HYBS/SeedGenerator"

    def seed_list_generator(self, count: int) -> List[int]:
        return ([random.randint(0, 2**32 - 1) for _ in range(count)], count)

NODE_CLASS_MAPPINGS = {
    "Seed List Generator": HYBS_SeedListGenerator,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "Seed List Generator": "Seed List Generator",
}