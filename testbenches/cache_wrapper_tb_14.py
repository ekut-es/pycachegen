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


# Testbench for testing different data widths with a block size of 1.
def test():
    dut = CacheWrapper(
        num_ports=1,
        arbiter_policy="priority",
        byte_size=8,
        enable_reset=False,
        address_width=6,
        cache_configs=[
            CacheConfig(
                data_width=8,
                num_ways=1,
                num_sets=4,
                replacement_policy=ReplacementPolicies.PLRU_TREE,
                write_through=False,
                write_allocate=True,
                block_size=1,
            ),
            CacheConfig(
                data_width=64,
                num_ways=1,
                num_sets=2,
                replacement_policy=ReplacementPolicies.PLRU_TREE,
                write_through=False,
                write_allocate=True,
                block_size=1,
            ),
        ],
        memory_config=MemoryConfig(
            data_width=128,
            read_latency=10,
            write_latency=15,
            min_address=0,
            max_address=4,
        ),
    )

    helper = CacheWrapperBenchHelper(dut)

    async def bench(ctx):
        await helper.write(ctx, 0, 0x01, False)
        await helper.read(ctx, 0, 0x01, True)

        # this should write back the block in the L1 cache and cause L2 to do a read block operation
        await helper.write(ctx, 4, 0x04, False)

        # 0 should be in the L2 cache and 4, which gets written back,
        # should be stored within the same word as address 0 in the L2 cache
        await helper.read(ctx, 0, 0x01, False)

        # check that 4 gets retrieved correctly from the L2 cache
        await helper.read(ctx, 4, 0x04, False)

        # write some more words into the same l2 word
        await helper.write(ctx, 7, 0x07, False)
        await helper.write(ctx, 3, 0x03, False)
        await helper.read(ctx, 7, 0x07, False)

        # write to 8 and 0xC so that 8 gets written to the l2 cache (first byte of the second set)
        await helper.write(ctx, 8, 0x08, False)
        await helper.write(ctx, 0xC, 0x0C, False)

        # write to 0x20 and 0x24 so that 0x20 gets written back (to the first l2 set, causing a write back of it)
        await helper.write(ctx, 0x20, 0x20, False)
        await helper.write(ctx, 0x24, 0x24, False)

        # check that all the data can get retrieved correctly
        await helper.read(ctx, 0x24, 0x24, True)
        await helper.read(ctx, 0x20, 0x20, False)
        await helper.read(ctx, 0xC, 0x0C, False)
        await helper.read(ctx, 0x8, 0x08, False)
        await helper.read(ctx, 0x7, 0x07, True)
        await helper.read(ctx, 0x3, 0x03, False)
        await helper.read(ctx, 0x4, 0x04, False)
        await helper.read(ctx, 0x0, 0x01, False)

    run_bench(dut=dut, bench=bench)


if __name__ == "__main__":
    test()
