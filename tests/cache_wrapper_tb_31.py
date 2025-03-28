from .tb_utils import (
    CacheWrapperBenchHelper,
    run_bench,
)
from pycachegen.cache_wrapper import CacheWrapper
from pycachegen.cache_config_validation import (
    CacheConfig,
    MemoryConfig,
    ReplacementPolicies,
)
from pycachegen.arbiter import ArbitrationScheme


# Testbench for testing a write back cache with block size > 1
# and BE data width > block size
def test():
    dut = CacheWrapper(
        num_ports=1,
        byte_size=8,
        address_width=8,
        cache_configs=[
            CacheConfig(
                data_width=16,
                num_ways=2,
                num_sets=1,
                replacement_policy=ReplacementPolicies.LRU,
                write_through=False,
                write_allocate=True,
                block_size=2,
            ),
        ],
        memory_config=MemoryConfig(
            data_width=64,
            read_latency=5,
            write_latency=8,
            min_address=0,
            max_address=64,
        ),
    )

    helper = CacheWrapperBenchHelper(dut)

    async def bench(ctx):
        await helper.write(ctx, 0, 0x1000, False)
        await helper.write(ctx, 1, 0x1001, True)
        await helper.write(ctx, 3, 0x1003, False)

        # This write should now cause a write back of 0 and 1
        await helper.write(ctx, 4, 0x1004, False)

        # Read from 0 and 1 to check that the write back worked
        # and to write back 2 and 3
        await helper.read(ctx, 1, 0x1001, False)
        await helper.read(ctx, 0, 0x1000, True)

        # Read from 2 and 3 to check that the write back worked
        # and to write back 4 and 5
        await helper.read(ctx, 3, 0x1003, False)
        await helper.read(ctx, 2, 0, True)

        # read from 4 and 5 to check that the write back worked
        await helper.read(ctx, 4, 0x1004, False)
        await helper.read(ctx, 5, 0, True)

    run_bench(dut=dut, bench=bench)
