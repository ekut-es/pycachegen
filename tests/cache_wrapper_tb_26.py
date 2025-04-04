from pycachegen import (
    ArbitrationScheme,
    CacheConfig,
    CacheWrapper,
    ReplacementPolicies,
    WritePolicies,
)

from .tb_utils import CacheWrapperBenchHelper, run_bench


# Testbench for testing a round robin arbiter
def test():
    dut = CacheWrapper(
        num_ports=4,
        arbitration_scheme=ArbitrationScheme.ROUND_ROBIN,
        byte_size=8,
        address_width=8,
        read_delay=4,
        write_delay=7,
        cache_configs=[
            CacheConfig(
                data_width=16,
                num_ways=2,
                num_sets=2,
                replacement_policy=ReplacementPolicies.LRU,
                write_policy=WritePolicies.WRITE_BACK,
                write_allocate=True,
                block_size=1,
            ),
        ],
        main_memory_data_width=32,
    )

    CacheWrapperBenchHelper(dut)

    async def bench(ctx):
        # read request from port 0
        ctx.set(dut.fe_0.request_valid, 1)
        ctx.set(dut.fe_0.address, 0)
        ctx.set(dut.fe_0.write_strobe, 0)

        # Write request from port 1
        ctx.set(dut.fe_1.request_valid, 1)
        ctx.set(dut.fe_1.address, 0)
        ctx.set(dut.fe_1.write_strobe, -1)
        ctx.set(dut.fe_1.write_data, 0x1000)

        # Write request from port 3
        ctx.set(dut.fe_3.request_valid, 1)
        ctx.set(dut.fe_3.address, 0)
        ctx.set(dut.fe_3.write_strobe, 0b01)
        ctx.set(dut.fe_3.write_data, 0x0010)

        await ctx.tick()
        # port 1 request should have been processed (because 0 is the initial previous grant)
        # port 0 & 3 request should have been buffered
        assert not ctx.get(dut.fe_0.port_ready)
        assert ctx.get(dut.fe_1.port_ready)
        assert ctx.get(dut.fe_2.port_ready)
        assert not ctx.get(dut.fe_3.port_ready)
        # dont send a new request from port 0 and 3
        ctx.set(dut.fe_0.request_valid, 0)
        ctx.set(dut.fe_3.request_valid, 0)
        # send a new write request from port 1 (should have least priority)
        ctx.set(dut.fe_1.write_data, 0)
        # send a read request from port 2 -> should be processed next
        ctx.set(dut.fe_2.request_valid, 1)
        ctx.set(dut.fe_2.address, 0)
        ctx.set(dut.fe_2.write_strobe, 0)

        await ctx.tick()
        # request 2 should have been processed now.
        # all others should have been buffered
        assert not ctx.get(dut.fe_0.port_ready)
        assert not ctx.get(dut.fe_1.port_ready)
        assert ctx.get(dut.fe_2.port_ready)
        assert not ctx.get(dut.fe_3.port_ready)
        # dont send any new requests
        ctx.set(dut.fe_1.request_valid, 0)
        ctx.set(dut.fe_2.request_valid, 0)
        # check that request 2 was processed correctly
        assert ctx.get(dut.fe_2.read_data_valid)
        assert ctx.get(dut.fe_2.read_data) == 0x1000

        await ctx.tick()
        # write request from port 3 should be done now
        assert not ctx.get(dut.fe_0.port_ready)
        assert not ctx.get(dut.fe_1.port_ready)
        assert ctx.get(dut.fe_2.port_ready)
        assert ctx.get(dut.fe_3.port_ready)

        await ctx.tick()
        # read from port 0 should be done
        assert ctx.get(dut.fe_0.port_ready)
        assert not ctx.get(dut.fe_1.port_ready)
        assert ctx.get(dut.fe_2.port_ready)
        assert ctx.get(dut.fe_3.port_ready)
        assert ctx.get(dut.fe_0.read_data_valid)
        assert ctx.get(dut.fe_0.read_data) == 0x1010

        await ctx.tick()
        # write from port 1 should be done now
        assert ctx.get(dut.fe_0.port_ready)
        assert ctx.get(dut.fe_1.port_ready)
        assert ctx.get(dut.fe_2.port_ready)
        assert ctx.get(dut.fe_3.port_ready)
        # send new read request from port 0
        ctx.set(dut.fe_0.write_strobe, 0)
        ctx.set(dut.fe_0.request_valid, 1)

        await ctx.tick()
        # check that the read worked and that the previous write did its thing
        assert ctx.get(dut.fe_0.port_ready)
        assert ctx.get(dut.fe_1.port_ready)
        assert ctx.get(dut.fe_2.port_ready)
        assert ctx.get(dut.fe_3.port_ready)
        assert ctx.get(dut.fe_0.read_data_valid)
        assert ctx.get(dut.fe_0.read_data) == 0
        # check that port 2 still has its original read data
        assert ctx.get(dut.fe_2.read_data_valid)
        assert ctx.get(dut.fe_2.read_data) == 0x1000

    run_bench(dut=dut, bench=bench)
