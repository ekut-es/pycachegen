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


# Testbench for testing a priority arbiter
def test():
    dut = CacheWrapper(
        num_ports=4,
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
                block_size=1,
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
        # Write request from port 0
        ctx.set(dut.fe_0.request_valid, 1)
        ctx.set(dut.fe_0.address, 0)
        ctx.set(dut.fe_0.write_strobe, -1)
        ctx.set(dut.fe_0.write_data, 0x1000)

        # Read request from port 1
        ctx.set(dut.fe_1.request_valid, 1)
        ctx.set(dut.fe_1.address, 0)
        ctx.set(dut.fe_1.write_strobe, 0)

        # Write request from port 2
        ctx.set(dut.fe_2.request_valid, 1)
        ctx.set(dut.fe_2.address, 0)
        ctx.set(dut.fe_2.write_strobe, 0b01)
        ctx.set(dut.fe_2.write_data, 0x0010)

        # Read request from port 3
        ctx.set(dut.fe_3.request_valid, 1)
        ctx.set(dut.fe_3.address, 0)
        ctx.set(dut.fe_3.write_strobe, 0)

        await ctx.tick()
        # all requests should be buffered,
        # request from port 0 should have been processed already
        # send a new write request from port 0, clear all other requests
        ctx.set(dut.fe_0.write_strobe, 0b10)
        ctx.set(dut.fe_0.write_data, 0x1100)
        ctx.set(dut.fe_1.request_valid, 0)
        ctx.set(dut.fe_2.request_valid, 0)
        ctx.set(dut.fe_3.request_valid, 0)
        assert ctx.get(dut.fe_0.port_ready)
        assert not ctx.get(dut.fe_1.port_ready)
        assert not ctx.get(dut.fe_2.port_ready)
        assert not ctx.get(dut.fe_3.port_ready)

        await ctx.tick()
        # new request from port 0 should have been processed now
        ctx.set(dut.fe_0.request_valid, 0)
        assert ctx.get(dut.fe_0.port_ready)
        assert not ctx.get(dut.fe_1.port_ready)
        assert not ctx.get(dut.fe_2.port_ready)
        assert not ctx.get(dut.fe_3.port_ready)

        await ctx.tick()
        # read request from port 1 should be done now
        assert ctx.get(dut.fe_0.port_ready)
        assert ctx.get(dut.fe_1.port_ready)
        assert not ctx.get(dut.fe_2.port_ready)
        assert not ctx.get(dut.fe_3.port_ready)
        assert ctx.get(dut.fe_1.read_data_valid)
        assert ctx.get(dut.fe_1.read_data) == 0x1100

        await ctx.tick()
        # write from port 2 should be done. also check that port 1 read data is still correct
        assert ctx.get(dut.fe_0.port_ready)
        assert ctx.get(dut.fe_1.port_ready)
        assert ctx.get(dut.fe_2.port_ready)
        assert not ctx.get(dut.fe_3.port_ready)
        assert ctx.get(dut.fe_1.read_data_valid)
        assert ctx.get(dut.fe_1.read_data) == 0x1100

        await ctx.tick()
        # port 3 read should be done now
        assert ctx.get(dut.fe_0.port_ready)
        assert ctx.get(dut.fe_1.port_ready)
        assert ctx.get(dut.fe_2.port_ready)
        assert ctx.get(dut.fe_3.port_ready)
        assert ctx.get(dut.fe_1.read_data_valid)
        assert ctx.get(dut.fe_1.read_data) == 0x1100
        assert ctx.get(dut.fe_3.read_data_valid)
        assert ctx.get(dut.fe_3.read_data) == 0x1110

    run_bench(dut=dut, bench=bench)
