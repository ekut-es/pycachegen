from pycachegen import (
    CacheConfig,
    CacheWrapper,
    DelayConfig,
    ReplacementPolicies,
    WritePolicies,
)

from .tb_utils import CacheWrapperBenchHelper, run_bench


# Testbench for testing burst mode with a write through cache
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
        cache_configs=[
            CacheConfig(
                data_width=16,
                num_ways=1,
                num_sets=4,
                replacement_policy=ReplacementPolicies.PLRU_TREE,
                write_policy=WritePolicies.WRITE_THROUGH,
                write_allocate=False,
                block_size=4,
                write_buffer_size=0,
            )
        ],
        main_memory_data_width=16,
    )

    helper = CacheWrapperBenchHelper(dut)

    async def bench(ctx):
        # read triggers read_block, which should utilize the burst
        await helper.read(ctx, 0, 0, False)

        # brust two writes to the main memory
        await helper.write(ctx, 5, 0x1005, False)
        await helper.write(ctx, 6, 0x1005, False)

        # now read some more blocks which should all start bursts
        await helper.read(ctx, 4, 0, False)
        await helper.read(ctx, 8, 0, False)
        await helper.read(ctx, 12, 0, False)
        await helper.read(ctx, 16, 0, False)

    run_bench(dut=dut, bench=bench)
