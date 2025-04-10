from amaranth.back import verilog

from pycachegen import *

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
            write_buffer_size=4,
        ),
        CacheConfig(
            data_width=32,
            num_ways=2,
            num_sets=2,
            block_size=4,
            replacement_policy=ReplacementPolicies.FIFO,
            write_policy=WritePolicies.WRITE_BACK,
            write_allocate=True,
            write_buffer_size=8,
        ),
    ],
    main_memory_data_width=128,
    create_main_memory=False,
)

with open("cache_wrapper.v", "w") as f:
    f.write(verilog.convert(cache_wrapper, name="CacheWrapper"))
