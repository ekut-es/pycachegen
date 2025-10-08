import os
import unittest

from amaranth.sim import Simulator

from pycachegen import (
    CacheConfig,
    CacheWrapper,
    DelayConfig,
    ReplacementPolicies,
    WritePolicies,
)

__current_dir_path__ = os.path.dirname(os.path.abspath(__file__))


class TestCacheWrapperPerfCounters(unittest.TestCase):
    def test_cache_wrapper_perf_counters(self):

        OPCODE = 1
        ADDRESS = 2
        DUMMY = 12
        BURST = 2
        CLOCK_SPEED_MULTIPLIER = 2
        IDLE_CYCLES_TO_DEEP_POWER_DOWN = 10

        NUM_WAYS = 1
        NUM_SETS = 4
        BLOCK_SIZE = 2

        delay_config = DelayConfig(
            # -1 because it is a delay and the total latency is one higher
            burst_read_delay=CLOCK_SPEED_MULTIPLIER * (BURST) - 1,
            burst_write_delay=1,
            # - 1 because it is a delay, another -1 because only need to wait for 3 cycles after the
            # dummy cycles until we receive the fourth byte
            read_delay=CLOCK_SPEED_MULTIPLIER * (OPCODE + ADDRESS + DUMMY + BURST) - 1 - 1,
            write_delay=1,
            burst_block_size=BLOCK_SIZE,
            idle_cycles_to_deep_power_down=IDLE_CYCLES_TO_DEEP_POWER_DOWN,
        )

        dut = CacheWrapper(
            num_ports=1,
            byte_size=8,
            address_width=8,
            delay_config=delay_config,
            cache_configs=[
                CacheConfig(
                    data_width=16,
                    num_ways=NUM_WAYS,
                    num_sets=NUM_SETS,
                    replacement_policy=ReplacementPolicies.FIFO,
                    write_policy=WritePolicies.WRITE_THROUGH,
                    write_allocate=False,
                    block_size=BLOCK_SIZE,
                )
            ],
            perf_counter=True,
            main_memory_data_width=16,
        )

        async def read_request(ctx, address):
            ctx.set(dut.fe_0.address, address)
            ctx.set(dut.fe_0.request_valid, 1)

            await ctx.tick()

            ctx.set(dut.fe_0.address, 0x00)
            ctx.set(dut.fe_0.request_valid, 0)

            while ctx.get(dut.fe_0.read_data_valid) == 0:
                await ctx.tick()

            while ctx.get(dut.fe_0.port_ready) == 0:
                await ctx.tick()

        async def testbench(ctx):
            await ctx.tick()

            await read_request(ctx, 0x04)
            await read_request(ctx, 0x04)
            await read_request(ctx, 0x08)
            # await read_request(ctx, 0x08)
            # await read_request(ctx, 0x0c)

            await ctx.tick().repeat(30)

            await read_request(ctx, 0x0C)

        sim = Simulator(dut)
        sim.add_testbench(testbench)
        sim.add_clock(1e-6)

        vcd_file_path = __current_dir_path__ + "/../vcd/cache_wrapper_perf_counters.vcd"

        with sim.write_vcd(vcd_file_path):
            sim.run()


if __name__ == "__main__":
    unittest.main()
