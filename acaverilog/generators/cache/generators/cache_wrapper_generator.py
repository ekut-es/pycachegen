from math import log2
from veriloggen import (
    Module,
    Submodule,
)

from acaverilog.generators.cache.generators.cache_generator import CacheGenerator
from acaverilog.generators.cache.generators.functional_memory_generator import (
    FunctionalMemoryGenerator,
)
from acaverilog.generators.cache.generators.memory_access_arbiter import (
    MemoryAccessArbiter,
)
from acaverilog.generators.cache.cache_config_validation import (
    CacheConfig,
    MemoryConfig,
    InternalCacheConfig,
    InternalMemoryConfig,
)


class CacheWrapperGenerator:
    """Generates a top level module containing one ore more caches and a main memory.
    There can also be an arbiter infront of the L1 cache. The caches are set up in a linear
    hierarchy.
    """

    def __init__(
        self,
        num_ports: int,
        arbiter_policy: str,
        byte_size: int,
        enable_reset: bool,
        address_width: int,
        memory_config: MemoryConfig,
        *cache_configs: CacheConfig,
    ) -> None:
        self.NUM_PORTS = num_ports
        self.ARBITER_POLICY = arbiter_policy
        self.BYTE_SIZE = byte_size
        self.ENABLE_RESET = enable_reset
        self.ADDRESS_WIDTH = address_width
        self.NUM_CACHES = len(cache_configs)

        self.CACHE_CONFIGS: list[InternalCacheConfig] = []
        for i in range(len(cache_configs)):
            config = cache_configs[i]
            address_width = self.ADDRESS_WIDTH - int(
                log2(config.DATA_WIDTH // self.BYTE_SIZE)
            )
            if i < len(cache_configs) - 1:
                be_data_width = cache_configs[i + 1].DATA_WIDTH
            else:
                be_data_width = memory_config.DATA_WIDTH
            be_address_width = self.ADDRESS_WIDTH - int(
                log2(be_data_width // self.BYTE_SIZE)
            )
            self.CACHE_CONFIGS.append(
                InternalCacheConfig(
                    cache_config=config,
                    address_width=address_width,
                    be_data_width=be_data_width,
                    be_address_width=be_address_width,
                    byte_size=self.BYTE_SIZE,
                    prefix=f"l{i+1}_",
                    enable_reset=self.ENABLE_RESET,
                )
            )

        memory_address_width = self.ADDRESS_WIDTH - int(
            log2(memory_config.DATA_WIDTH // self.BYTE_SIZE)
        )
        self.MEMORY_CONFIG = InternalMemoryConfig(
            memory_config=memory_config,
            address_width=memory_address_width,
            byte_size=self.BYTE_SIZE,
            enable_reset=self.ENABLE_RESET,
        )

        if self.NUM_CACHES > 0:
            self.FE_DATA_WIDTH = self.CACHE_CONFIGS[0].DATA_WIDTH
            self.FE_ADDRESS_WIDTH = self.CACHE_CONFIGS[0].ADDRESS_WIDTH
        else:
            self.FE_DATA_WIDTH = self.MEMORY_CONFIG.DATA_WIDTH
            self.FE_ADDRESS_WIDTH = self.MEMORY_CONFIG.ADDRESS_WIDTH

    def generate_module(self) -> Module:
        m = Module("cache_wrapper")

        ## Create the Caches if there are any

        caches = []
        for i in range(self.NUM_CACHES):
            caches.append(
                CacheGenerator(
                    config=self.CACHE_CONFIGS[i],
                ).generate_module()
            )

        ## Create the Memory
        memory = FunctionalMemoryGenerator(config=self.MEMORY_CONFIG).generate_module()

        # Common Inputs
        clk_i = m.Input("clk_i")
        reset_n_i = m.Input("reset_n_i")
        # Ports that do not need to be arbitrated and are only for the l1 cache
        flush_i = m.Input("flush_i")
        flush_done_o = m.Output("flush_done_o")
        hit_o = m.Output("hit_o")

        ## Create Ports for the very front end (potentially the interface to the arbiter)
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
            address_i.append(m.Input(f"address_{i}_i", self.FE_ADDRESS_WIDTH))
            address_valid_i.append(m.Input(f"address_valid_{i}_i"))
            write_data_i.append(m.Input(f"write_data_{i}_i", self.FE_DATA_WIDTH))
            write_data_valid_i.append(m.Input(f"write_data_valid_{i}_i"))
            read_write_select_i.append(m.Input(f"read_write_select_{i}_i"))
            read_data_o.append(m.Output(f"read_data_{i}_o", self.FE_DATA_WIDTH))
            read_data_valid_o.append(m.Output(f"read_data_valid_{i}_o"))
            write_done_o.append(m.Output(f"write_done_{i}_o"))
            port_ready_o.append(m.Output(f"port_ready_{i}_o"))

        ## Create the interfaces between the caches and between the last cache and the memory
        # hit signal is purely for testing atm
        request_hit = []
        # Cache Backend <- Next level memory
        be_read_data = []
        be_read_data_valid = []
        be_write_done = []
        be_port_ready = []
        be_flush_done = []
        # Cache Backend -> Next level memory
        be_address = []
        be_address_valid = []
        be_write_data = []
        be_write_data_valid = []
        be_read_write_select = []
        be_write_strobe = []
        be_flush = []

        for i in range(self.NUM_CACHES):
            request_hit.append(m.Wire(f"request_hit_{i}"))
            be_read_data.append(
                m.Wire(f"be_read_data_{i}", self.CACHE_CONFIGS[i].BE_DATA_WIDTH)
            )
            be_read_data_valid.append(m.Wire(f"be_read_data_valid_{i}"))
            be_write_done.append(m.Wire(f"be_write_done_{i}"))
            be_port_ready.append(m.Wire(f"be_port_ready_{i}"))
            be_flush_done.append(m.Wire(f"be_flush_done_{i}"))
            be_address.append(
                m.Wire(f"be_address_{i}", self.CACHE_CONFIGS[i].BE_ADDRESS_WIDTH)
            )
            be_address_valid.append(m.Wire(f"be_address_valid_{i}"))
            be_write_data.append(
                m.Wire(f"be_write_data_{i}", self.CACHE_CONFIGS[i].BE_DATA_WIDTH)
            )
            be_write_data_valid.append(m.Wire(f"be_write_data_valid_{i}"))
            be_read_write_select.append(m.Wire(f"be_read_write_select_{i}"))
            be_write_strobe.append(
                m.Wire(
                    f"be_write_strobe_{i}",
                    self.CACHE_CONFIGS[i].BE_DATA_WIDTH // self.BYTE_SIZE,
                )
            )
            be_flush.append(m.Wire(f"be_flush_{i}"))

        # Assign the hit status of the l1 cache if there is one
        if self.NUM_CACHES > 0:
            m.Assign(hit_o(request_hit[0]))
        else:
            m.Assign(hit_o(0))

        ## Create the interface for the ports of the L1 cache (or the memory if there are no caches)
        l1_address = m.Wire(f"l1_address", self.FE_ADDRESS_WIDTH)
        l1_address_valid = m.Wire(f"l1_address_valid")
        l1_write_data = m.Wire(f"l1_write_data", self.FE_DATA_WIDTH)
        l1_write_data_valid = m.Wire(f"l1_write_data_valid")
        l1_read_write_select = m.Wire(f"l1_read_write_select")
        l1_read_data = m.Wire(f"l1_read_data", self.FE_DATA_WIDTH)
        l1_read_data_valid = m.Wire(f"l1_read_data_valid")
        l1_write_done = m.Wire(f"l1_write_done")
        l1_port_ready = m.Wire(f"l1_port_ready")
        l1_write_strobe = m.Wire(
            "l1_write_strobe", self.FE_DATA_WIDTH // self.BYTE_SIZE
        )
        m.Assign(
            l1_write_strobe((2 ** (self.FE_DATA_WIDTH // self.BYTE_SIZE)) - 1)
        )  # FE will always do word operations
        # so we can just assign all ones here

        if self.NUM_PORTS > 1:
            ## Create an arbiter
            arbiter = MemoryAccessArbiter(
                num_ports=self.NUM_PORTS,
                address_width=self.FE_ADDRESS_WIDTH,
                data_width=self.FE_DATA_WIDTH,
                policy=self.ARBITER_POLICY,
                enable_reset=self.ENABLE_RESET,
            ).generate_module()

            arbiter_port_mapping = [
                ("clk_i", clk_i),
                ("reset_n_i", reset_n_i),
                ("be_port_ready_i", l1_port_ready),
                ("be_read_data_i", l1_read_data),
                ("be_read_data_valid_i", l1_read_data_valid),
                ("be_write_done_i", l1_write_done),
                ("be_address_o", l1_address),
                ("be_address_valid_o", l1_address_valid),
                ("be_write_data_o", l1_write_data),
                ("be_write_data_valid_o", l1_write_data_valid),
                ("be_read_write_select_o", l1_read_write_select),
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
        else:
            ## Directly connect the L1 interface wires to the in-/outputs
            m.Assign(l1_address(address_i[0]))
            m.Assign(l1_address_valid(address_valid_i[0]))
            m.Assign(l1_write_data(write_data_i[0]))
            m.Assign(l1_write_data_valid(write_data_valid_i[0]))
            m.Assign(l1_read_write_select(read_write_select_i[0]))
            m.Assign(read_data_o[0](l1_read_data))
            m.Assign(read_data_valid_o[0](l1_read_data_valid))
            m.Assign(write_done_o[0](l1_write_done))
            m.Assign(port_ready_o[0](l1_port_ready))

        ## Use the L1 interface wires for the very first cache/memory
        be_read_data.insert(0, l1_read_data)
        be_read_data_valid.insert(0, l1_read_data_valid)
        be_write_done.insert(0, l1_write_done)
        be_port_ready.insert(0, l1_port_ready)
        be_flush_done.insert(0, flush_done_o)
        be_address.insert(0, l1_address)
        be_address_valid.insert(0, l1_address_valid)
        be_write_data.insert(0, l1_write_data)
        be_write_data_valid.insert(0, l1_write_data_valid)
        be_read_write_select.insert(0, l1_read_write_select)
        be_write_strobe.insert(0, l1_write_strobe)
        be_flush.insert(0, flush_i)

        # Assign 1 to the last flush done because the memory doesn't need a flush
        m.Assign(be_flush_done[-1](1))

        ## Connect all caches
        for i in range(self.NUM_CACHES):
            Submodule(
                m,
                caches[i],
                f"l{i+1}_cache",
                arg_ports=(
                    # Common
                    ("clk_i", clk_i),
                    ("reset_n_i", reset_n_i),
                    # Cache In
                    ("fe_flush_i", be_flush[i]),
                    ("fe_address_i", be_address[i]),
                    ("fe_address_valid_i", be_address_valid[i]),
                    ("fe_write_data_i", be_write_data[i]),
                    ("fe_write_data_valid_i", be_write_data_valid[i]),
                    ("fe_read_write_select_i", be_read_write_select[i]),
                    ("fe_write_strobe_i", be_write_strobe[i]),
                    # Cache Out
                    ("fe_flush_done_o", be_flush_done[i]),
                    ("fe_read_data_o", be_read_data[i]),
                    ("fe_read_data_valid_o", be_read_data_valid[i]),
                    ("fe_write_done_o", be_write_done[i]),
                    ("fe_port_ready_o", be_port_ready[i]),
                    ("fe_hit_o", request_hit[i]),
                    # Cache Backend <- Memory
                    ("be_flush_done_i", be_flush_done[i + 1]),
                    ("be_read_data_i", be_read_data[i + 1]),
                    ("be_read_data_valid_i", be_read_data_valid[i + 1]),
                    ("be_write_done_i", be_write_done[i + 1]),
                    ("be_port_ready_i", be_port_ready[i + 1]),
                    # Cache Backend -> Memory
                    ("be_flush_o", be_flush[i + 1]),
                    ("be_address_o", be_address[i + 1]),
                    ("be_address_valid_o", be_address_valid[i + 1]),
                    ("be_write_data_o", be_write_data[i + 1]),
                    ("be_write_data_valid_o", be_write_data_valid[i + 1]),
                    ("be_read_write_select_o", be_read_write_select[i + 1]),
                    ("be_write_strobe_o", be_write_strobe[i + 1]),
                ),
            )

        # The memory gets the last in-/outputs
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
                ("write_strobe_i", be_write_strobe[-1]),
            ),
        )

        return m
