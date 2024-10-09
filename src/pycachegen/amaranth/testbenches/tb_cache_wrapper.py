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

elapsed_time = 0


async def tick(ctx, count: int = 1):
    global elapsed_time
    elapsed_time += count
    await ctx.tick().repeat(count)


async def read(ctx, address: int, data_expected: int, hit_expected: bool):
    print(f"READ  at {elapsed_time}: addr {address}...", end=" ")
    ctx.set(dut.fe.address, address)
    ctx.set(dut.fe.write_strobe, 0)
    ctx.set(dut.fe.request_valid, 1)
    await tick(ctx)
    ctx.set(dut.fe.request_valid, 0)
    while not ctx.get(dut.fe.read_data_valid):
        await tick(ctx)
    assert ctx.get(dut.fe.read_data) == data_expected
    assert ctx.get(dut.hit_o) == hit_expected
    print("success")


async def write(ctx, address: int, data: int, hit_expected: bool):
    print(f"WRITE at {elapsed_time}: addr {address}, data {data}...", end=" ")
    ctx.set(dut.fe.address, address)
    ctx.set(dut.fe.write_data, data)
    ctx.set(dut.fe.write_strobe, -1)
    ctx.set(dut.fe.request_valid, 1)
    await tick(ctx)
    ctx.set(dut.fe.request_valid, 0)
    while not ctx.get(
        dut.fe.port_ready
    ):  # NOTE waiting for port ready might not always be desired
        await tick(ctx)
    assert not ctx.get(
        dut.fe.read_data_valid
    )  # Not that important but it should still happen and thus be checked
    assert ctx.get(dut.hit_o) == hit_expected
    print("success")


async def bench(ctx):
    await read(ctx, 0, 0, False)
    await read(ctx, 1, 0, False)
    await read(ctx, 2, 0, False)
    await read(ctx, 3, 0, False)

    await read(ctx, 0, 0, True)
    await read(ctx, 1, 0, True)
    await read(ctx, 2, 0, True)
    await read(ctx, 3, 0, True)

    await write(ctx, 4, 333, False)
    await read(ctx, 0, 0, True)
    await read(ctx, 4, 333, False)
    await read(ctx, 4, 333, True)
    await read(ctx, 0, 0, False)
    await read(ctx, 0, 0, True)


sim = Simulator(dut)
sim.add_clock(1e-6)
sim.add_testbench(bench)
with sim.write_vcd("cache_wrapper.vcd"):
    sim.run_until(1000 * 1e-6)
