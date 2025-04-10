from pycachegen import (
    CacheConfig,
    CacheWrapper,
    ReplacementPolicies,
    WritePolicies,
)

from .tb_utils import CacheWrapperBenchHelper, run_bench


# Testbench for testing a set associative cache
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
        # read from 0 and 4 -> they should both be able to stay in the cache at the same time
        await helper.read(ctx, 0, 0, False)
        await helper.read(ctx, 0, 0, True)
        await helper.read(ctx, 4, 0, False)
        await helper.read(ctx, 4, 0, True)
        await helper.read(ctx, 0, 0, True)

        # read from 1 and 2
        await helper.read(ctx, 1, 0, False)
        await helper.read(ctx, 2, 0, False)

        # writing to 0 and 4 should still generate hits
        await helper.write(ctx, 0, 0x111, True)
        await helper.write(ctx, 4, 0x222, True)

        # writing to 8 should not replace a block (write no-allocate)
        await helper.write(ctx, 8, 0x333, False)
        await helper.read(ctx, 0, 0x111, True)
        await helper.read(ctx, 4, 0x222, True)
        await helper.read(ctx, 0, 0x111, True)

        # reading from 8 should replace 0 (fifo replacement policy)
        await helper.read(ctx, 8, 0x333, False)
        await helper.read(ctx, 8, 0x333, True)
        await helper.read(ctx, 4, 0x222, True)
        await helper.read(ctx, 0, 0x111, False)

        # 1 and 2 should still be in the cache since they have different address indicies
        await helper.read(ctx, 1, 0, True)
        await helper.read(ctx, 2, 0, True)

    run_bench(dut=dut, bench=bench)
