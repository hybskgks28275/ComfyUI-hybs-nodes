import random
from typing import List
from comfy_api.latest import io

class HYBS_SeedListGenerator(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="HYBS_SeedListGenerator",
            display_name="Seed List Generator",
            category="HYBS/SeedGenerator",
            inputs=[
                io.Int.Input("count", default=1, min=1, max=0xffffffffffffffff),
            ],
            outputs=[
                io.Custom("LIST").Output(display_name="seed list"),
                io.Int.Output(display_name="count"),
            ],
            description="Generate a list of random seed values."
        )

    @classmethod
    def execute(cls, count: int) -> io.NodeOutput:
        seeds: List[int] = [random.randint(0, 2**32 - 1) for _ in range(count)]
        return io.NodeOutput(seeds, count)
