import sys
from acaverilog.generators.cache.generators.cache_wrapper_generator import (
    CacheWrapperGenerator,
)
from acaverilog.generators.cache.cache_config_validation import (
    CacheConfig,
    MemoryConfig,
)

if __name__ == "__main__":
    # Put all your cache configurations here
    cache_configs = [
        CacheConfig(
            data_width=16,
            address_width=15,
            num_ways=2,
            num_sets=4,
            replacement_policy="plru_tree",
            hit_latency=0,
            miss_latency=0,
            write_through=False,
            write_allocate=True,
            block_size=4,
            be_data_width=64,
            be_address_width=13,
            byte_size=8,
            prefix="l1_",
            enable_reset=False,
        )
    ]

    # Configure your main memory
    memory_config = MemoryConfig(
        data_width=64,
        address_width=13,
        read_latency=30,
        write_latency=45,
        byte_size=8,
        min_address=0,
        max_address=(2**13 - 1),
        enable_reset=False,
    )

    # Create the Cache Wrapper Generator
    generator = CacheWrapperGenerator(
        1,
        "round_robin",
        False,
        memory_config,
        *cache_configs,
    )

    # determine output path
    if len(sys.argv) == 2:
        path = sys.argv[1]
    else:
        path = "custom_cache_wrapper.v"

    # Generate the verilog source code
    generator.generate_module().to_verilog(path, for_verilator=True)
