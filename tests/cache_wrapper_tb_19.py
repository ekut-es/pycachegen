from pycachegen import (
    CacheConfig,
    CacheWrapper,
    ReplacementPolicies,
    WritePolicies,
)

from .tb_utils import CacheWrapperBenchHelper, run_bench


# Testbench for testing that byte sizes other than 8 work.
def test():
    dut = CacheWrapper(
        num_ports=1,
        byte_size=13,
        address_width=4,
        read_delay=9,
        write_delay=14,
        cache_configs=[
            CacheConfig(
                data_width=13,
                num_ways=2,
                num_sets=2,
                replacement_policy=ReplacementPolicies.PLRU_TREE,
                write_policy=WritePolicies.WRITE_BACK,
                write_allocate=True,
                block_size=2,
            ),
        ],
        main_memory_data_width=26,
    )

    helper = CacheWrapperBenchHelper(dut)

    async def bench(ctx):
        # reading 0 will also read 1 into the block
        await helper.write(ctx, 0, 0x100, False)
        await helper.write(ctx, 1, 0x101, True)
        await helper.read(ctx, 0, 0x100, True)

        # reading 2 will also load 3 into the block
        await helper.read(ctx, 2, 0x000, False)
        await helper.read(ctx, 3, 0x000, True)

        # write to 3
        await helper.write(ctx, 3, 0x103, True)

        # write to 4, 8 to replace 0 and 1
        await helper.write(ctx, 4, 0x104, False)
        await helper.write(ctx, 8, 0x108, False)

        # read 0 and 1
        await helper.read(ctx, 0, 0x100, False)
        await helper.read(ctx, 1, 0x101, True)

    run_bench(dut=dut, bench=bench)
