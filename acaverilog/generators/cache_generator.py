from math import ceil, log2
from veriloggen import Module, Submodule, Posedge, Negedge, If, For, AndList

from acadl import ACADLObject

from .acadl_object_generator import ACADLObjectGenerator


class ExecuteStageGenerator(ACADLObjectGenerator):

    def __init__(
        self,
        acadl_object: ACADLObject,
    ) -> None:
        super().__init__(acadl_object)

    def generate_module(self) -> Module:
        m = Module(self.base_file_name)

        # Parameters
        DATA_WIDTH = m.Parameter("DATA_WIDTH", 32)
        ADDRESS_WIDTH = m.Parameter("ADDRESS_WIDTH", 16)
        NUM_SETS = m.Parameter("NUM_SETS", 4)
        HIT_LATENCY = m.Parameter("HIT_LATENCY", 4)
        MISS_LATENCY = m.Parameter("MISS_LATENCY", 2)

        # Local Parameters
        READ_LATENCY_COUNTER_SIZE = m.Localparam(
            "LATENCY_COUNTER_SIZE",
            ceil(log2(self.acadl_object.read_latency.int_latency)),
        )
        WRITE_LATENCY_COUNTER_SIZE = m.Localparam(
            "LATENCY_COUNTER_SIZE",
            ceil(log2(self.acadl_object.write_latency.int_latency)),
        )

        # Front End Inputs
        clk_i = m.Input("clk_i")
        reset_n_i = m.Input("reset_n_i")
        address_i = m.Input("address_i", ADDRESS_WIDTH)
        address_valid_i = m.Input("address_valid_i")
        write_data_i = m.Input("write_data_i", DATA_WIDTH)
        write_data_valid_i = m.Input("write_data_valid_i")
        read_write_select_i = m.Input("read_write_select_i")

        # Front End Outputs
        read_data_o = m.Output("read_data_o", DATA_WIDTH)
        read_data_valid_o = m.Output("read_data_valid_o")
        write_done_o = m.Output("write_done_o")
        port_ready_o = m.Output("port_ready_o")

        # Back End Inputs
        read_data_i = m.Input("read_data_i", DATA_WIDTH)
        read_data_valid_i = m.Input("read_data_valid_i")
        write_done_i = m.Input("write_done_i")
        port_ready_i = m.Input("port_ready_i")

        # Back End Outputs
        address_o = m.Output("address_o", ADDRESS_WIDTH)
        address_valid_o = m.Output("address_valid_o")
        write_data_o = m.Output("write_data_o", DATA_WIDTH)
        write_data_valid_o = m.Output("write_data_valid_o")
        read_write_select_o = m.Input("read_write_select_o")

        # Front End Input Buffers
        address_i_reg = m.Reg("address_i_reg", ADDRESS_WIDTH)
        address_valid_i_reg = m.Reg("address_valid_i_reg")
        write_data_i_reg = m.Reg("write_data_i_reg", DATA_WIDTH)
        write_data_valid_i_reg = m.Reg("write_data_valid_i_reg")
        read_write_select_i_reg = m.Reg("read_write_select_i_reg")

        # Front End Output Buffers
        read_data_o_reg = m.Reg("read_data_o_reg", DATA_WIDTH)
        read_data_valid_o_reg = m.Reg("read_data_valid_o_reg")
        write_done_o_reg = m.Reg("write_done_o_reg")
        port_ready_o_reg = m.Reg("port_ready_o_reg")

        # Back End Input Buffers
        read_data_i_reg = m.Reg("read_data_i_reg", DATA_WIDTH)
        read_data_valid_i_reg = m.Reg("read_data_valid_i_reg")
        write_done_i_reg = m.Reg("write_done_i_reg")
        port_ready_i_reg = m.Reg("port_ready_i_reg")

        # Back End Output Buffers
        address_o_reg = m.Output("address_o_reg", ADDRESS_WIDTH)
        address_valid_o_reg = m.Output("address_valid_o_reg")
        write_data_o_reg = m.Output("write_data_o_reg", DATA_WIDTH)
        write_data_valid_o_reg = m.Output("write_data_valid_o_reg")
        read_write_select_o_reg = m.Input("read_write_select_o_reg")

        # Frontend Output Buffer Assignments
        m.Assign(read_data_o(read_data_o_reg))
        m.Assign(read_data_valid_o(read_data_valid_o_reg))
        m.Assign(write_done_o(write_done_o_reg))
        m.Assign(port_ready_o(port_ready_o_reg))

        # Backend Output Buffer Assignments
        m.Assign(address_o(address_o_reg))
        m.Assign(address_valid_o(address_valid_o_reg))
        m.Assign(write_data_o(write_data_o_reg))
        m.Assign(write_data_valid_o(write_data_valid_o_reg))
        m.Assign(read_write_select_o(read_write_select_o_reg))

        # Internal
        read_latency_counter = m.Reg("read_latency_counter", READ_LATENCY_COUNTER_SIZE)
        write_latency_counter = m.Reg(
            "write_latency_counter", WRITE_LATENCY_COUNTER_SIZE
        )
        read_in_progress = m.Reg("read_in_progress")
        write_in_progress = m.Reg("write_in_progress")
        tag_memory = m.Reg('tag_memory', ...)
        m.Assign(
            port_ready_o_reg(AndList(read_in_progress == 0, write_in_progress == 0))
        )
