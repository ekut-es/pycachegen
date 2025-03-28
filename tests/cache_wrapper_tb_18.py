from pycachegen.cache_config import MemoryConfig
from pycachegen.cache_wrapper import CacheWrapper

from .tb_utils import CacheWrapperBenchHelper, run_bench


# Testbench for testing that the cache wrapper can generate architectures without caches
def test():
    dut = CacheWrapper(
        num_ports=1,
        byte_size=8,
        address_width=3,
        cache_configs=[],
        memory_config=MemoryConfig(
            data_width=16,
            read_latency=10,
            write_latency=15,
            min_address=0,
            max_address=8,
        ),
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
