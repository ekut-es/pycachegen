from .tb_utils import (
    CacheWrapperBenchHelper,
    run_bench,
)
from pycachegen.cache_wrapper import CacheWrapper
from pycachegen.cache_config_validation import CacheConfig, MemoryConfig


# Testbench for testing two layers of caches
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
                num_ways=2,
                num_sets=1,
                replacement_policy="fifo",
                hit_latency=10,
                miss_latency=15,
                write_through=False,
                write_allocate=True,
                block_size=1,
            ),
            CacheConfig(
                data_width=16,
                num_ways=2,
                num_sets=2,
                replacement_policy="fifo",
                hit_latency=10,
                miss_latency=15,
                write_through=False,
                write_allocate=True,
                block_size=1,
            ),
        ],
        memory_config=MemoryConfig(
            data_width=16,
            read_latency=10,
            write_latency=15,
            min_address=0,
            max_address=256,
        ),
    )

    helper = CacheWrapperBenchHelper(dut)

    async def bench(ctx):
        # write to both ways
        await helper.write(ctx, 0, 0x1000, False)
        await helper.write(ctx, 1, 0x1010, False)

        # check that the data is there
        await helper.read(ctx, 0, 0x1000, True)
        await helper.read(ctx, 1, 0x1010, True)

        # replace both ways
        await helper.write(ctx, 2, 0x1020, False)
        await helper.write(ctx, 3, 0x1030, False)

        # read 0 and 1 again - they should be in the L2 cache
        await helper.read(ctx, 0, 0x1000, False)
        await helper.read(ctx, 1, 0x1010, False)

        # read 4 to replace addr 0 in both the l1 and l2 caches
        await helper.read(ctx, 4, 0, False)

        # read 0 (manually check that it isn't cached anywhere)
        await helper.read(ctx, 0, 0x1000, False)

    run_bench(dut=dut, bench=bench)


if __name__ == "__main__":
    test()
