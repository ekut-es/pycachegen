from pycachegen import MemoryConfig
from pycachegen.cache_wrapper import CacheWrapper

from .tb_utils import run_bench


# Testbench for a CacheWrapper with only a main memory and no caches
def test():
    dut = CacheWrapper(
        address_width=3,
        num_ports=1,
        read_delay=1,
        write_delay=2,
        memory_config=MemoryConfig(
            data_width=32,
            min_address=3,
            max_address=7,
        ),
        cache_configs=[],
        create_main_memory=True,
        byte_size=8,
    )

    async def bench(ctx):
        # write to 5
        ctx.set(dut.fe_0.address, 5)
        ctx.set(dut.fe_0.write_strobe, 0b1101)
        ctx.set(dut.fe_0.write_data, 0xA0A1A2A3)
        ctx.set(dut.fe_0.request_valid, 1)

        # wait
        await ctx.tick()
        assert not ctx.get(dut.fe_0.port_ready)
        ctx.set(dut.fe_0.request_valid, 0)

        # wait
        await ctx.tick()
        assert not ctx.get(dut.fe_0.port_ready)

        # read from 5
        await ctx.tick()
        assert ctx.get(dut.fe_0.port_ready)
        ctx.set(dut.fe_0.write_strobe, 0)
        ctx.set(dut.fe_0.request_valid, 1)

        # wait
        await ctx.tick()
        assert not ctx.get(dut.fe_0.port_ready)
        ctx.set(dut.fe_0.request_valid, 0)

        # check that write to 2 doesn't to anything
        await ctx.tick()
        assert ctx.get(dut.fe_0.port_ready)
        assert ctx.get(dut.fe_0.read_data_valid)
        assert ctx.get(dut.fe_0.read_data == 0xA0A100A3)
        ctx.set(dut.fe_0.address, 2)
        ctx.set(dut.fe_0.write_strobe, 0b1111)
        ctx.set(dut.fe_0.write_data, 0x12345678)
        ctx.set(dut.fe_0.request_valid, 1)

        # check that write to 7 doesn't do anything
        await ctx.tick()
        assert ctx.get(dut.fe_0.port_ready)
        ctx.set(dut.fe_0.address, 7)

        # write to 4
        await ctx.tick()
        assert ctx.get(dut.fe_0.port_ready)
        ctx.set(dut.fe_0.address, 4)

        # wait
        await ctx.tick()
        assert not ctx.get(dut.fe_0.port_ready)
        assert not ctx.get(dut.fe_0.read_data_valid)  # check that read valid got reset
        ctx.set(dut.fe_0.request_valid, 0)

        # wait
        await ctx.tick()
        assert not ctx.get(dut.fe_0.port_ready)

        # read from 4
        await ctx.tick()
        assert ctx.get(dut.fe_0.port_ready)
        ctx.set(dut.fe_0.write_strobe, 0)
        ctx.set(dut.fe_0.request_valid, 1)

        # wait
        await ctx.tick()
        assert not ctx.get(dut.fe_0.port_ready)
        ctx.set(dut.fe_0.request_valid, 0)

        # read from 5 again
        await ctx.tick()
        assert ctx.get(dut.fe_0.port_ready)
        assert ctx.get(dut.fe_0.read_data_valid)
        assert ctx.get(dut.fe_0.read_data) == 0x12345678
        ctx.set(dut.fe_0.address, 5)
        ctx.set(dut.fe_0.request_valid, 1)

        # wait
        await ctx.tick()
        assert not ctx.get(dut.fe_0.port_ready)
        assert not ctx.get(dut.fe_0.read_data_valid)  # check that read valid got reset
        ctx.set(dut.fe_0.request_valid, 0)

        await ctx.tick()
        assert ctx.get(dut.fe_0.port_ready)
        assert ctx.get(dut.fe_0.read_data_valid)
        assert ctx.get(dut.fe_0.read_data) == 0xA0A100A3

    run_bench(dut=dut, bench=bench)
