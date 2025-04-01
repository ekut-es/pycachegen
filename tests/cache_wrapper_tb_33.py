from pycachegen import (
    CacheConfig,
    CacheWrapper,
    MemoryConfig,
    ReplacementPolicies,
    WritePolicies,
)

from .tb_utils import CacheWrapperBenchHelper, run_bench


# Testbench for testing write buffers
def test():
    dut = CacheWrapper(
        num_ports=1,
        byte_size=8,
        address_width=8,
        cache_configs=[
            CacheConfig(
                data_width=16,
                num_ways=1,
                num_sets=4,
                replacement_policy=ReplacementPolicies.PLRU_TREE,
                write_policy=WritePolicies.WRITE_THROUGH,
                write_allocate=False,
                block_size=1,
                write_buffer_size=4,
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
        # do a bunch of writes to different addresses
        await helper.write(ctx, 0, 0x1000, False)
        await helper.write(ctx, 1, 0x1010, False)
        await helper.write(ctx, 2, 0x1020, False)
        await helper.write(ctx, 3, 0x1030, False)

        # read the data that was written last
        await helper.read(ctx, 3, 0x1030, False)

        # do some more writes
        await helper.write(ctx, 1, 0x1011, False)
        await helper.write(ctx, 2, 0x1021, False)

        # read data that should already be written to main memory
        await helper.read(ctx, 0, 0x1000, False)

    run_bench(dut=dut, bench=bench)
