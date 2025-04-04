from pycachegen import (
    CacheConfig,
    CacheWrapper,
    ReplacementPolicies,
    WritePolicies,
)

from .tb_utils import CacheWrapperBenchHelper, run_bench


# Testbench for testing the write through, write allocate policy
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
                write_policy=WritePolicies.WRITE_THROUGH,
                write_allocate=True,
                block_size=1,
            )
        ],
        main_memory_data_width=16,
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
