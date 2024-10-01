from amaranth.sim import Simulator
from pycachegen.amaranth.main_memory import MainMemory
from pycachegen.cache_config_validation import InternalMemoryConfig, MemoryConfig


if __name__ == "__main__":
    dut = MainMemory(
        config=InternalMemoryConfig(
            MemoryConfig(
                data_width=32,
                read_latency=2,
                write_latency=3,
                min_address=(3 << 2),
                max_address=(7 << 2),
            ),
            address_width=3,
            byte_size=8,
            enable_reset=True,
        )
    )

    async def bench(ctx):
        # write to 5
        ctx.set(dut.mem_if.address, 5)
        ctx.set(dut.mem_if.write_strobe, 0b1101)
        ctx.set(dut.mem_if.write_data, 0xA0A1A2A3)
        ctx.set(dut.mem_if.request_valid, 1)

        # wait
        await ctx.tick()
        assert not ctx.get(dut.mem_if.port_ready)
        ctx.set(dut.mem_if.request_valid, 0)

        # wait
        await ctx.tick()
        assert not ctx.get(dut.mem_if.port_ready)

        # read from 5
        await ctx.tick()
        assert ctx.get(dut.mem_if.port_ready)
        ctx.set(dut.mem_if.write_strobe, 0)
        ctx.set(dut.mem_if.request_valid, 1)

        # wait
        await ctx.tick()
        assert not ctx.get(dut.mem_if.port_ready)
        ctx.set(dut.mem_if.request_valid, 0)

        # check that write to 2 doesn't to anything
        await ctx.tick()
        assert ctx.get(dut.mem_if.port_ready)
        assert ctx.get(dut.mem_if.read_data_valid)
        assert ctx.get(dut.mem_if.read_data == 0xA0A100A3)
        ctx.set(dut.mem_if.address, 2)
        ctx.set(dut.mem_if.write_strobe, 0b1111)
        ctx.set(dut.mem_if.write_data, 0x12345678)
        ctx.set(dut.mem_if.request_valid, 1)

        # check that write to 7 doesn't do anything
        await ctx.tick()
        assert ctx.get(dut.mem_if.port_ready)
        ctx.set(dut.mem_if.address, 7)

        # write to 4
        await ctx.tick()
        assert ctx.get(dut.mem_if.port_ready)
        ctx.set(dut.mem_if.address, 4)

        # wait
        await ctx.tick()
        assert not ctx.get(dut.mem_if.port_ready)
        assert not ctx.get(
            dut.mem_if.read_data_valid
        )  # check that read valid got reset
        ctx.set(dut.mem_if.request_valid, 0)

        # wait
        await ctx.tick()
        assert not ctx.get(dut.mem_if.port_ready)

        # read from 4
        await ctx.tick()
        assert ctx.get(dut.mem_if.port_ready)
        ctx.set(dut.mem_if.write_strobe, 0)
        ctx.set(dut.mem_if.request_valid, 1)

        # wait
        await ctx.tick()
        assert not ctx.get(dut.mem_if.port_ready)
        ctx.set(dut.mem_if.request_valid, 0)

        # read from 5 again
        await ctx.tick()
        assert ctx.get(dut.mem_if.port_ready)
        assert ctx.get(dut.mem_if.read_data_valid)
        assert ctx.get(dut.mem_if.read_data) == 0x12345678
        ctx.set(dut.mem_if.address, 5)
        ctx.set(dut.mem_if.request_valid, 1)

        # wait
        await ctx.tick()
        assert not ctx.get(dut.mem_if.port_ready)
        assert not ctx.get(
            dut.mem_if.read_data_valid
        )  # check that read valid got reset
        ctx.set(dut.mem_if.request_valid, 0)

        await ctx.tick()
        assert ctx.get(dut.mem_if.port_ready)
        assert ctx.get(dut.mem_if.read_data_valid)
        assert ctx.get(dut.mem_if.read_data) == 0xA0A100A3

    sim = Simulator(dut)
    sim.add_clock(1e-6)
    sim.add_testbench(bench)
    with sim.write_vcd("main_memory.vcd"):
        sim.run()
