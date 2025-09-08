from pycachegen import (
    CacheConfig,
    CacheWrapper,
    DelayConfig,
    ReplacementPolicies,
    WritePolicies,
)

from .tb_utils import run_bench


# Testbench for testing testbench access to the main memory
def test():
    dut = CacheWrapper(
        num_ports=1,
        byte_size=8,
        address_width=8,
        delay_config=DelayConfig(read_delay=9, write_delay=14),
        cache_configs=[
            CacheConfig(
                data_width=16,
                num_ways=1,
                num_sets=4,
                replacement_policy=ReplacementPolicies.FIFO,
                write_policy=WritePolicies.WRITE_THROUGH,
                write_allocate=False,
                block_size=1,
            )
        ],
        main_memory_data_width=32,
    )

    async def bench(ctx):
        ctx.set(dut.main_memory.data_memory.data[0], 0xDEADBEEF)
        await ctx.tick()

        assert ctx.get(dut.main_memory.data_memory.data[0]) == 0xDEADBEEF

    run_bench(dut=dut, bench=bench)
