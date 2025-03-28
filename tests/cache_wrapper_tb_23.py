from .tb_utils import (
    CacheWrapperBenchHelper,
    run_bench,
)
from pycachegen.cache_wrapper import CacheWrapper
from pycachegen.cache_config import (
    CacheConfig,
    MemoryConfig,
    ReplacementPolicies,
)


# Testbench for testing big block sizes
def test():
    dut = CacheWrapper(
        num_ports=1,
        byte_size=8,
        address_width=8,
        cache_configs=[
            CacheConfig(
                data_width=16,
                num_ways=1,
                num_sets=1,
                replacement_policy=ReplacementPolicies.LRU,
                write_through=False,
                write_allocate=True,
                block_size=16,
            ),
        ],
        memory_config=MemoryConfig(
            data_width=64,
            read_latency=5,
            write_latency=8,
            min_address=0,
            max_address=64,
        ),
    )

    helper = CacheWrapperBenchHelper(dut)

    async def bench(ctx):
        # Write to some words
        await helper.write(ctx, 7, 0x1070, False)
        await helper.write(ctx, 1, 0x1010, True)
        await helper.write(ctx, 0xF, 0x10F0, True)

        # Write to 0x17 to cause a write back
        await helper.write(ctx, 0x17, 0x1170, False)
        await helper.read(ctx, 0x17, 0x1170, True)
        await helper.read(ctx, 0x10, 0, True)
        await helper.read(ctx, 0x1F, 0, True)

        # check that everything got written back correctly
        await helper.read(ctx, 0xF, 0x10F0, False)
        await helper.read(ctx, 0x1, 0x1010, True)
        await helper.read(ctx, 0x7, 0x1070, True)

        # check that 0x17 also got writte back correctly
        await helper.read(ctx, 0x17, 0x1170, False)
        await helper.read(ctx, 0x17, 0x1170, True)

    run_bench(dut=dut, bench=bench)
