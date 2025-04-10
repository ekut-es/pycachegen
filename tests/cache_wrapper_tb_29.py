from pycachegen import (
    CacheConfig,
    CacheWrapper,
    ReplacementPolicies,
    WritePolicies,
)

from .tb_utils import CacheWrapperBenchHelper, run_bench


# Testbench for testing write buffers
def test():
    dut = CacheWrapper(
        num_ports=1,
        byte_size=4,
        address_width=8,
        read_delay=9,
        write_delay=14,
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
        main_memory_data_width=16,
    )

    helper = CacheWrapperBenchHelper(dut)

    async def bench(ctx):
        # do a bunch of writes to different addresses
        await helper.write(ctx, 0, 0x1000, False)
        await helper.write(ctx, 1, 0x1010, False)
        await helper.write(ctx, 2, 0x1020, False)
        await helper.write(ctx, 3, 0x1030, False)
        await helper.write(ctx, 4, 0x1040, False)
        await helper.write(ctx, 5, 0x1050, False)
        await helper.write(ctx, 6, 0x1060, False)
        await helper.write(ctx, 7, 0x1070, False)

        # read the data that was written last
        await helper.read(ctx, 7, 0x1070, False)

        # read the data that was never written to
        await helper.read(ctx, 8, 0, False)

        # do some more writes
        await helper.write(ctx, 1, 0x1011, False)
        await helper.write(ctx, 2, 0x1021, False)

        # read data that should already be written to main memory
        await helper.read(ctx, 0, 0x1000, False)

        # write to the same address repeatedly
        await helper.write(ctx, 6, 0x1061, False)
        await helper.write(ctx, 6, 0x1062, False)
        await helper.write(ctx, 6, 0x1063, False)
        await helper.write(ctx, 6, 0x1064, False)
        await helper.write(ctx, 6, 0x1065, False)

        # read from that address again
        await helper.read(ctx, 6, 0x1065, False)

        # do some byte writes
        await helper.write(ctx, 4, 0x0A00, False, 0b0100)
        await helper.write(ctx, 4, 0x000A, False, 0b0001)

        # read from that address again
        await helper.read(ctx, 4, 0x1A4A, False)

        # The buffer is now empty again, because the last read had to wait
        # do some writes to the same address to check that write merging doesn't
        # happen to the data at the read_ptr if that data is also being sent to the main memory
        await helper.write(ctx, 3, 0x0B00, False, 0b0100)
        await helper.write(ctx, 3, 0x000B, False, 0b0001)

        # read from that address again
        await helper.read(ctx, 3, 0x1B3B, False)

        # The buffer is now empty again
        # Write and read immediately afterward
        await helper.write(ctx, 9, 0x1090, False)
        await helper.read(ctx, 9, 0x1090, False)

    run_bench(dut=dut, bench=bench)
