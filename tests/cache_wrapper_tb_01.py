from pycachegen import (
    CacheConfig,
    CacheWrapper,
    ReplacementPolicies,
    WritePolicies,
)

from .tb_utils import CacheWrapperBenchHelper, run_bench


# Testbench for testing a direct mapped cache
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
                num_ways=1,
                num_sets=4,
                replacement_policy=ReplacementPolicies.FIFO,
                write_policy=WritePolicies.WRITE_THROUGH,
                write_allocate=False,
                block_size=1,
            )
        ],
        main_memory_data_width=16,
    )

    helper = CacheWrapperBenchHelper(dut)

    async def bench(ctx):
        await helper.read(ctx, 0, 0, False)
        await helper.read(ctx, 1, 0, False)
        await helper.read(ctx, 2, 0, False)
        await helper.read(ctx, 3, 0, False)

        await helper.read(ctx, 0, 0, True)
        await helper.read(ctx, 1, 0, True)
        await helper.read(ctx, 2, 0, True)
        await helper.read(ctx, 3, 0, True)

        await helper.write(ctx, 4, 333, False)
        await helper.read(ctx, 0, 0, True)
        await helper.read(ctx, 4, 333, False)
        await helper.read(ctx, 4, 333, True)
        await helper.read(ctx, 0, 0, False)
        await helper.read(ctx, 0, 0, True)

    run_bench(dut=dut, bench=bench)
