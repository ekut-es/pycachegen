from pycachegen import (
    CacheConfig,
    CacheWrapper,
    MemoryConfig,
    ReplacementPolicies,
    WritePolicies,
)

from .tb_utils import CacheWrapperBenchHelper, run_bench


# Testbench for testing hit and miss latencies of 0
def test():
    latency = 0
    dut = CacheWrapper(
        num_ports=1,
        byte_size=8,
        address_width=8,
        cache_configs=[
            CacheConfig(
                data_width=16,
                num_ways=2,
                num_sets=2,
                replacement_policy=ReplacementPolicies.LRU,
                write_policy=WritePolicies.WRITE_BACK,
                write_allocate=True,
                block_size=1,
                hit_latency=latency,
                miss_latency=latency,
            ),
        ],
        memory_config=MemoryConfig(
            data_width=16,
            read_latency=5,
            write_latency=8,
            min_address=0,
            max_address=256,
        ),
    )

    helper = CacheWrapperBenchHelper(dut)

    async def bench(ctx):
        # Do some write misses
        await helper.write(ctx, 0, 0x1000, False)
        assert helper.elapsed_time == (1 + latency)
        await helper.write(ctx, 1, 0x1001, False)
        assert helper.elapsed_time == 2 * (1 + latency)
        await helper.write(ctx, 3, 0x1003, False)
        assert helper.elapsed_time == 3 * (1 + latency)

        # Do some write hits
        await helper.write(ctx, 0, 0x1100, True)
        assert helper.elapsed_time == 4 * (1 + latency)
        await helper.write(ctx, 1, 0x1101, True)
        assert helper.elapsed_time == 5 * (1 + latency)
        await helper.write(ctx, 3, 0x1103, True)
        assert helper.elapsed_time == 6 * (1 + latency)

        # Do some read hits
        await helper.read(ctx, 0, 0x1100, True)
        assert helper.elapsed_time == 7 * (1 + latency)
        await helper.read(ctx, 1, 0x1101, True)
        assert helper.elapsed_time == 8 * (1 + latency)
        await helper.read(ctx, 3, 0x1103, True)
        assert helper.elapsed_time == 9 * (1 + latency)

        # Do a read miss
        await helper.read(ctx, 2, 0, False)
        # Do a read miss with a replacement
        await helper.read(ctx, 6, 0, False)

        # Do a write with a write back
        await helper.write(ctx, 5, 0x1005, False)

        # Check whether everything still works by creating read hits
        elapsed_time = helper.elapsed_time
        await helper.read(ctx, 2, 0, True)
        assert helper.elapsed_time - elapsed_time == (1 + latency)
        await helper.read(ctx, 6, 0, True)
        assert helper.elapsed_time - elapsed_time == 2 * (1 + latency)
        await helper.read(ctx, 3, 0x1103, True)
        assert helper.elapsed_time - elapsed_time == 3 * (1 + latency)
        await helper.read(ctx, 5, 0x1005, True)
        assert helper.elapsed_time - elapsed_time == 4 * (1 + latency)

    run_bench(dut=dut, bench=bench)
