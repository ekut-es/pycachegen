from pycachegen import CacheConfig, CacheWrapper, MemoryConfig, ReplacementPolicies

from .tb_utils import CacheWrapperBenchHelper, run_bench


# Testbench for testing the plru_tree replacement policy
def test():
    dut = CacheWrapper(
        num_ports=1,
        byte_size=8,
        address_width=8,
        cache_configs=[
            CacheConfig(
                data_width=16,
                num_ways=4,
                num_sets=2,
                replacement_policy=ReplacementPolicies.PLRU_TREE,
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
