from pycachegen import CacheWrapper

from .tb_utils import CacheWrapperBenchHelper, run_bench


# Testbench for testing that the cache wrapper can generate architectures without caches
def test():
    dut = CacheWrapper(
        num_ports=1,
        byte_size=8,
        address_width=3,
        read_delay=9,
        write_delay=14,
        cache_configs=[],
        main_memory_data_width=16,
    )

    helper = CacheWrapperBenchHelper(dut)

    async def bench(ctx):
        # just do a bit of reading and writing
        await helper.read(ctx, 0, 0, False)
        await helper.read(ctx, 1, 0, False)
        await helper.read(ctx, 2, 0, False)
        await helper.read(ctx, 3, 0, False)

        await helper.write(ctx, 4, 0x1040, False)
        await helper.read(ctx, 4, 0x1040, False)
        await helper.read(ctx, 0, 0, False)

    run_bench(dut=dut, bench=bench)
