from amaranth.back import verilog
from pycachegen.cache_wrapper import CacheWrapper
from pycachegen.cache_config_validation import (
    CacheConfig,
    MemoryConfig,
    ReplacementPolicies,
)

cache_wrapper = CacheWrapper(
    num_ports=1,
    arbiter_policy="priority",
    byte_size=8,
    enable_reset=False,
    address_width=8,
    cache_configs=[
        CacheConfig(
            data_width=16,
            num_ways=4,
            num_sets=16,
            replacement_policy=ReplacementPolicies.FIFO,
            write_through=True,
            write_allocate=False,
            block_size=1,
        )
    ],
    memory_config=MemoryConfig(
        data_width=16, read_latency=10, write_latency=15, min_address=0, max_address=256
    ),
)

with open("cache_wrapper.v", "w") as f:
    f.write(verilog.convert(cache_wrapper, name="CacheWrapper"))
