from amaranth.sim import Simulator
from pycachegen.amaranth.cache_wrapper import CacheWrapper
from pycachegen.cache_config_validation import CacheConfig, MemoryConfig

dut = CacheWrapper(
    num_ports=1,
    arbiter_policy="priority",
    byte_size=8,
    enable_reset=False,
    address_width=9,
    cache_configs=[
        CacheConfig(
            data_width=16,
            num_ways=1,
            num_sets=4,
            replacement_policy="fifo",
            hit_latency=10,
            miss_latency=15,
            write_through=True,
            write_allocate=False,
            block_size=1,
        )
    ],
    memory_config=MemoryConfig(
        data_width=16, read_latency=10, write_latency=15, min_address=0, max_address=512
    ),
)


async def bench(ctx):
    ctx.set(dut.fe.address, 0)
    ctx.set(dut.fe.write_strobe, 0)
    ctx.set(dut.fe.request_valid, 1)
    await ctx.tick()
    ctx.set(dut.fe.request_valid, 0)
    while not ctx.get(dut.fe.port_ready):
        await ctx.tick()
    assert ctx.get(dut.fe.read_data_valid) == 1
    assert ctx.get(dut.fe.read_data) == 0


sim = Simulator(dut)
sim.add_clock(1e-6)
sim.add_testbench(bench)
with sim.write_vcd("cache_wrapper.vcd"):
    sim.run()
