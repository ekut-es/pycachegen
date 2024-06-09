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
from itertools import chain

from acaverilog.generators.cache.generators.cache_generator import CacheGenerator
from acaverilog.generators.cache.generators.functional_memory_generator import (
    FunctionalMemoryGenerator,
)
from acaverilog.generators.cache.generators.memory_access_arbiter import (
    MemoryAccessArbiter,
)


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
        self.BLOCK_SIZE = int(args[9])
        self.NUM_PORTS = int(args[10])

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
            write_allocate=self.WRITE_ALLOCATE,
            block_size=self.BLOCK_SIZE,
        ).generate_module()
        memory = FunctionalMemoryGenerator(
            data_width=self.DATA_WIDTH, address_width=self.ADDRESS_WIDTH
        ).generate_module()

        # Common Inputs
        clk_i = m.Input("clk_i")
        reset_n_i = m.Input("reset_n_i")

        # Cache Signals that do not need to be arbitrated
        flush_i = m.Input("flush_i")
        hit_o = m.Output("hit_o")

        # Frontend Inputs
        address_i = []
        address_valid_i = []
        write_data_i = []
        write_data_valid_i = []
        read_write_select_i = []
        # Frontend Outputs
        read_data_o = []
        read_data_valid_o = []
        write_done_o = []
        port_ready_o = []

        for i in range(self.NUM_PORTS):
            address_i.append(m.Input(f"address_{i}_i", self.ADDRESS_WIDTH))
            address_valid_i.append(m.Input(f"address_valid_{i}_i"))
            write_data_i.append(m.Input(f"write_data_{i}_i", self.DATA_WIDTH))
            write_data_valid_i.append(m.Input(f"write_data_valid_{i}_i"))
            read_write_select_i.append(m.Input(f"read_write_select_{i}_i"))
            read_data_o.append(m.Output(f"read_data_{i}_o", self.DATA_WIDTH))
            read_data_valid_o.append(m.Output(f"read_data_valid_{i}_o"))
            write_done_o.append(m.Output(f"write_done_{i}_o"))
            port_ready_o.append(m.Output(f"port_ready_{i}_o"))

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

        if self.NUM_PORTS == 1:
            Submodule(
                m,
                cache,
                "cache",
                arg_ports=(
                    # Common
                    ("clk_i", clk_i),
                    ("reset_n_i", reset_n_i),
                    # Signals that dont need arbitration
                    ("flush_i", flush_i),
                    ("fe_hit_o", hit_o),
                    # Cache In
                    ("fe_address_i", address_i[0]),
                    ("fe_address_valid_i", address_valid_i[0]),
                    ("fe_write_data_i", write_data_i[0]),
                    ("fe_write_data_valid_i", write_data_valid_i[0]),
                    ("fe_read_write_select_i", read_write_select_i[0]),
                    # Cache Out
                    ("fe_read_data_o", read_data_o[0]),
                    ("fe_read_data_valid_o", read_data_valid_o[0]),
                    ("fe_write_done_o", write_done_o[0]),
                    ("fe_port_ready_o", port_ready_o[0]),
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
        else:
            # arbiter -> cache
            arbiter_address = m.Wire("arbiter_address", self.ADDRESS_WIDTH)
            arbiter_address_valid = m.Wire("arbiter_address_valid")
            arbiter_write_data = m.Wire("arbiter_write_data", self.DATA_WIDTH)
            arbiter_write_data_valid = m.Wire("arbiter_write_data_valid")
            arbiter_read_write_select = m.Wire("arbiter_read_write_select")
            # arbiter <- cache
            arbiter_port_ready = m.Wire("arbiter_port_ready")
            arbiter_read_data = m.Wire("arbiter_read_data", self.DATA_WIDTH)
            arbiter_read_data_valid = m.Wire("arbiter_read_data_valid")
            arbiter_write_done = m.Wire("arbiter_write_done")

            arbiter = MemoryAccessArbiter(
                self.NUM_PORTS, self.ADDRESS_WIDTH, self.DATA_WIDTH
            ).generate_module()

            arbiter_fe_mapping = []
            for i in range(self.NUM_PORTS):
                arbiter_fe_mapping.extend(
                    [
                        ("fe_address_{i}_i", address_i[i]),
                        ("fe_address_valid_{i}_i", address_valid_i[i]),
                        ("fe_write_data_{i}_i", write_data_i[i]),
                        ("fe_write_data_valid_{i}_i", write_data_valid_i[i]),
                        ("fe_read_write_select_{i}_i", read_write_select_i[i]),
                        ("fe_read_data_{i}_o", read_data_o[i]),
                        ("fe_read_data_valid_{i}_o", read_data_valid_o[i]),
                        ("fe_write_done_{i}_o", write_done_o[i]),
                        ("fe_port_ready_{i}_o", port_ready_o[i]),
                    ]
                )
            Submodule(
                m,
                arbiter,
                "arbiter",
                arg_ports=(
                    ("clk_i", clk_i),
                    ("reset_n_i", reset_n_i),
                    ("be_port_ready_i", arbiter_port_ready),
                    ("be_read_data_i", arbiter_read_data),
                    ("be_read_data_valid_i", arbiter_read_data_valid),
                    ("be_write_done_i", arbiter_write_done),
                    ("be_address_o", arbiter_address),
                    ("be_address_valid_o", arbiter_address_valid),
                    ("be_write_data_o", arbiter_write_data),
                    ("be_write_data_valid_o", arbiter_write_data_valid),
                    ("be_read_write_select_o", arbiter_read_write_select),
                    *arbiter_fe_mapping,
                ),
            )
            Submodule(
                m,
                cache,
                "cache",
                arg_ports=(
                    # Common
                    ("clk_i", clk_i),
                    ("reset_n_i", reset_n_i),
                    # Signals that dont need arbitration
                    ("flush_i", flush_i),
                    ("fe_hit_o", hit_o),
                    # Cache In
                    ("fe_address_i", arbiter_address),
                    ("fe_address_valid_i", arbiter_address_valid),
                    ("fe_write_data_i", arbiter_write_data),
                    ("fe_write_data_valid_i", arbiter_write_data_valid),
                    ("fe_read_write_select_i", arbiter_read_write_select),
                    # Cache Out
                    ("fe_read_data_o", arbiter_read_data),
                    ("fe_read_data_valid_o", arbiter_read_data_valid),
                    ("fe_write_done_o", arbiter_write_done),
                    ("fe_port_ready_o", arbiter_port_ready),
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
            "memory",
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
    # argv: (file name), number for output file suffix, data width, address width, num ways, num sets, replacement policy, hit latency, miss latency, write through, write allocate, block size, num ports
    cache_wrapper_generator = CacheWrapperGenerator(*sys.argv[2:])
    m = cache_wrapper_generator.generate_module()
    m.to_verilog(f"../src/cache_wrapper_{sys.argv[1]}.v", for_verilator=True)
