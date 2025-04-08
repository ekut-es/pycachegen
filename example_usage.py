from amaranth.back import verilog

from pycachegen import (
    ArbitrationScheme,
    CacheConfig,
    CacheWrapper,
    ReplacementPolicies,
    WritePolicies,
)

cache_wrapper = CacheWrapper(
    address_width=8,
    cache_configs=[
        CacheConfig(
            data_width=16,
            num_ways=1,
            num_sets=4,
            replacement_policy=ReplacementPolicies.FIFO,
            write_policy=WritePolicies.WRITE_THROUGH,
            write_allocate=False,
            block_size=1,
        )
    ],
    main_memory_data_width=16,
    create_main_memory=True,
    num_ports=1,
    read_delay=9,
    write_delay=14,
    arbitration_scheme=ArbitrationScheme.PRIORITY,
    byte_size=8,
)

with open("cache_wrapper.v", "w") as f:
    f.write(verilog.convert(cache_wrapper, name="CacheWrapper", emit_src=False))
