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

from acaverilog.generators.cache_generator import CacheGenerator
from acaverilog.generators.functional_memory_generator import FunctionalMemoryGenerator


class CacheWrapperGenerator:
    def generate_module(self) -> Module:
        DATA_WIDTH = 16
        ADDRESS_WIDTH = 8
        m = Module("cache_wrapper")
        cache = CacheGenerator(
            data_width=DATA_WIDTH, address_width=ADDRESS_WIDTH
        ).generate_module()
        memory = FunctionalMemoryGenerator(
            data_width=DATA_WIDTH, address_width=ADDRESS_WIDTH
        ).generate_module()

        # Common Inputs
        clk_i = m.Input("clk_i")
        reset_n_i = m.Input("reset_n_i")

        # Cache Inputs
        address_i = m.Input("address_i", ADDRESS_WIDTH)
        address_valid_i = m.Input("address_valid_i")
        write_data_i = m.Input("write_data_i", DATA_WIDTH)
        write_data_valid_i = m.Input("write_data_valid_i")
        read_write_select_i = m.Input("read_write_select_i")

        # Cache Outputs
        read_data_o = m.Output("read_data_o", DATA_WIDTH)
        read_data_valid_o = m.Output("read_data_valid_o")
        write_done_o = m.Output("write_done_o")
        port_ready_o = m.Output("port_ready_o")
        hit_o = m.Output("hit_o")

        # Backend Cache <- Memory
        be_read_data = m.Wire("be_read_data", DATA_WIDTH)
        be_read_data_valid = m.Wire("be_read_data_valid")
        be_write_done = m.Wire("be_write_done")
        be_port_ready = m.Wire("be_port_ready")

        # Backend Cache -> Memory
        be_address = m.Wire("be_address", ADDRESS_WIDTH)
        be_address_valid = m.Wire("be_address_valid")
        be_write_data = m.Wire("be_write_data", DATA_WIDTH)
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
    cache_wrapper_generator = CacheWrapperGenerator()
    m = cache_wrapper_generator.generate_module()
    m.to_verilog("../src/cache_wrapper.v", for_verilator=True)
