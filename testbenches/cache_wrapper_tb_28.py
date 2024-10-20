from .tb_utils import (
    CacheWrapperBenchHelper,
    run_bench,
)
from pycachegen.cache_wrapper import CacheWrapper
from pycachegen.cache_config_validation import CacheConfig, MemoryConfig


# Testbench for testing memory address ranges
def test():
    dut = CacheWrapper(
        num_ports=1,
        arbiter_policy="priority",
        byte_size=8,
        enable_reset=False,
        address_width=8,
        cache_configs=[],
        memory_config=MemoryConfig(
            data_width=16,
            read_latency=10,
            write_latency=15,
            min_address=42,
            max_address=49,
        ),
    )

    helper = CacheWrapperBenchHelper(dut)

    async def bench(ctx):
        await helper.assert_doesnt_start_read(ctx, 0)
        await helper.assert_doesnt_start_read(ctx, 41)
        await helper.assert_doesnt_start_read(ctx, 49)
        await helper.assert_doesnt_start_read(ctx, 255)

        await helper.read(ctx, 42, 0, False)
        await helper.read(ctx, 43, 0, False)
        await helper.read(ctx, 47, 0, False)
        await helper.read(ctx, 48, 0, False)

        await helper.write(ctx, 45, 0x145, False)
        await helper.read(ctx, 45, 0x145, False)

    run_bench(dut=dut, bench=bench)


if __name__ == "__main__":
    test()
