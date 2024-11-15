from .tb_utils import (
    CacheWrapperBenchHelper,
    run_bench,
)
from pycachegen.cache_wrapper import CacheWrapper
from pycachegen.cache_config_validation import (
    CacheConfig,
    MemoryConfig,
    ReplacementPolicies,
)
from pycachegen.arbiter import ArbitrationScheme


# Testbench for testing a priority arbiter but with longer cache delays
def test():
    dut = CacheWrapper(
        num_ports=3,
        arbitration_scheme=ArbitrationScheme.PRIORITY,
        byte_size=8,
        enable_reset=False,
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
        # Write request from port 0 to addr 0
        ctx.set(dut.fe_0.request_valid, 1)
        ctx.set(dut.fe_0.address, 0)
        ctx.set(dut.fe_0.write_strobe, -1)
        ctx.set(dut.fe_0.write_data, 0x1000)

        # Read request from port 1 from addr 6 (which is in another block)
        ctx.set(dut.fe_1.request_valid, 1)
        ctx.set(dut.fe_1.address, 6)
        ctx.set(dut.fe_1.write_strobe, 0)

        # Read request from port 2 from addr 0
        ctx.set(dut.fe_2.request_valid, 1)
        ctx.set(dut.fe_2.address, 0)
        ctx.set(dut.fe_2.write_strobe, 0)

        await ctx.tick()
        # all requests buffered, dont send new requests
        ctx.set(dut.fe_0.request_valid, 0)
        ctx.set(dut.fe_1.request_valid, 0)
        ctx.set(dut.fe_2.request_valid, 0)
        assert not ctx.get(dut.fe_0.port_ready)
        assert not ctx.get(dut.fe_1.port_ready)
        assert not ctx.get(dut.fe_2.port_ready)

        # wait until port 1's read data is valid
        while not ctx.get(dut.fe_1.read_data_valid):
            await ctx.tick()
        # check that it's correct
        assert ctx.get(dut.fe_1.read_data) == 0
        # check that port 1 is still not ready because the cache is still busy with its request
        assert ctx.get(dut.fe_0.port_ready)
        assert not ctx.get(dut.fe_1.port_ready)
        assert not ctx.get(dut.fe_2.port_ready)

        # now do the same for port 2 read data: wait until valid
        while not ctx.get(dut.fe_2.read_data_valid):
            await ctx.tick()
        # check that the data is correct
        assert ctx.get(dut.fe_2.read_data) == 0x1000
        # the cache should be ready again and so all ports should be ready too
        assert ctx.get(dut.fe_0.port_ready)
        assert ctx.get(dut.fe_1.port_ready)
        assert ctx.get(dut.fe_2.port_ready)

    run_bench(dut=dut, bench=bench)
