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


# Testbench for testing a direct mapped cache
def test():
    dut = CacheWrapper(
        num_ports=1,
        byte_size=8,
        enable_reset=False,
        address_width=8,
        cache_configs=[
            CacheConfig(
                data_width=16,
                num_ways=1,
                num_sets=4,
                replacement_policy=ReplacementPolicies.FIFO,
                write_through=True,
                write_allocate=False,
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
        await helper.read(ctx, 0, 0, False)
        await helper.read(ctx, 1, 0, False)
        await helper.read(ctx, 2, 0, False)
        await helper.read(ctx, 3, 0, False)

        await helper.read(ctx, 0, 0, True)
        await helper.read(ctx, 1, 0, True)
        await helper.read(ctx, 2, 0, True)
        await helper.read(ctx, 3, 0, True)

        await helper.write(ctx, 4, 333, False)
        await helper.read(ctx, 0, 0, True)
        await helper.read(ctx, 4, 333, False)
        await helper.read(ctx, 4, 333, True)
        await helper.read(ctx, 0, 0, False)
        await helper.read(ctx, 0, 0, True)

    run_bench(dut=dut, bench=bench)
