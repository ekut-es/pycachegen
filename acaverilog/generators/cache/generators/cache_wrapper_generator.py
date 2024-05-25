import sys
from math import ceil, log2
from veriloggen import (
    Module,
    Submodule,
    Posedge,
    Negedge,
    If,
    For,
    AndList,
    OrList,
    Not,
)

from acaverilog.generators.cache.generators.cache_generator import CacheGenerator
from acaverilog.generators.cache.generators.functional_memory_generator import FunctionalMemoryGenerator


class CacheWrapperGenerator:
    def __init__(self, *args) -> None:
        self.DATA_WIDTH = int(args[0])
        self.ADDRESS_WIDTH = int(args[1])
        self.NUM_WAYS = int(args[2])
        self.NUM_SETS = int(args[3])
        self.REPLACEMENT_POLICY = args[4]
        self.HIT_LATENCY = int(args[5])
        self.MISS_LATENCY = int(args[6])
        self.WRITE_THROUGH = bool(int(args[7]))
        self.WRITE_ALLOCATE = bool(int(args[8]))

    def generate_module(self) -> Module:
        m = Module("cache_wrapper")
        cache = CacheGenerator(
            address_width=self.ADDRESS_WIDTH,
            data_width=self.DATA_WIDTH,
            num_ways=self.NUM_WAYS,
            num_sets=self.NUM_SETS,
            replacement_policy=self.REPLACEMENT_POLICY,
            hit_latency=self.HIT_LATENCY,
            miss_latency=self.MISS_LATENCY,
            write_through=self.WRITE_THROUGH,
            write_allocate=self.WRITE_ALLOCATE
        ).generate_module()
        memory = FunctionalMemoryGenerator(
            data_width=self.DATA_WIDTH, address_width=self.ADDRESS_WIDTH
        ).generate_module()

        # Common Inputs
        clk_i = m.Input("clk_i")
        reset_n_i = m.Input("reset_n_i")

        # Cache Inputs
        flush_i =  m.Input("flush_i")
        address_i = m.Input("address_i", self.ADDRESS_WIDTH)
        address_valid_i = m.Input("address_valid_i")
        write_data_i = m.Input("write_data_i", self.DATA_WIDTH)
        write_data_valid_i = m.Input("write_data_valid_i")
        read_write_select_i = m.Input("read_write_select_i")

        # Cache Outputs
        read_data_o = m.Output("read_data_o", self.DATA_WIDTH)
        read_data_valid_o = m.Output("read_data_valid_o")
        write_done_o = m.Output("write_done_o")
        port_ready_o = m.Output("port_ready_o")
        hit_o = m.Output("hit_o")

        # Backend Cache <- Memory
        be_read_data = m.Wire("be_read_data", self.DATA_WIDTH)
        be_read_data_valid = m.Wire("be_read_data_valid")
        be_write_done = m.Wire("be_write_done")
        be_port_ready = m.Wire("be_port_ready")

        # Backend Cache -> Memory
        be_address = m.Wire("be_address", self.ADDRESS_WIDTH)
        be_address_valid = m.Wire("be_address_valid")
        be_write_data = m.Wire("be_write_data", self.DATA_WIDTH)
        be_write_data_valid = m.Wire("be_write_data_valid")
        be_read_write_select = m.Wire("be_read_write_select")

        Submodule(
            m,
            cache,
            "cache_child",
            arg_ports=(
                # Common
                ("clk_i", clk_i),
                ("reset_n_i", reset_n_i),
                # Cache In
                ("flush_i", flush_i),
                ("fe_address_i", address_i),
                ("fe_address_valid_i", address_valid_i),
                ("fe_write_data_i", write_data_i),
                ("fe_write_data_valid_i", write_data_valid_i),
                ("fe_read_write_select_i", read_write_select_i),
                # Cache Out
                ("fe_read_data_o", read_data_o),
                ("fe_read_data_valid_o", read_data_valid_o),
                ("fe_write_done_o", write_done_o),
                ("fe_port_ready_o", port_ready_o),
                ("fe_hit_o", hit_o),
                # Backend Cache <- Memory
                ("be_read_data_i", be_read_data),
                ("be_read_data_valid_i", be_read_data_valid),
                ("be_write_done_i", be_write_done),
                ("be_port_ready_i", be_port_ready),
                # Backend Cache -> Memory
                ("be_address_o", be_address),
                ("be_address_valid_o", be_address_valid),
                ("be_write_data_o", be_write_data),
                ("be_write_data_valid_o", be_write_data_valid),
                ("be_read_write_select_o", be_read_write_select),
            ),
        )

        Submodule(
            m,
            memory,
            "memory_child",
            arg_ports=(
                # Common
                ("clk_i", clk_i),
                ("reset_n_i", reset_n_i),
                # Backend Cache <- Memory
                ("read_data_0_o", be_read_data),
                ("read_data_valid_0_o", be_read_data_valid),
                ("write_done_0_o", be_write_done),
                ("port_ready_0_o", be_port_ready),
                # Backend Cache -> Memory
                ("address_0_i", be_address),
                ("address_valid_0_i", be_address_valid),
                ("write_data_0_i", be_write_data),
                ("write_data_valid_0_i", be_write_data_valid),
                ("read_write_select_0_i", be_read_write_select),
            ),
        )
        return m


if __name__ == "__main__":
    # argv: (file name), number for output file suffix, data width, address width, num ways, num sets, replacement policy, hit latency, miss latency, write through, write allocate
    cache_wrapper_generator = CacheWrapperGenerator(*sys.argv[2:])
    m = cache_wrapper_generator.generate_module()
    m.to_verilog(f"../src/cache_wrapper_{sys.argv[1]}.v", for_verilator=True)
