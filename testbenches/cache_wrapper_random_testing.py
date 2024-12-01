import random
from amaranth import *
from amaranth.sim import Simulator
from pycachegen import *


def random_test(dut: CacheWrapper) -> None:
    async def bench(ctx):
        requests_processed = 0
        hits = 0
        memory_dict = dict()
        data_width_ratio = dut.memory_config.data_width // dut.fe_data_width
        block_size = dut.cache_configs[0].block_size
        rand_interval_size = max(1, block_size // 3)
        min_address = dut.memory_config.min_address * data_width_ratio
        max_address = dut.memory_config.max_address * data_width_ratio
        address = 0
        while True:
            # generate a random request
            if random.random() < 0.05:
                # jump to a completely random address
                address = random.randrange(
                    min_address,
                    max_address,
                )
            else:
                # jump to a nearby address
                address = (
                    address + random.randrange(-rand_interval_size, rand_interval_size)
                ) % max_address
            write_strobe = (
                0 if random.random() < 0.5 else (2 ** (dut.fe_bytes_per_word) - 1)
            )
            write_data = random.randrange(0, 2**dut.fe_data_width)

            # send the request
            ctx.set(dut.fe_0.address, address)
            ctx.set(dut.fe_0.write_strobe, write_strobe)
            ctx.set(dut.fe_0.write_data, write_data)
            ctx.set(dut.fe_0.request_valid, 1)
            await ctx.tick()

            # wait for the cache to get ready again
            ctx.set(dut.fe_0.request_valid, 0)
            while not ctx.get(dut.fe_0.port_ready):
                await ctx.tick()

            # update own statistics
            requests_processed += 1
            hits += ctx.get(dut.hit_o_0)

            if write_strobe:
                # write to dict
                memory_dict[address] = write_data
            else:
                # check if read data is correct
                assert ctx.get(dut.fe_0.read_data_valid), str(requests_processed)
                assert ctx.get(dut.fe_0.read_data) == memory_dict.get(address, 0), str(
                    requests_processed
                )

            # print statistics
            if requests_processed % 100 == 0:
                print(
                    f"Requests processed: {requests_processed}, hit rate: {'{:.3f}'.format(hits/requests_processed)}"
                )

    # setup simulator
    sim = Simulator(dut)
    sim.add_clock(1e-6)
    sim.add_testbench(bench)
    sim.run()


if __name__ == "__main__":
    cache = CacheWrapper(
        num_ports=1,
        byte_size=8,
        address_width=8,
        memory_config=MemoryConfig(
            data_width=64,
            read_latency=2,
            write_latency=3,
            min_address=0,
            max_address=2**7,
        ),
        cache_configs=[
            CacheConfig(
                data_width=32,
                num_ways=4,
                num_sets=4,
                block_size=4,
                replacement_policy=ReplacementPolicies.PLRU_TREE,
                write_through=False,
                write_allocate=True,
                hit_latency=0,
                miss_latency=0,
            )
        ],
    )
    random_test(cache)
