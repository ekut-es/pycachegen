from .tb_utils import (
    CacheWrapperBenchHelper,
    run_bench,
)
from pycachegen.cache_wrapper import CacheWrapper
from pycachegen.cache_config import (
    CacheConfig,
    MemoryConfig,
    ReplacementPolicies,
)


# Testbench for testing the FIFO replacement policy
def test():
    dut = CacheWrapper(
        num_ports=1,
        byte_size=8,
        address_width=8,
        cache_configs=[
            CacheConfig(
                data_width=16,
                num_ways=4,
                num_sets=2,
                replacement_policy=ReplacementPolicies.FIFO,
                write_through=True,
                write_allocate=False,
                block_size=1,
            )
        ],
        memory_config=MemoryConfig(
            data_width=16,
            read_latency=10,
            write_latency=15,
            min_address=0,
            max_address=256,
        ),
    )

    helper = CacheWrapperBenchHelper(dut)

    async def bench(ctx):
        # Read from 0, 2, 4, 6 (all go into the same set)
        await helper.read(ctx, 0, 0, False)
        await helper.read(ctx, 0, 0, True)
        await helper.read(ctx, 2, 0, False)
        await helper.read(ctx, 2, 0, True)
        await helper.read(ctx, 4, 0, False)
        await helper.read(ctx, 4, 0, True)
        await helper.read(ctx, 6, 0, False)
        await helper.read(ctx, 6, 0, True)

        # Write some data to them
        await helper.write(ctx, 0, 0x1000, True)
        await helper.write(ctx, 2, 0x1002, True)
        await helper.write(ctx, 4, 0x1004, True)
        await helper.write(ctx, 6, 0x1006, True)

        # check that 0 is still in the cache
        await helper.read(ctx, 0, 0x1000, True)
        await helper.read(ctx, 0, 0x1000, True)

        # reading from 8 should replace 0
        await helper.read(ctx, 8, 0, False)
        await helper.read(ctx, 0, 0x1000, False)

        # reading from 0 should now replace 2, all other data should still be there
        await helper.read(ctx, 0, 0x1000, True)
        await helper.read(ctx, 8, 0, True)
        await helper.read(ctx, 4, 0x1004, True)
        await helper.read(ctx, 6, 0x1006, True)
        await helper.read(ctx, 2, 0x1002, False)

    run_bench(dut=dut, bench=bench)
