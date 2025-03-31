from pycachegen.cache_config import (
    CacheConfig,
    MemoryConfig,
    ReplacementPolicies,
    WritePolicies,
)
from pycachegen.cache_wrapper import CacheWrapper

if __name__ == "__main__":
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
                write_policy=WritePolicies.WRITE_THROUGH,
                write_allocate=False,
                block_size=4,
            )
        ],
        memory_config=MemoryConfig(
            data_width=64,
            read_latency=10,
            write_latency=15,
            min_address=0,
            max_address=512,
        ),
    )
