from pycachegen.amaranth.testbenches.tb_utils import (
    CacheWrapperBenchHelper,
    run_bench,
)
from pycachegen.amaranth.cache_wrapper import CacheWrapper
from pycachegen.cache_config_validation import CacheConfig, MemoryConfig

# Testbench for testing the FIFO replacement policy

dut = CacheWrapper(
    num_ports=1,
    arbiter_policy="priority",
    byte_size=8,
    enable_reset=False,
    address_width=8,
    cache_configs=[
        CacheConfig(
            data_width=16,
            num_ways=4,
            num_sets=2,
            replacement_policy="plru_tree",
            hit_latency=10,
            miss_latency=15,
            write_through=True,
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
