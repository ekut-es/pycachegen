from pycachegen import (
    CacheConfig,
    CacheWrapper,
    ReplacementPolicies,
    WritePolicies,
)

from .tb_utils import CacheWrapperBenchHelper, run_bench


# Testbench for testing the plru_mru replacement policy
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
                replacement_policy=ReplacementPolicies.PLRU_MRU,
                write_policy=WritePolicies.WRITE_BACK,
                write_allocate=True,
                block_size=1,
            )
        ],
        main_memory_data_width=16,
    )

    helper = CacheWrapperBenchHelper(dut)

    async def bench(ctx):
        # write to all ways
        await helper.write(ctx, 0, 0x1000, False)
        await helper.write(ctx, 2, 0x1020, False)
        await helper.write(ctx, 4, 0x1040, False)
        await helper.write(ctx, 6, 0x1060, False)

        # access way 0
        await helper.read(ctx, 0, 0x1000, True)

        # this should replace way 1 (addr 2)
        await helper.write(ctx, 8, 0x1080, False)

        # check that addr 2 got replaced
        await helper.read(ctx, 2, 0x1020, False)

        # check that now addr 4 got replaced
        await helper.read(ctx, 4, 0x1040, False)

        # check that all the data is still there
        await helper.read(ctx, 4, 0x1040, True)
        await helper.read(ctx, 8, 0x1080, True)
        await helper.read(ctx, 2, 0x1020, True)
        await helper.read(ctx, 6, 0x1060, True)

    run_bench(dut=dut, bench=bench)
