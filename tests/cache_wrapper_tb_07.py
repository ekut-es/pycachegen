from pycachegen import (
    CacheConfig,
    CacheWrapper,
    ReplacementPolicies,
    WritePolicies,
)

from .tb_utils import CacheWrapperBenchHelper, run_bench


# Testbench for testing the write back, write no-allocate policy
def test():
    dut = CacheWrapper(
        num_ports=1,
        byte_size=8,
        address_width=8,
        read_delay=9,
        write_delay=14,
        cache_configs=[
            CacheConfig(
                data_width=16,
                num_ways=2,
                num_sets=2,
                replacement_policy=ReplacementPolicies.PLRU_TREE,
                write_policy=WritePolicies.WRITE_BACK,
                write_allocate=False,
                block_size=1,
            )
        ],
        main_memory_data_width=16,
    )

    helper = CacheWrapperBenchHelper(dut)

    async def bench(ctx):
        # Check that write no-allocate works
        await helper.write(ctx, 0, 0x1000, False)
        await helper.read(ctx, 0, 0x1000, False)

        # get 2 into the cache, then write to it (should be a hit)
        await helper.read(ctx, 2, 0, False)
        await helper.write(ctx, 2, 0x1020, True)

        # check that 0 is also in the cache
        await helper.read(ctx, 0, 0x1000, True)

        # replace 2 and check that write back worked
        await helper.read(ctx, 4, 0, False)
        await helper.read(ctx, 2, 0x1020, False)

    run_bench(dut=dut, bench=bench)
