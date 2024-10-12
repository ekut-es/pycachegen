from pycachegen.amaranth.testbenches.tb_utils import (
    CacheWrapperBenchHelper,
    run_bench,
)
from pycachegen.amaranth.cache_wrapper import CacheWrapper
from pycachegen.cache_config_validation import CacheConfig, MemoryConfig


# Testbench for testing the write back, write allocate policy
def test():
    dut = CacheWrapper(
        num_ports=1,
        arbiter_policy="priority",
        byte_size=8,
        enable_reset=False,
        address_width=8,
        cache_configs=[
            CacheConfig(
                data_width=16,
                num_ways=4,
                num_sets=2,
                replacement_policy="plru_tree",
                hit_latency=10,
                miss_latency=15,
                write_through=False,
                write_allocate=True,
                block_size=1,
            )
        ],
        memory_config=MemoryConfig(
            data_width=16,
            read_latency=10,
            write_latency=15,
            min_address=0,
            max_address=512,
        ),
    )

    helper = CacheWrapperBenchHelper(dut)

    async def bench(ctx):
        # Check that write allocate works
        await helper.write(ctx, 0, 0x1000, False)
        await helper.read(ctx, 0, 0x1000, True)

        # Fill the block so that 0 gets replaced
        await helper.write(ctx, 2, 0x1020, False)
        await helper.write(ctx, 4, 0x1040, False)
        await helper.write(ctx, 6, 0x1060, False)
        await helper.write(ctx, 8, 0x1080, False)

        # Check that 0 got written back
        await helper.read(ctx, 0, 0x1000, False)

        # Randomly write to 8
        await helper.write(ctx, 8, 0x1081, True)

        # Check that 2 got replaced and that writing to it still works
        await helper.write(ctx, 2, 0x1021, False)
        await helper.read(ctx, 2, 0x1021, True)

    run_bench(dut=dut, bench=bench)
