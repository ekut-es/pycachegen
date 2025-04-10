from pycachegen import (
    CacheConfig,
    CacheWrapper,
    ReplacementPolicies,
    WritePolicies,
)

from .tb_utils import CacheWrapperBenchHelper, run_bench


# Testbench for testing the plru_tree replacement policy
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
                num_ways=4,
                num_sets=2,
                replacement_policy=ReplacementPolicies.PLRU_TREE,
                write_policy=WritePolicies.WRITE_THROUGH,
                write_allocate=False,
                block_size=1,
            )
        ],
        main_memory_data_width=16,
    )

    helper = CacheWrapperBenchHelper(dut)

    async def bench(ctx):
        # Read from 0, 2, 4, 6 (all go into the same set)
        await helper.read(ctx, 0, 0, False)
        await helper.read(ctx, 2, 0, False)
        await helper.read(ctx, 0, 0, True)
        await helper.read(ctx, 4, 0, False)
        await helper.read(ctx, 6, 0, False)
        await helper.read(ctx, 4, 0, True)
        await helper.read(ctx, 8, 0, False)
        await helper.read(ctx, 4, 0, True)
        await helper.read(ctx, 2, 0, True)
        await helper.read(ctx, 8, 0, True)
        await helper.read(ctx, 0, 0, False)
        await helper.read(ctx, 2, 0, True)
        await helper.read(ctx, 4, 0, False)

    run_bench(dut=dut, bench=bench)
