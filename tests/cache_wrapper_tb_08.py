from pycachegen import (
    CacheConfig,
    CacheWrapper,
    ReplacementPolicies,
    WritePolicies,
)

from .tb_utils import CacheWrapperBenchHelper, run_bench


# Testbench for testing the flush in a set-assocative cache
def test():
    dut = CacheWrapper(
        num_ports=1,
        byte_size=8,
        address_width=8,
        read_delay=9,
        write_delay=14,
        cache_configs=[
            CacheConfig(
                data_width=16,
                num_ways=2,
                num_sets=2,
                replacement_policy=ReplacementPolicies.PLRU_TREE,
                write_policy=WritePolicies.WRITE_BACK,
                write_allocate=True,
                block_size=1,
            )
        ],
        main_memory_data_width=16,
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
