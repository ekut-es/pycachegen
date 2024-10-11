from pycachegen.amaranth.testbenches.tb_utils import (
    CacheWrapperBenchHelper,
    run_bench,
)
from pycachegen.amaranth.cache_wrapper import CacheWrapper
from pycachegen.cache_config_validation import CacheConfig, MemoryConfig


# Testbench for testing the flush in a direct mapped cache
def test():
    dut = CacheWrapper(
        num_ports=1,
        arbiter_policy="priority",
        byte_size=8,
        enable_reset=False,
        address_width=8,
        cache_configs=[
            CacheConfig(
                data_width=16,
                num_ways=1,
                num_sets=4,
                replacement_policy="plru_tree",
                hit_latency=10,
                miss_latency=15,
                write_through=False,
                write_allocate=True,
                block_size=1,
            )
        ],
        memory_config=MemoryConfig(
            data_width=16,
            read_latency=10,
            write_latency=15,
            min_address=0,
            max_address=512,
        ),
    )

    helper = CacheWrapperBenchHelper(dut)

    async def bench(ctx):
        # Write some data to the cache
        await helper.write(ctx, 0, 0x1000, False)
        await helper.write(ctx, 1, 0x1010, False)
        await helper.write(ctx, 2, 0x1020, False)

        # flush it
        await helper.flush(ctx)

        # check that the data is still there
        await helper.read(ctx, 0, 0x1000, True)
        await helper.read(ctx, 1, 0x1010, True)
        await helper.read(ctx, 2, 0x1020, True)

        # manually check that this doesn't cause a write-back
        await helper.write(ctx, 4, 0x1040, False)

    run_bench(dut=dut, bench=bench)
