from amaranth.back import verilog

from pycachegen import (
    CacheConfig,
    CacheWrapper,
    MemoryConfig,
    ReplacementPolicies,
    WritePolicies,
)

cache_wrapper = CacheWrapper(
    num_ports=1,
    address_width=25,
    cache_configs=[
        CacheConfig(
            data_width=32,
            num_ways=2,
            num_sets=1,
            block_size=2,
            replacement_policy=ReplacementPolicies.PLRU_TREE,
            write_policy=WritePolicies.WRITE_BACK,
            write_allocate=True,
        ),
        CacheConfig(
            data_width=32,
            num_ways=2,
            num_sets=2,
            block_size=4,
            replacement_policy=ReplacementPolicies.FIFO,
            write_policy=WritePolicies.WRITE_BACK,
            write_allocate=True,
        ),
    ],
    memory_config=MemoryConfig(
        data_width=128,
        min_address=0,
        size=512,
    ),
)

with open("cache_wrapper.v", "w") as f:
    f.write(verilog.convert(cache_wrapper, name="CacheWrapper", emit_src=False))
