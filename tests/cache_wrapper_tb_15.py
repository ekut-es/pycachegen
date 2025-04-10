from pycachegen import (
    CacheConfig,
    CacheWrapper,
    ReplacementPolicies,
    WritePolicies,
)

from .tb_utils import CacheWrapperBenchHelper, run_bench


# Testbench for testing that multiple words will be taken from the BE read data
# without sending a new memory request for each word. One BE word spans two blocks.
def test():
    dut = CacheWrapper(
        num_ports=1,
        byte_size=8,
        address_width=6,
        read_delay=9,
        write_delay=14,
        cache_configs=[
            CacheConfig(
                data_width=8,
                num_ways=1,
                num_sets=2,
                replacement_policy=ReplacementPolicies.PLRU_TREE,
                write_policy=WritePolicies.WRITE_THROUGH,
                write_allocate=False,
                block_size=4,
            ),
        ],
        main_memory_data_width=64,
    )

    helper = CacheWrapperBenchHelper(dut)

    async def bench(ctx):
        # initialize some values
        await helper.write(ctx, 0, 0x10, False)
        await helper.write(ctx, 1, 0x11, False)
        await helper.write(ctx, 2, 0x12, False)
        await helper.write(ctx, 3, 0x13, False)
        await helper.write(ctx, 4, 0x14, False)
        await helper.write(ctx, 5, 0x15, False)
        await helper.write(ctx, 6, 0x16, False)
        await helper.write(ctx, 7, 0x17, False)

        # read both sets but don't start with the first word
        await helper.read(ctx, 2, 0x12, False)
        await helper.read(ctx, 0, 0x10, True)
        await helper.read(ctx, 1, 0x11, True)
        await helper.read(ctx, 3, 0x13, True)

        await helper.read(ctx, 7, 0x17, False)
        await helper.read(ctx, 4, 0x14, True)
        await helper.read(ctx, 5, 0x15, True)
        await helper.read(ctx, 6, 0x16, True)

    run_bench(dut=dut, bench=bench)
