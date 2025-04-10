from pycachegen import (
    CacheConfig,
    CacheWrapper,
    ReplacementPolicies,
    WritePolicies,
)

from .tb_utils import CacheWrapperBenchHelper, run_bench


# Testbench for testing a flush with a block size > 1
def test():
    dut = CacheWrapper(
        num_ports=1,
        byte_size=8,
        address_width=8,
        read_delay=4,
        write_delay=7,
        cache_configs=[
            CacheConfig(
                data_width=16,
                num_ways=2,
                num_sets=1,
                replacement_policy=ReplacementPolicies.LRU,
                write_policy=WritePolicies.WRITE_BACK,
                write_allocate=True,
                block_size=4,
            ),
        ],
        main_memory_data_width=32,
    )

    helper = CacheWrapperBenchHelper(dut)

    async def bench(ctx):
        # write to both blocks
        await helper.write(ctx, 0, 0x1000, False)
        await helper.write(ctx, 3, 0x1003, True)
        await helper.write(ctx, 5, 0x1005, False)

        # flush
        await helper.flush(ctx)

        # read miss to replace the first block, then read both blocks
        await helper.read(ctx, 8, 0, False)
        await helper.read(ctx, 0, 0x1000, False)
        await helper.read(ctx, 3, 0x1003, True)
        await helper.read(ctx, 5, 0x1005, False)

    run_bench(dut=dut, bench=bench)
