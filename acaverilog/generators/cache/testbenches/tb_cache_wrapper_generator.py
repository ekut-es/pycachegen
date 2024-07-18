import copy
import sys
from acaverilog.generators.cache.cache_config_validation import (
    CacheConfig,
    MemoryConfig,
)
from acaverilog.generators.cache.generators.cache_wrapper_generator import (
    CacheWrapperGenerator,
)

if __name__ == "__main__":
    # argv:
    # (file name), path to output directory, number for output file suffix, num ports, arbiter policy, byte size, enable reset, address_width
    # [data width, num ways, num sets, replacement policy, hit latency, miss latency, write through, write allocate, block size]...
    # [main memory data width, read latency, write latency, min address, max address]
    args = copy.copy(sys.argv[1:])  # make a copy just to be sure
    OUT_DIR = args.pop(0)
    FILE_SUFFIX = args.pop(0)
    NUM_PORTS = int(args.pop(0))
    ARBITER_POLICY = args.pop(0)
    BYTE_SIZE = int(args.pop(0))
    ENABLE_RESET = bool(int(args.pop(0)))
    ADDRESS_WIDTH = int(args.pop(0))
    raw_memory_config = args.pop().split()
    raw_cache_configs = [config.split() for config in args]

    cache_configs = []
    for config in raw_cache_configs:
        cache_configs.append(
            CacheConfig(
                data_width=int(config[0]),
                num_ways=int(config[1]),
                num_sets=int(config[2]),
                replacement_policy=config[3],
                hit_latency=int(config[4]),
                miss_latency=int(config[5]),
                write_through=bool(int(config[6])),
                write_allocate=bool(int(config[7])),
                block_size=int(config[8]),
            )
        )
    memory_config = MemoryConfig(
        data_width=int(raw_memory_config[0]),
        read_latency=int(raw_memory_config[1]),
        write_latency=int(raw_memory_config[2]),
        min_address=int(raw_memory_config[3], base=0),
        max_address=int(raw_memory_config[4], base=0),
    )

    cache_wrapper_generator = CacheWrapperGenerator(
        NUM_PORTS,
        ARBITER_POLICY,
        BYTE_SIZE,
        ENABLE_RESET,
        ADDRESS_WIDTH,
        memory_config,
        *cache_configs,
    )
    m = cache_wrapper_generator.generate_module()
    m.to_verilog(f"{OUT_DIR}/cache_wrapper_{FILE_SUFFIX}.v", for_verilator=True)
