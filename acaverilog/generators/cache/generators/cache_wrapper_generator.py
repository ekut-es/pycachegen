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
    """Generates a top level module containing one ore more caches and a main memory.
    There can also be an arbiter infront of the L1 cache. The caches are set up in a linear
    hierarchy.
    """

    def __init__(self, *args) -> None:
        NUM_COMMON_ARGS = 2
        self.NUM_PORTS = int(args[0])
        self.ARBITER_POLICY = args[1]
        self.NUM_CACHES = len(args) - NUM_COMMON_ARGS - 1
        cache_configs = [config.split() for config in args[NUM_COMMON_ARGS:-1]]
        self.DATA_WIDTH = [int(config[0]) for config in cache_configs]
        self.ADDRESS_WIDTH = [int(config[1]) for config in cache_configs]
        self.NUM_WAYS = [int(config[2]) for config in cache_configs]
        self.NUM_SETS = [int(config[3]) for config in cache_configs]
        self.REPLACEMENT_POLICY = [config[4] for config in cache_configs]
        self.HIT_LATENCY = [int(config[5]) for config in cache_configs]
        self.MISS_LATENCY = [int(config[6]) for config in cache_configs]
        self.WRITE_THROUGH = [bool(int(config[7])) for config in cache_configs]
        self.WRITE_ALLOCATE = [bool(int(config[8])) for config in cache_configs]
        self.BLOCK_SIZE = [int(config[9]) for config in cache_configs]
        self.DATA_WIDTH.append(int(args[-1].split()[0]))  # main memory data width
        self.ADDRESS_WIDTH.append(int(args[-1].split()[1]))  # main memory address width
        self.BYTE_SIZE = 8

    def generate_module(self) -> Module:
        m = Module("cache_wrapper")

        caches = []

        for i in range(self.NUM_CACHES):
            caches.append(
                CacheGenerator(
                    address_width=self.ADDRESS_WIDTH[i],
                    data_width=self.DATA_WIDTH[i],
                    num_ways=self.NUM_WAYS[i],
                    num_sets=self.NUM_SETS[i],
                    replacement_policy=self.REPLACEMENT_POLICY[i],
                    hit_latency=self.HIT_LATENCY[i],
                    miss_latency=self.MISS_LATENCY[i],
                    write_through=self.WRITE_THROUGH[i],
                    write_allocate=self.WRITE_ALLOCATE[i],
                    block_size=self.BLOCK_SIZE[i],
                    prefix=f"l{i+1}_",
                    be_address_width=self.ADDRESS_WIDTH[i + 1],
                    be_data_width=self.DATA_WIDTH[i + 1],
                ).generate_module()
            )

        memory = FunctionalMemoryGenerator(
            data_width=self.DATA_WIDTH[-1], address_width=self.ADDRESS_WIDTH[-1]
        ).generate_module()

        # Common Inputs
        clk_i = m.Input("clk_i")
        reset_n_i = m.Input("reset_n_i")
        flush_i = m.Input("flush_i")
        # Output the cache hit status of the l1 cache
        hit_o = m.Output("hit_o")
        # L1 Cache will always be written to with whole words
        l1_write_strobe = m.Wire(
            "l1_write_strobe", self.DATA_WIDTH[0] // self.BYTE_SIZE
        )
        m.Assign(l1_write_strobe((2 ** (self.DATA_WIDTH[0] // self.BYTE_SIZE)) - 1))

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
            address_i.append(m.Input(f"address_{i}_i", self.ADDRESS_WIDTH[0]))
            address_valid_i.append(m.Input(f"address_valid_{i}_i"))
            write_data_i.append(m.Input(f"write_data_{i}_i", self.DATA_WIDTH[0]))
            write_data_valid_i.append(m.Input(f"write_data_valid_{i}_i"))
            read_write_select_i.append(m.Input(f"read_write_select_{i}_i"))
            read_data_o.append(m.Output(f"read_data_{i}_o", self.DATA_WIDTH[0]))
            read_data_valid_o.append(m.Output(f"read_data_valid_{i}_o"))
            write_done_o.append(m.Output(f"write_done_{i}_o"))
            port_ready_o.append(m.Output(f"port_ready_{i}_o"))

        # hit signal is purely for testing atm
        request_hit = []
        # Cache Backend <- Next level memory
        be_read_data = []
        be_read_data_valid = []
        be_write_done = []
        be_port_ready = []

        # Cache Backend -> Next level memory
        be_address = []
        be_address_valid = []
        be_write_data = []
        be_write_data_valid = []
        be_read_write_select = []
        be_write_strobe = []

        for i in range(self.NUM_CACHES):
            request_hit.append(m.Wire(f"request_hit_{i}"))
            be_read_data.append(m.Wire(f"be_read_data_{i}", self.DATA_WIDTH[i + 1]))
            be_read_data_valid.append(m.Wire(f"be_read_data_valid_{i}"))
            be_write_done.append(m.Wire(f"be_write_done_{i}"))
            be_port_ready.append(m.Wire(f"be_port_ready_{i}"))
            be_address.append(m.Wire(f"be_address_{i}", self.ADDRESS_WIDTH[i + 1]))
            be_address_valid.append(m.Wire(f"be_address_valid_{i}"))
            be_write_data.append(m.Wire(f"be_write_data_{i}", self.DATA_WIDTH[i + 1]))
            be_write_data_valid.append(m.Wire(f"be_write_data_valid_{i}"))
            be_read_write_select.append(m.Wire(f"be_read_write_select_{i}"))
            be_write_strobe.append(
                m.Wire(f"be_write_strobe_{i}", self.DATA_WIDTH[i + 1] // self.BYTE_SIZE)
            )

        # Assign the hit status of the l1 cache
        m.Assign(hit_o(request_hit[0]))

        if self.NUM_PORTS == 1:
            # first level cache connected to frontend ports
            Submodule(
                m,
                caches[0],
                "l1_cache",
                arg_ports=(
                    # Common
                    ("clk_i", clk_i),
                    ("reset_n_i", reset_n_i),
                    ("flush_i", flush_i),
                    # Hit signal
                    ("fe_hit_o", request_hit[0]),
                    # Cache In
                    ("fe_address_i", address_i[0]),
                    ("fe_address_valid_i", address_valid_i[0]),
                    ("fe_write_data_i", write_data_i[0]),
                    ("fe_write_data_valid_i", write_data_valid_i[0]),
                    ("fe_read_write_select_i", read_write_select_i[0]),
                    ("fe_write_strobe_i", l1_write_strobe),
                    # Cache Out
                    ("fe_read_data_o", read_data_o[0]),
                    ("fe_read_data_valid_o", read_data_valid_o[0]),
                    ("fe_write_done_o", write_done_o[0]),
                    ("fe_port_ready_o", port_ready_o[0]),
                    # Backend Cache <- Memory
                    ("be_read_data_i", be_read_data[0]),
                    ("be_read_data_valid_i", be_read_data_valid[0]),
                    ("be_write_done_i", be_write_done[0]),
                    ("be_port_ready_i", be_port_ready[0]),
                    # Backend Cache -> Memory
                    ("be_address_o", be_address[0]),
                    ("be_address_valid_o", be_address_valid[0]),
                    ("be_write_data_o", be_write_data[0]),
                    ("be_write_data_valid_o", be_write_data_valid[0]),
                    ("be_read_write_select_o", be_read_write_select[0]),
                    ("be_write_strobe_o", be_write_strobe[0])
                ),
            )
        else:
            # arbiter -> cache
            arbiter_address = m.Wire("arbiter_address", self.ADDRESS_WIDTH[0])
            arbiter_address_valid = m.Wire("arbiter_address_valid")
            arbiter_write_data = m.Wire("arbiter_write_data", self.DATA_WIDTH[0])
            arbiter_write_data_valid = m.Wire("arbiter_write_data_valid")
            arbiter_read_write_select = m.Wire("arbiter_read_write_select")
            # arbiter <- cache
            arbiter_port_ready = m.Wire("arbiter_port_ready")
            arbiter_read_data = m.Wire("arbiter_read_data", self.DATA_WIDTH[0])
            arbiter_read_data_valid = m.Wire("arbiter_read_data_valid")
            arbiter_write_done = m.Wire("arbiter_write_done")

            arbiter = MemoryAccessArbiter(
                num_ports=self.NUM_PORTS,
                address_width=self.ADDRESS_WIDTH[0],
                data_width=self.DATA_WIDTH[0],
                policy=self.ARBITER_POLICY,
            ).generate_module()

            arbiter_port_mapping = [
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
            ]
            for i in range(self.NUM_PORTS):
                arbiter_port_mapping.extend(
                    [
                        (f"fe_address_{i}_i", address_i[i]),
                        (f"fe_address_valid_{i}_i", address_valid_i[i]),
                        (f"fe_write_data_{i}_i", write_data_i[i]),
                        (f"fe_write_data_valid_{i}_i", write_data_valid_i[i]),
                        (f"fe_read_write_select_{i}_i", read_write_select_i[i]),
                        (f"fe_read_data_{i}_o", read_data_o[i]),
                        (f"fe_read_data_valid_{i}_o", read_data_valid_o[i]),
                        (f"fe_write_done_{i}_o", write_done_o[i]),
                        (f"fe_port_ready_{i}_o", port_ready_o[i]),
                    ]
                )
            Submodule(m, arbiter, "arbiter", arg_ports=arbiter_port_mapping)
            # first level cache connected to arbiter
            Submodule(
                m,
                caches[0],
                "l1_cache",
                arg_ports=(
                    # Common
                    ("clk_i", clk_i),
                    ("reset_n_i", reset_n_i),
                    ("flush_i", flush_i),
                    # Hit signal
                    ("fe_hit_o", request_hit[0]),
                    # Cache In
                    ("fe_address_i", arbiter_address),
                    ("fe_address_valid_i", arbiter_address_valid),
                    ("fe_write_data_i", arbiter_write_data),
                    ("fe_write_data_valid_i", arbiter_write_data_valid),
                    ("fe_read_write_select_i", arbiter_read_write_select),
                    ("fe_write_strobe_i", l1_write_strobe),
                    # Cache Out
                    ("fe_read_data_o", arbiter_read_data),
                    ("fe_read_data_valid_o", arbiter_read_data_valid),
                    ("fe_write_done_o", arbiter_write_done),
                    ("fe_port_ready_o", arbiter_port_ready),
                    # Backend Cache <- Memory
                    ("be_read_data_i", be_read_data[0]),
                    ("be_read_data_valid_i", be_read_data_valid[0]),
                    ("be_write_done_i", be_write_done[0]),
                    ("be_port_ready_i", be_port_ready[0]),
                    # Backend Cache -> Memory
                    ("be_address_o", be_address[0]),
                    ("be_address_valid_o", be_address_valid[0]),
                    ("be_write_data_o", be_write_data[0]),
                    ("be_write_data_valid_o", be_write_data_valid[0]),
                    ("be_read_write_select_o", be_read_write_select[0]),
                    ("be_write_strobe_o", be_write_strobe[0])
                ),
            )

        # all other caches
        for i in range(1, self.NUM_CACHES):
            Submodule(
                m,
                caches[i],
                f"l{i+1}_cache",
                arg_ports=(
                    # Common
                    ("clk_i", clk_i),
                    ("reset_n_i", reset_n_i),
                    ("flush_i", flush_i),
                    # Hit signal
                    ("fe_hit_o", request_hit[i]),
                    # Cache In
                    ("fe_address_i", be_address[i - 1]),
                    ("fe_address_valid_i", be_address_valid[i - 1]),
                    ("fe_write_data_i", be_write_data[i - 1]),
                    ("fe_write_data_valid_i", be_write_data_valid[i - 1]),
                    ("fe_read_write_select_i", be_read_write_select[i - 1]),
                    ("fe_write_strobe_i", be_write_strobe[i - 1]),
                    # Cache Out
                    ("fe_read_data_o", be_read_data[i - 1]),
                    ("fe_read_data_valid_o", be_read_data_valid[i - 1]),
                    ("fe_write_done_o", be_write_done[i - 1]),
                    ("fe_port_ready_o", be_port_ready[i - 1]),
                    # Cache Backend <- Memory
                    ("be_read_data_i", be_read_data[i]),
                    ("be_read_data_valid_i", be_read_data_valid[i]),
                    ("be_write_done_i", be_write_done[i]),
                    ("be_port_ready_i", be_port_ready[i]),
                    # Cache Backend -> Memory
                    ("be_address_o", be_address[i]),
                    ("be_address_valid_o", be_address_valid[i]),
                    ("be_write_data_o", be_write_data[i]),
                    ("be_write_data_valid_o", be_write_data_valid[i]),
                    ("be_read_write_select_o", be_read_write_select[i]),
                    ("be_write_strobe_o", be_write_strobe[i]),
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
                # Cache Backend <- Memory
                ("read_data_o", be_read_data[-1]),
                ("read_data_valid_o", be_read_data_valid[-1]),
                ("write_done_o", be_write_done[-1]),
                ("port_ready_o", be_port_ready[-1]),
                # Cache Backend -> Memory
                ("address_i", be_address[-1]),
                ("address_valid_i", be_address_valid[-1]),
                ("write_data_i", be_write_data[-1]),
                ("write_data_valid_i", be_write_data_valid[-1]),
                ("read_write_select_i", be_read_write_select[-1]),
                ("write_strobe_i", be_write_strobe[-1])
            ),
        )
        return m


if __name__ == "__main__":
    # argv: (file name), number for output file suffix, num ports, arbiter policy, [data width, address width, num ways, num sets, replacement policy, hit latency, miss latency, write through, write allocate, block size]... [main memory data width, main memory address width]
    cache_wrapper_generator = CacheWrapperGenerator(*sys.argv[2:])
    m = cache_wrapper_generator.generate_module()
    m.to_verilog(f"../src/cache_wrapper_{sys.argv[1]}.v", for_verilator=True)
