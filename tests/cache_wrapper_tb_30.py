from pycachegen import CacheWrapper

from .tb_utils import CacheWrapperBenchHelper, run_bench


# Testbench for a CacheWrapper with only a main memory and no caches
def test():
    dut = CacheWrapper(
        address_width=3,
        num_ports=1,
        read_delay=1,
        write_delay=2,
        main_memory_data_width=32,
        cache_configs=[],
        create_main_memory=True,
        byte_size=8,
    )

    helper = CacheWrapperBenchHelper(dut)

    async def bench(ctx):
        await helper.write(ctx, 5, 0xA0A1A2A3, False, write_strobe=0b1101)
        await helper.read(ctx, 5, 0xA0A100A3, False)
        await helper.write(ctx, 4, 0x12345678, False)
        await helper.read(ctx, 4, 0x12345678, False)
        await helper.read(ctx, 5, 0xA0A100A3, False)

    run_bench(dut=dut, bench=bench)
