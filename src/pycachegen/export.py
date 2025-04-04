from pathlib import Path

from amaranth.back import verilog

from .cache_config import CacheConfig, ReplacementPolicies
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
    main_memory_data_width=64,
    read_delay=9,
    write_delay=14,
)

Path("export").mkdir(parents=True, exist_ok=True)
with open("export/cache_wrapper.v", "w") as f:
    f.write(verilog.convert(cache_wrapper, name="CacheWrapper", emit_src=False))
