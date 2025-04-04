from pycachegen import (
    CacheConfig,
    CacheWrapper,
    ReplacementPolicies,
    WritePolicies,
)

from .tb_utils import CacheWrapperBenchHelper, run_bench


# Testbench for testing the timing of some 1 cycle operations
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
        # Do some write misses
        await helper.write(ctx, 0, 0x1000, False)
        assert helper.elapsed_time == 1
        await helper.write(ctx, 1, 0x1001, False)
        assert helper.elapsed_time == 2
        await helper.write(ctx, 3, 0x1003, False)
        assert helper.elapsed_time == 3

        # Do some write hits
        await helper.write(ctx, 0, 0x1100, True)
        assert helper.elapsed_time == 4
        await helper.write(ctx, 1, 0x1101, True)
        assert helper.elapsed_time == 5
        await helper.write(ctx, 3, 0x1103, True)
        assert helper.elapsed_time == 6

        # Do some read hits
        await helper.read(ctx, 0, 0x1100, True)
        assert helper.elapsed_time == 7
        await helper.read(ctx, 1, 0x1101, True)
        assert helper.elapsed_time == 8
        await helper.read(ctx, 3, 0x1103, True)
        assert helper.elapsed_time == 9

        # Do a read miss
        await helper.read(ctx, 2, 0, False)
        # Do a read miss with a replacement
        await helper.read(ctx, 6, 0, False)

        # Do a write with a write back
        await helper.write(ctx, 5, 0x1005, False)

        # Check whether everything still works by creating read hits
        elapsed_time = helper.elapsed_time
        await helper.read(ctx, 2, 0, True)
        assert helper.elapsed_time - elapsed_time == 1
        await helper.read(ctx, 6, 0, True)
        assert helper.elapsed_time - elapsed_time == 2
        await helper.read(ctx, 3, 0x1103, True)
        assert helper.elapsed_time - elapsed_time == 3
        await helper.read(ctx, 5, 0x1005, True)
        assert helper.elapsed_time - elapsed_time == 4

    run_bench(dut=dut, bench=bench)
