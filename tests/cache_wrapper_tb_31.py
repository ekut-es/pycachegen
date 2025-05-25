from pycachegen import (
    CacheWrapper,
)

from .tb_utils import CacheWrapperBenchHelper, run_bench


# Testbench for delay unit burst mode
def test():
    dut = CacheWrapper(
        num_ports=1,
        byte_size=4,
        address_width=8,
        read_delay=9,
        write_delay=14,
        burst_block_size=4,
        burst_read_delay=3,
        burst_write_delay=5,
        cache_configs=[],
        main_memory_data_width=16,
    )

    helper = CacheWrapperBenchHelper(dut)

    async def bench(ctx):
        # do a bunch of reads and writes within the same block. First read should be slow, after that it shoud be fast
        await helper.read(ctx, 6, 0x0000, False)
        await helper.read(ctx, 5, 0x0000, False)
        await helper.write(ctx, 6, 0x1060, False)
        await helper.write(ctx, 7, 0x1070, False)
        await helper.read(ctx, 7, 0x1070, False)
        await helper.read(ctx, 4, 0x0000, False)
        await helper.write(ctx, 4, 0x1040, False)
        await helper.read(ctx, 6, 0x1060, False)
        await helper.write(ctx, 5, 0x1050, False)

        # read/write from addresses outside that block
        await helper.write(ctx, 0, 0x1000, False)
        await helper.read(ctx, 1, 0x0000, False)
        await helper.read(ctx, 0, 0x1000, False)

        # read from the first block again
        await helper.read(ctx, 4, 0x1040, False)
        await helper.read(ctx, 5, 0x1050, False)
        await helper.read(ctx, 6, 0x1060, False)
        await helper.read(ctx, 7, 0x1070, False)

        # read the next address after that block
        await helper.read(ctx, 8, 0x0000, False)

    run_bench(dut=dut, bench=bench)
