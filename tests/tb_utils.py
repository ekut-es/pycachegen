import inspect
import os
import warnings
from math import ceil
from pathlib import Path

from amaranth.sim import Simulator

from pycachegen import CacheWrapper

from .expected_results import expected_results


class CacheWrapperBenchHelper:
    """This object provides useful functions for testing cache wrappers.
    To construct it, simply pass the cache wrapper elaboratable to __init__.
    You can then use methods like read and write by passing the simulator
    context object to them.
    """

    def __init__(self, cache_wrapper: CacheWrapper):
        self._dut = cache_wrapper
        self._address_format_spec = "{:0=" + str(ceil(cache_wrapper.fe_address_width / 4)) + "X}"
        self._data_format_spec = "{:0=" + str(ceil(cache_wrapper.fe_data_width / 4)) + "X}"
        self.elapsed_time = 0
        self.max_time = 1000

    def _get_timestamp(self):
        return "{: =4}".format(self.elapsed_time)

    def _addr_to_str(self, addr: int) -> str:
        return "0x" + self._address_format_spec.format(addr)

    def _data_to_str(self, data: int) -> str:
        return "0x" + self._data_format_spec.format(data)

    async def _tick(self, ctx, count: int = 1):
        if self.elapsed_time >= self.max_time:
            raise RuntimeError("Exceeded maximum simulation time")
        self.elapsed_time += count
        await ctx.tick().repeat(count)

    async def read(self, ctx, address: int, data_expected: int, hit_expected: bool):
        # send request
        print(f"{self._get_timestamp()}: R addr {self._addr_to_str(address)}")
        ctx.set(self._dut.fe_0.address, address)
        ctx.set(self._dut.fe_0.write_strobe, 0)
        ctx.set(self._dut.fe_0.request_valid, 1)
        # invalidate request
        await self._tick(ctx)
        ctx.set(self._dut.fe_0.request_valid, 0)
        # wait until the response is there
        while not ctx.get(self._dut.fe_0.read_data_valid):
            await self._tick(ctx)
        assert ctx.get(self._dut.fe_0.read_data) == data_expected
        assert ctx.get(self._dut.hit_o_0) == hit_expected
        # wait until the port gets ready again
        while not ctx.get(self._dut.fe_0.port_ready):
            await self._tick(ctx)
        # check that the read data is still the same
        assert ctx.get(self._dut.fe_0.read_data) == data_expected
        assert ctx.get(self._dut.hit_o_0) == hit_expected

    async def write(self, ctx, address: int, data: int, hit_expected: bool, write_strobe: int = -1):
        print(
            f"{self._get_timestamp()}: W addr {self._addr_to_str(address)}, data {self._data_to_str(data)},"
            + f" strobe {write_strobe}"
        )
        ctx.set(self._dut.fe_0.address, address)
        ctx.set(self._dut.fe_0.write_data, data)
        ctx.set(self._dut.fe_0.write_strobe, write_strobe)
        ctx.set(self._dut.fe_0.request_valid, 1)
        await self._tick(ctx)
        ctx.set(self._dut.fe_0.request_valid, 0)
        while not ctx.get(self._dut.fe_0.port_ready):  # NOTE waiting for port ready might not always be desired
            await self._tick(ctx)
        assert not ctx.get(
            self._dut.fe_0.read_data_valid
        )  # Not that important but it should still happen and thus be checked
        assert ctx.get(self._dut.hit_o_0) == hit_expected

    async def flush(self, ctx):
        print(f"{self._get_timestamp()}: Flush")
        ctx.set(self._dut.fe_0.flush, 1)
        await self._tick(ctx)
        ctx.set(self._dut.fe_0.flush, 0)
        while not ctx.get(self._dut.fe_0.flush_done):
            await self._tick(ctx)


def run_bench(dut, bench, vcd_path: str = "vcd", vcd_filename: str = ""):
    """Runs the given testbench on the given dut.
    The waveform will be recorded and saved using the given filename
    in the given file path.
    If no filename was provided, the filename of the calling function
    will be used with the .py suffix replaced by .vcd.
    """
    # setup simulator
    sim = Simulator(dut)
    sim.add_clock(1e-6)
    sim.add_testbench(bench)
    if not vcd_filename:
        caller_filename = os.path.basename(inspect.stack()[1].filename)
        if not caller_filename.endswith(".py"):
            raise RuntimeError("Automatic vcd filename determination failed.")
        vcd_filename = caller_filename.removesuffix(".py") + ".vcd"
    # create output directory
    Path(vcd_path).mkdir(parents=True, exist_ok=True)
    # run simulation and save vcd in output directory
    with sim.write_vcd(str(Path(vcd_path, vcd_filename))):
        sim.run()
    # check the expected result
    elapsed_time = sim._engine.now
    if vcd_filename in expected_results:
        if expected_results[vcd_filename] != elapsed_time:
            warnings.warn(
                f"Runtime for {vcd_filename} differs: Expected {expected_results[vcd_filename]}, got {elapsed_time}"
            )
    else:
        warnings.warn(f"Did not find an expected runtime for {vcd_filename}. Runtime: {elapsed_time} ")
