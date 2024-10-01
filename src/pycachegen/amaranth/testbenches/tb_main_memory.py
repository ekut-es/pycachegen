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
        # write
        ctx.set(dut.mem_if.address, 5)
        ctx.set(dut.mem_if.write_strobe, 0b1101)
        ctx.set(dut.mem_if.write_data, 0xA0A1A2A3)
        ctx.set(dut.mem_if.request_valid, 1)

        # wait
        await ctx.tick()
        assert not ctx.get(dut.mem_if.port_ready)
        ctx.set(dut.mem_if.request_valid, 0)
        await ctx.tick()
        assert not ctx.get(dut.mem_if.port_ready)

        # read
        await ctx.tick()
        assert ctx.get(dut.mem_if.port_ready)
        ctx.set(dut.mem_if.write_strobe, 0)
        ctx.set(dut.mem_if.request_valid, 1)

        # wait
        await ctx.tick()
        assert not ctx.get(dut.mem_if.port_ready)
        ctx.set(dut.mem_if.request_valid, 0)

        await ctx.tick()
        assert ctx.get(dut.mem_if.port_ready)
        assert ctx.get(dut.mem_if.read_data_valid)
        assert ctx.get(dut.mem_if.read_data == 0xA0A100A3)

    sim = Simulator(dut)
    sim.add_clock(1e-6)
    sim.add_testbench(bench)
    with sim.write_vcd("main_memory.vcd"):
        sim.run()
