from pycachegen.cache_config import CacheConfig, MemoryConfig, ReplacementPolicies
from pycachegen.cache_wrapper import CacheWrapper

from .tb_utils import CacheWrapperBenchHelper, run_bench


# Testbench for testing fully associative caches
def test():
    dut = CacheWrapper(
        num_ports=1,
        byte_size=8,
        address_width=8,
        cache_configs=[
            CacheConfig(
                data_width=16,
                num_ways=4,
                num_sets=1,
                replacement_policy=ReplacementPolicies.PLRU_TREE,
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
            max_address=256,
        ),
    )

    helper = CacheWrapperBenchHelper(dut)

    async def bench(ctx):
        # write to all ways
        await helper.write(ctx, 0, 0x1000, False)
        await helper.write(ctx, 1, 0x1010, False)
        await helper.write(ctx, 2, 0x1020, False)
        await helper.write(ctx, 3, 0x1030, False)

        # check that all the data is still there
        await helper.read(ctx, 0, 0x1000, True)
        await helper.read(ctx, 1, 0x1010, True)
        await helper.read(ctx, 2, 0x1020, True)
        await helper.read(ctx, 3, 0x1030, True)

        # Replace 0
        await helper.write(ctx, 4, 0x1040, False)

        # Read from 0 again
        await helper.read(ctx, 0, 0x1000, False)

    run_bench(dut=dut, bench=bench)
