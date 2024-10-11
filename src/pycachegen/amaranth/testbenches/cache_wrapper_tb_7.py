from pycachegen.amaranth.testbenches.tb_utils import (
    CacheWrapperBenchHelper,
    run_bench,
)
from pycachegen.amaranth.cache_wrapper import CacheWrapper
from pycachegen.cache_config_validation import CacheConfig, MemoryConfig

# Testbench for testing the write through, write allocate policy

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
            write_through=True,
            write_allocate=True,
            block_size=1,
        )
    ],
    memory_config=MemoryConfig(
        data_width=16, read_latency=10, write_latency=15, min_address=0, max_address=512
    ),
)

helper = CacheWrapperBenchHelper(dut)


async def bench(ctx):
    # Check that write allocate works
    await helper.write(ctx, 0, 0x1000, False)
    await helper.read(ctx, 0, 0x1000, True)

    # Write to 2
    await helper.write(ctx, 2, 0x1020, False)
    await helper.write(ctx, 2, 0x1020, True)
    await helper.write(ctx, 2, 0x1021, True)

    # Replace 2 and check that reading from it still works
    await helper.read(ctx, 0, 0x1000, True)
    await helper.read(ctx, 4, 0, False)
    await helper.read(ctx, 2, 0x1021, False)


run_bench(dut=dut, bench=bench)
