from pycachegen import CacheWrapper, DelayConfig

from .tb_utils import CacheWrapperBenchHelper, run_bench


# Testbench for delay unit burst mode
def test():
    dut = CacheWrapper(
        num_ports=1,
        byte_size=4,
        address_width=8,
        delay_config=DelayConfig(
            read_delay=9,
            write_delay=14,
            burst_block_size=4,
            burst_read_delay=3,
            burst_write_delay=5,
        ),
        cache_configs=[],
        main_memory_data_width=16,
    )

    helper = CacheWrapperBenchHelper(dut)

    async def bench(ctx):
        # burst a full block. first read should be slow, the other fast
        await helper.read(ctx, 2, 0x0000, False)
        await helper.read(ctx, 3, 0x0000, False)
        await helper.read(ctx, 0, 0x0000, False)
        await helper.read(ctx, 1, 0x0000, False)

        # burst two words, then skip one word which should not continue the burst
        await helper.read(ctx, 0, 0x0000, False)
        await helper.read(ctx, 1, 0x0000, False)
        await helper.read(ctx, 3, 0x0000, False)

        # go to another block now
        await helper.read(ctx, 4, 0x0000, False)
        await helper.read(ctx, 5, 0x0000, False)

        # dont finish the burst and start a new one on another block
        await helper.read(ctx, 9, 0x0000, False)
        await helper.read(ctx, 10, 0x0000, False)

    run_bench(dut=dut, bench=bench)
