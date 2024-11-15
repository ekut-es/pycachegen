import sys
from pycachegen import (
    CacheWrapperGenerator,
    CacheConfig,
    MemoryConfig,
)

if __name__ == "__main__":
    FILE_NAME = "custom_cache_wrapper.v"  # path for output file (will be overridden by argv[1] if called with any arguments)
    NUM_PORTS = 1
    ARBITER_POLICY = "round_robin"  # one of "fifo", "priority", "round_robin"
    BYTE_SIZE = 8  # bits per byte
    ADDRESS_WIDTH = 15  # Addresses must include the byte offset bits
    # Put all your cache configurations here
    CACHE_CONFIGS = [
        CacheConfig(
            data_width=16,
            num_ways=2,
            num_sets=4,
            replacement_policy="plru_tree",
            hit_latency=0,
            miss_latency=0,
            write_through=False,
            write_allocate=True,
            block_size=4,
        )
    ]

    # Configure your main memory
    MEMORY_CONFIG = MemoryConfig(
        data_width=64,
        read_latency=60,
        write_latency=60,
        min_address=0,
        max_address=(2**ADDRESS_WIDTH),
    )

    ### No need to change anything below this line

    # Create the Cache Wrapper Generator
    generator = CacheWrapperGenerator(
        NUM_PORTS,
        ARBITER_POLICY,
        BYTE_SIZE,
        ENABLE_RESET,
        ADDRESS_WIDTH,
        MEMORY_CONFIG,
        *CACHE_CONFIGS,
    )

    # determine output path
    if len(sys.argv) == 2:
        path = sys.argv[1]
    else:
        path = FILE_NAME

    # Generate the verilog source code
    generator.generate_module().to_verilog(path, for_verilator=True)
