from amaranth.sim import Simulator
from .tb_utils import run_bench
from pycachegen.main_memory import MainMemory
from pycachegen.cache_config_validation import InternalMemoryConfig, MemoryConfig


# Testbench for the main memory
def test():
    dut = MainMemory(
        config=InternalMemoryConfig(
            MemoryConfig(
                data_width=32,
                read_latency=2,
                write_latency=3,
                min_address=3,
                max_address=7,
            ),
            address_width=3,
            byte_size=8,
        )
    )

    async def bench(ctx):
        # write to 5
        ctx.set(dut.fe.address, 5)
        ctx.set(dut.fe.write_strobe, 0b1101)
        ctx.set(dut.fe.write_data, 0xA0A1A2A3)
        ctx.set(dut.fe.request_valid, 1)

        # wait
        await ctx.tick()
        assert not ctx.get(dut.fe.port_ready)
        ctx.set(dut.fe.request_valid, 0)

        # wait
        await ctx.tick()
        assert not ctx.get(dut.fe.port_ready)

        # read from 5
        await ctx.tick()
        assert ctx.get(dut.fe.port_ready)
        ctx.set(dut.fe.write_strobe, 0)
        ctx.set(dut.fe.request_valid, 1)

        # wait
        await ctx.tick()
        assert not ctx.get(dut.fe.port_ready)
        ctx.set(dut.fe.request_valid, 0)

        # check that write to 2 doesn't to anything
        await ctx.tick()
        assert ctx.get(dut.fe.port_ready)
        assert ctx.get(dut.fe.read_data_valid)
        assert ctx.get(dut.fe.read_data == 0xA0A100A3)
        ctx.set(dut.fe.address, 2)
        ctx.set(dut.fe.write_strobe, 0b1111)
        ctx.set(dut.fe.write_data, 0x12345678)
        ctx.set(dut.fe.request_valid, 1)

        # check that write to 7 doesn't do anything
        await ctx.tick()
        assert ctx.get(dut.fe.port_ready)
        ctx.set(dut.fe.address, 7)

        # write to 4
        await ctx.tick()
        assert ctx.get(dut.fe.port_ready)
        ctx.set(dut.fe.address, 4)

        # wait
        await ctx.tick()
        assert not ctx.get(dut.fe.port_ready)
        assert not ctx.get(dut.fe.read_data_valid)  # check that read valid got reset
        ctx.set(dut.fe.request_valid, 0)

        # wait
        await ctx.tick()
        assert not ctx.get(dut.fe.port_ready)

        # read from 4
        await ctx.tick()
        assert ctx.get(dut.fe.port_ready)
        ctx.set(dut.fe.write_strobe, 0)
        ctx.set(dut.fe.request_valid, 1)

        # wait
        await ctx.tick()
        assert not ctx.get(dut.fe.port_ready)
        ctx.set(dut.fe.request_valid, 0)

        # read from 5 again
        await ctx.tick()
        assert ctx.get(dut.fe.port_ready)
        assert ctx.get(dut.fe.read_data_valid)
        assert ctx.get(dut.fe.read_data) == 0x12345678
        ctx.set(dut.fe.address, 5)
        ctx.set(dut.fe.request_valid, 1)

        # wait
        await ctx.tick()
        assert not ctx.get(dut.fe.port_ready)
        assert not ctx.get(dut.fe.read_data_valid)  # check that read valid got reset
        ctx.set(dut.fe.request_valid, 0)

        await ctx.tick()
        assert ctx.get(dut.fe.port_ready)
        assert ctx.get(dut.fe.read_data_valid)
        assert ctx.get(dut.fe.read_data) == 0xA0A100A3

    run_bench(dut, bench)
