"""Seed list generator node."""

import random
import uuid

from ..hybs_comfy_api import io

MAX_SEED = 2**32 - 1


class HYBS_SeedListGenerator(io.ComfyNode):
    """Generate a list of random 32-bit seeds."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="HYBS_SeedListGenerator",
            display_name="Seed List Generator",
            category="HYBS/SeedGenerator",
            search_aliases=["seed", "random seed list", "batch seeds"],
            essentials_category="Utilities/Seed",
            inputs=[
                io.Int.Input("count", default=1, min=1, max=MAX_SEED + 1),
            ],
            outputs=[
                io.Custom("LIST").Output(display_name="seed list"),
                io.Int.Output(display_name="count"),
            ],
            description="Generate a list of random seed values."
        )

    @classmethod
    def execute(cls, count: int) -> io.NodeOutput:
        count = int(count)
        seeds = random.sample(range(MAX_SEED + 1), count)
        return io.NodeOutput(seeds, count)

    @classmethod
    def fingerprint_inputs(cls, **kwargs) -> str:
        return uuid.uuid4().hex
