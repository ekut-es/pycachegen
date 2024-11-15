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


# Testbench for testing weird data and address widths (8/16)
def test():
    dut = CacheWrapper(
        num_ports=1,
        byte_size=8,
        address_width=16,
        cache_configs=[
            CacheConfig(
                data_width=8,
                num_ways=2,
                num_sets=4,
                replacement_policy=ReplacementPolicies.PLRU_TREE,
                write_through=False,
                write_allocate=True,
                block_size=1,
            ),
        ],
        memory_config=MemoryConfig(
            data_width=8,
            read_latency=10,
            write_latency=15,
            min_address=0,
            max_address=0x10000,
        ),
    )

    helper = CacheWrapperBenchHelper(dut)

    async def bench(ctx):
        # initialize some values
        await helper.write(ctx, 0, 0x10, False)
        await helper.write(ctx, 1, 0x11, False)
        await helper.write(ctx, 2, 0x12, False)
        await helper.write(ctx, 3, 0x13, False)
        await helper.write(ctx, 4, 0x14, False)
        await helper.write(ctx, 5, 0x15, False)
        await helper.write(ctx, 6, 0x16, False)
        await helper.write(ctx, 7, 0x17, False)

        # read all values
        await helper.read(ctx, 0, 0x10, True)
        await helper.read(ctx, 1, 0x11, True)
        await helper.read(ctx, 2, 0x12, True)
        await helper.read(ctx, 3, 0x13, True)
        await helper.read(ctx, 4, 0x14, True)
        await helper.read(ctx, 5, 0x15, True)
        await helper.read(ctx, 6, 0x16, True)
        await helper.read(ctx, 7, 0x17, True)

        # write to 8 to cause a write back of 0
        await helper.write(ctx, 8, 0x18, False)

        # read from 0 to see that it is no longer in the cache
        await helper.read(ctx, 0, 0x10, False)
        # check that 8 and 0 are now both in the cache
        await helper.read(ctx, 8, 0x18, True)
        await helper.read(ctx, 0, 0x10, True)

    run_bench(dut=dut, bench=bench)
