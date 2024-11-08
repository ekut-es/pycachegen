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


# Testbench for testing flushes in multi layer cache architectures
def test():
    dut = CacheWrapper(
        num_ports=1,
        arbiter_policy="priority",
        byte_size=8,
        enable_reset=False,
        address_width=3,
        cache_configs=[
            CacheConfig(
                data_width=8,
                num_ways=1,
                num_sets=2,
                replacement_policy=ReplacementPolicies.PLRU_TREE,
                write_through=False,
                write_allocate=True,
                block_size=1,
            ),
            CacheConfig(
                data_width=8,
                num_ways=1,
                num_sets=2,
                replacement_policy=ReplacementPolicies.PLRU_TREE,
                write_through=True,
                write_allocate=False,
                block_size=1,
            ),
            CacheConfig(
                data_width=8,
                num_ways=1,
                num_sets=2,
                replacement_policy=ReplacementPolicies.PLRU_TREE,
                write_through=False,
                write_allocate=True,
                block_size=1,
            ),
        ],
        memory_config=MemoryConfig(
            data_width=8,
            read_latency=3,
            write_latency=5,
            min_address=0,
            max_address=8,
        ),
    )

    helper = CacheWrapperBenchHelper(dut)

    async def bench(ctx):
        # write to several addresses so we have
        # dirty data in the l1 and l3 caches
        await helper.write(ctx, 0, 0x10, False)
        await helper.write(ctx, 1, 0x11, False)
        await helper.write(ctx, 2, 0x12, False)
        await helper.write(ctx, 3, 0x13, False)
        await helper.write(ctx, 4, 0x14, False)

        await helper.flush(ctx)

        # check that the data is all still there
        await helper.read(ctx, 4, 0x14, True)
        await helper.read(ctx, 3, 0x13, True)
        await helper.read(ctx, 2, 0x12, False)
        await helper.read(ctx, 1, 0x11, False)
        await helper.read(ctx, 0, 0x10, False)

    run_bench(dut=dut, bench=bench)


if __name__ == "__main__":
    test()
