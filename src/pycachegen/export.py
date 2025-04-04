from pathlib import Path

from amaranth.back import verilog

from .cache_config import CacheConfig, MemoryConfig, ReplacementPolicies
from .cache_wrapper import CacheWrapper

# TODO delete this file
cache_wrapper = CacheWrapper(
    num_ports=1,
    byte_size=8,
    address_width=16,
    cache_configs=[
        CacheConfig(
            data_width=32,
            num_ways=4,
            num_sets=16,
            replacement_policy=ReplacementPolicies.PLRU_MRU,
            write_through=True,
            write_allocate=False,
            block_size=4,
        )
    ],
    memory_config=MemoryConfig(
        data_width=64, read_latency=10, write_latency=15, min_address=0, max_address=512
    ),
)

Path("export").mkdir(parents=True, exist_ok=True)
with open("export/cache_wrapper.v", "w") as f:
    f.write(verilog.convert(cache_wrapper, name="CacheWrapper", emit_src=False))
