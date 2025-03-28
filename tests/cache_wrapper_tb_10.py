from pycachegen.cache_config import CacheConfig, MemoryConfig, ReplacementPolicies
from pycachegen.cache_wrapper import CacheWrapper

from .tb_utils import CacheWrapperBenchHelper, run_bench


# Testbench for testing multiple words per block
def test():
    dut = CacheWrapper(
        num_ports=1,
        byte_size=8,
        address_width=8,
        cache_configs=[
            CacheConfig(
                data_width=16,
                num_ways=2,
                num_sets=2,
                replacement_policy=ReplacementPolicies.PLRU_TREE,
                write_through=False,
                write_allocate=True,
                block_size=4,
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
        # Write block A
        await helper.write(ctx, 0, 0x1000, False)
        await helper.write(ctx, 1, 0x1010, True)
        await helper.write(ctx, 2, 0x1020, True)
        await helper.write(ctx, 3, 0x1030, True)

        # Partially read block B (same index as block A)
        await helper.read(ctx, 0xA, 0, False)
        await helper.read(ctx, 8, 0, True)

        # Write to block B
        await helper.write(ctx, 8, 0x1080, True)
        await helper.write(ctx, 9, 0x1090, True)
        await helper.write(ctx, 0xA, 0x10A0, True)
        await helper.write(ctx, 0xB, 0x10B0, True)

        # Write to block C (also same index so it replaces block A)
        await helper.write(ctx, 0x10, 0x1100, False)

        # Read block A to make sure write back worked correctly (and to write back block B)
        await helper.read(ctx, 2, 0x1020, False)

        # Read block C to check it's still there
        await helper.read(ctx, 0x11, 0, True)

    run_bench(dut=dut, bench=bench)
