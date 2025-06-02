import random

import pytest
from amaranth import *
from amaranth.sim import Simulator

from pycachegen import *


@pytest.mark.slow
@pytest.mark.parametrize(
    "address_width,cache_data_width,cache_num_sets,cache_replacement_policy,byte_size,cache_write_buffer_size"
    + ",main_memory_data_width,delay_config",
    [(8, 32, 8, ReplacementPolicies.PLRU_TREE, 8, 6, 64, DelayConfig(4, 5, 4, 2, 3))],
)  # FIXME setting main_memory_data_width to 64 causes tests with block size > 1 to fail
@pytest.mark.parametrize("cache_num_ways", [1, 4])
@pytest.mark.parametrize("cache_block_size", [1, 4])
@pytest.mark.parametrize("cache_write_policy", [WritePolicies.WRITE_THROUGH, WritePolicies.WRITE_BACK])
@pytest.mark.parametrize("cache_write_allocate", [True, False])
def test(
    address_width,
    cache_data_width,
    cache_num_ways,
    cache_num_sets,
    cache_block_size,
    cache_replacement_policy,
    cache_write_policy,
    cache_write_allocate,
    cache_write_buffer_size,
    main_memory_data_width,
    delay_config,
    byte_size,
) -> None:
    print("Test start")
    random.seed(45)
    dut = CacheWrapper(
        address_width=address_width,
        cache_configs=[
            CacheConfig(
                data_width=cache_data_width,
                num_ways=cache_num_ways,
                num_sets=cache_num_sets,
                replacement_policy=cache_replacement_policy,
                write_policy=cache_write_policy,
                write_allocate=cache_write_allocate,
                block_size=cache_block_size,
                write_buffer_size=cache_write_buffer_size,
                data_memory_module="",
            )
        ],
        main_memory_data_width=main_memory_data_width,
        create_main_memory=True,
        num_ports=1,
        delay_config=delay_config,
        arbitration_scheme=ArbitrationScheme.ROUND_ROBIN,
        byte_size=byte_size,
    )

    async def bench(ctx):
        hits = 0
        memory_dict = dict()
        block_size = dut.cache_configs[0].block_size
        rand_interval_size = max(1, block_size // 3)
        min_address = 0
        max_address = 2**dut.fe_address_width
        bytes_per_word = dut.fe_memory_bus_signature.bytes_per_word
        address = 0
        for request_number in range(1, 10_001):
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
            hits += ctx.get(dut.hit_o_0)

            if write_strobe:
                # write request -> write to dict
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
                # read request -> check if read data is correct
                try:
                    assert ctx.get(dut.fe_0.read_data_valid)
                    assert ctx.get(dut.fe_0.read_data) == memory_dict.get(address, 0)
                except AssertionError:
                    raise RuntimeError(
                        f"Request {request_number} failed: Tried reading from {'{:X}'.format(address)} expecting"
                        + f" {'{:X}'.format(memory_dict.get(address, 0))},"
                        + f" got {'{:X}'.format(ctx.get(dut.fe_0.read_data))}"
                        + f" (read_data_valid: {ctx.get(dut.fe_0.read_data_valid)})"
                    )

            # print statistics
            if request_number % 1000 == 0:
                print(f"Requests processed: {request_number}, hit rate: {'{:.3f}'.format(hits/request_number)}")

    # setup simulator
    print(f"Starting random test for {dut}")
    sim = Simulator(dut)
    sim.add_clock(1e-6)
    sim.add_testbench(bench)
    sim.run()
    # with sim.write_vcd("random.vcd"):
    #     sim.run()
