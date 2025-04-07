import random

from amaranth import *
from amaranth.sim import Simulator

from pycachegen import *


def random_test(dut: CacheWrapper) -> None:
    async def bench(ctx):
        requests_processed = 0
        hits = 0
        memory_dict = dict()
        block_size = dut.cache_configs[0].block_size
        rand_interval_size = max(1, block_size // 3)
        min_address = 0
        max_address = 2**dut.fe_address_width
        bytes_per_word = dut.fe_memory_bus_signature.bytes_per_word
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
                address = (address + random.randint(-rand_interval_size, rand_interval_size)) % max_address
            if random.random() < 0.5:  # 50%
                write_strobe = 0
            elif random.random() < 0.75:  # 37,5%
                write_strobe = 2**bytes_per_word - 1
            else:  # 12,5%
                write_strobe = random.randrange(0, 2**bytes_per_word)
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
                val = memory_dict.get(address, 0)
                new_val = 0
                for i in range(bytes_per_word):
                    byte_in_mem = (val >> (i * dut.byte_size)) % (2**dut.byte_size)
                    byte_in_req = (write_data >> (i * dut.byte_size)) % (2**dut.byte_size)
                    if write_strobe & (1 << i):
                        new_byte = byte_in_req
                    else:
                        new_byte = byte_in_mem
                    new_val += new_byte << (i * dut.byte_size)
                memory_dict[address] = new_val
            else:
                # check if read data is correct
                try:
                    assert ctx.get(dut.fe_0.read_data_valid)
                    assert ctx.get(dut.fe_0.read_data) == memory_dict.get(address, 0)
                except AssertionError:
                    raise RuntimeError(
                        f"Request {requests_processed} failed: Tried reading from {address} expecting"
                        + f" {memory_dict.get(address, 0)}, got {ctx.get(dut.fe_0.read_data)}"
                        + f" (valid: {ctx.get(dut.fe_0.read_data_valid)})"
                    )

            # print statistics
            if requests_processed % 100 == 0:
                print(f"Requests processed: {requests_processed}, hit rate: {'{:.3f}'.format(hits/requests_processed)}")

    # setup simulator
    sim = Simulator(dut)
    sim.add_clock(1e-6)
    sim.add_testbench(bench)
    sim.run()
    # with sim.write_vcd("random.vcd"):
    #     sim.run()


if __name__ == "__main__":
    cache = CacheWrapper(
        num_ports=1,
        byte_size=8,
        address_width=8,
        main_memory_data_width=32,
        create_main_memory=True,
        read_delay=3,
        write_delay=5,
        cache_configs=[
            CacheConfig(
                data_width=32,
                num_ways=2,
                num_sets=8,
                block_size=1,
                replacement_policy=ReplacementPolicies.PLRU_TREE,
                write_policy=WritePolicies.WRITE_THROUGH,
                write_allocate=False,
                write_buffer_size=16,
                data_memory_module="",
            )
        ],
    )
    random_test(cache)
