from pycachegen import (
    CacheConfig,
    CacheWrapper,
    ReplacementPolicies,
    WritePolicies,
)

from .tb_utils import CacheWrapperBenchHelper, run_bench


# Testbench for testing the LRU replacement policy.
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
                replacement_policy=ReplacementPolicies.LRU,
                write_policy=WritePolicies.WRITE_BACK,
                write_allocate=True,
                block_size=1,
            ),
        ],
        main_memory_data_width=16,
    )

    helper = CacheWrapperBenchHelper(dut)

    async def bench(ctx):
        # Fill set A
        await helper.write(ctx, 0, 0x1000, False)
        await helper.write(ctx, 2, 0x1020, False)
        await helper.write(ctx, 4, 0x1040, False)
        await helper.write(ctx, 6, 0x1060, False)

        # Fill set B
        await helper.write(ctx, 1, 0x1010, False)
        await helper.write(ctx, 3, 0x1030, False)
        await helper.write(ctx, 5, 0x1050, False)
        await helper.write(ctx, 7, 0x1070, False)

        # Test the LRU policy on set A
        await helper.read(ctx, 4, 0x1040, True)
        await helper.read(ctx, 0, 0x1000, True)
        await helper.read(ctx, 8, 0, False)
        await helper.read(ctx, 0xA, 0, False)
        await helper.read(ctx, 2, 0x1020, False)
        await helper.read(ctx, 6, 0x1060, False)
        await helper.read(ctx, 4, 0x1040, False)
        await helper.read(ctx, 0xA, 0, True)
        await helper.read(ctx, 2, 0x1020, True)
        await helper.read(ctx, 6, 0x1060, True)
        await helper.read(ctx, 4, 0x1040, True)
        await helper.read(ctx, 0, 0x1000, False)
        await helper.read(ctx, 0xA, 0, False)

        # Test set B
        await helper.read(ctx, 1, 0x1010, True)
        await helper.read(ctx, 9, 0, False)
        await helper.read(ctx, 3, 0x1030, False)
        await helper.read(ctx, 7, 0x1070, True)
        await helper.read(ctx, 5, 0x1050, False)
        await helper.read(ctx, 1, 0x1010, False)

        # Test set A again
        await helper.read(ctx, 4, 0x1040, True)
        await helper.read(ctx, 0, 0x1000, True)
        await helper.read(ctx, 6, 0x1060, True)
        await helper.read(ctx, 2, 0x1020, False)

    run_bench(dut=dut, bench=bench)
