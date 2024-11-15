from .tb_utils import (
    CacheWrapperBenchHelper,
    run_bench,
)
from pycachegen.cache_wrapper import CacheWrapper
from pycachegen.cache_config_validation import (
    CacheConfig,
    MemoryConfig,
    ReplacementPolicies,
)


# Testbench for testing hit latency of 5 and miss latency of 16
def test():
    hit_latency = 5
    miss_latency = 16
    dut = CacheWrapper(
        num_ports=1,
        byte_size=8,
        enable_reset=False,
        address_width=8,
        cache_configs=[
            CacheConfig(
                data_width=16,
                num_ways=2,
                num_sets=2,
                replacement_policy=ReplacementPolicies.LRU,
                write_through=False,
                write_allocate=True,
                block_size=1,
                hit_latency=hit_latency,
                miss_latency=miss_latency,
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

    elapsed_time = 0

    def assert_elapsed_time(t):
        nonlocal elapsed_time
        assert helper.elapsed_time - elapsed_time == t
        elapsed_time = helper.elapsed_time

    async def bench(ctx):
        # Do some write misses
        await helper.write(ctx, 0, 0x1000, False)
        assert_elapsed_time(1 + miss_latency)
        await helper.write(ctx, 1, 0x1001, False)
        assert_elapsed_time(1 + miss_latency)
        await helper.write(ctx, 3, 0x1003, False)
        assert_elapsed_time(1 + miss_latency)

        # Do some write hits
        await helper.write(ctx, 0, 0x1100, True)
        assert_elapsed_time(1 + hit_latency)
        await helper.write(ctx, 1, 0x1101, True)
        assert_elapsed_time(1 + hit_latency)
        await helper.write(ctx, 3, 0x1103, True)
        assert_elapsed_time(1 + hit_latency)

        # Do some read hits
        await helper.read(ctx, 0, 0x1100, True)
        assert_elapsed_time(1 + hit_latency)
        await helper.read(ctx, 1, 0x1101, True)
        assert_elapsed_time(1 + hit_latency)
        await helper.read(ctx, 3, 0x1103, True)
        assert_elapsed_time(1 + hit_latency)

        # Do a read miss
        await helper.read(ctx, 2, 0, False)
        # Do a read miss with a replacement
        await helper.read(ctx, 6, 0, False)

        # Do a write with a write back
        await helper.write(ctx, 5, 0x1005, False)

        # Check whether everything still works by creating read hits
        nonlocal elapsed_time
        elapsed_time = helper.elapsed_time
        await helper.read(ctx, 2, 0, True)
        assert_elapsed_time(1 + hit_latency)
        await helper.read(ctx, 6, 0, True)
        assert_elapsed_time(1 + hit_latency)
        await helper.read(ctx, 3, 0x1103, True)
        assert_elapsed_time(1 + hit_latency)
        await helper.read(ctx, 5, 0x1005, True)
        assert_elapsed_time(1 + hit_latency)

    run_bench(dut=dut, bench=bench)
