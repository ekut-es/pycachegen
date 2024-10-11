from pycachegen.amaranth.testbenches.tb_utils import (
    CacheWrapperBenchHelper,
    run_bench,
)
from pycachegen.amaranth.cache_wrapper import CacheWrapper
from pycachegen.cache_config_validation import CacheConfig, MemoryConfig

# Testbench for testing the write back, write no-allocate policy

dut = CacheWrapper(
    num_ports=1,
    arbiter_policy="priority",
    byte_size=8,
    enable_reset=False,
    address_width=8,
    cache_configs=[
        CacheConfig(
            data_width=16,
            num_ways=2,
            num_sets=2,
            replacement_policy="plru_tree",
            hit_latency=10,
            miss_latency=15,
            write_through=False,
            write_allocate=False,
            block_size=1,
        )
    ],
    memory_config=MemoryConfig(
        data_width=16, read_latency=10, write_latency=15, min_address=0, max_address=512
    ),
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
