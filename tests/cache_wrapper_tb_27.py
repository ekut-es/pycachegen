from .tb_utils import (
    CacheWrapperBenchHelper,
    run_bench,
)
from pycachegen.cache_wrapper import CacheWrapper
from pycachegen.cache_config import (
    CacheConfig,
    MemoryConfig,
    ReplacementPolicies,
)


# Testbench for testing that handing out read data before ready
# gets delayed properly
def test():
    hit_latency = 5
    miss_latency = 16
    dut = CacheWrapper(
        num_ports=1,
        byte_size=8,
        address_width=8,
        cache_configs=[
            CacheConfig(
                data_width=16,
                num_ways=2,
                num_sets=2,
                replacement_policy=ReplacementPolicies.LRU,
                write_through=False,
                write_allocate=True,
                block_size=4,
                hit_latency=hit_latency,
                miss_latency=miss_latency,
            ),
        ],
        memory_config=MemoryConfig(
            data_width=32,
            read_latency=5,
            write_latency=8,
            min_address=0,
            max_address=128,
        ),
    )

    helper = CacheWrapperBenchHelper(dut)

    async def bench(ctx):
        # Create a read miss
        ctx.set(dut.fe_0.request_valid, 1)
        ctx.set(dut.fe_0.address, 0)
        ctx.set(dut.fe_0.write_strobe, 0)

        # wait until the read data is valid
        while not ctx.get(dut.fe_0.read_data_valid):
            await ctx.tick()

        # check that the port is not yet ready
        assert not ctx.get(dut.fe_0.port_ready)

        while not ctx.get(dut.fe_0.port_ready):
            await ctx.tick()

        # now do some other reads/writes (without timing checks)
        # to check that everything still works
        await helper.read(ctx, 0, 0, True)
        await helper.read(ctx, 1, 0, True)
        await helper.write(ctx, 2, 0x1002, True)
        await helper.read(ctx, 2, 0x1002, True)
        await helper.read(ctx, 3, 0, True)

    run_bench(dut=dut, bench=bench)
