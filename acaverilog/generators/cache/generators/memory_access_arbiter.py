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
    Or,
    And,
)
from enum import Enum
from math import ceil, log2

from acaverilog.generators.cache.generators.priority_encoder_generator import (
    PriorityEncoderGenerator,
)


class States(Enum):
    READY = 1
    WAITING_FOR_MEMORY = 2


class MemoryAccessArbiter:
    def __init__(self, num_ports, address_width, data_width) -> None:
        self.NUM_PORTS = num_ports
        self.ADDRESS_WIDTH = address_width
        self.DATA_WIDTH = data_width

    def generate_module(self) -> Module:
        m = Module("memory_access_arbiter")

        clk_i = m.Input("clk_i")
        reset_n_i = m.Input("reset_n_i")

        ## backend
        # inputs
        be_port_ready_i = m.Input("be_port_ready_i")
        be_read_data_i = m.Input("be_read_data_i", self.DATA_WIDTH)
        be_read_data_valid_i = m.Input("be_read_data_valid_i")
        be_write_done_i = m.Input("be_write_done_i")
        # outputs
        be_address_o = m.Output("be_address_o", self.ADDRESS_WIDTH)
        be_address_valid_o = m.Output("be_address_valid_o")
        be_write_data_o = m.Output("be_write_data_o", self.DATA_WIDTH)
        be_write_data_valid_o = m.Output("be_write_data_valid_o")
        be_read_write_select_o = m.Output("be_read_write_select_o")
        # output buffers
        be_address = m.Reg("be_address", self.ADDRESS_WIDTH)
        be_address_valid = m.Reg("be_address_valid")
        be_write_data = m.Reg("be_write_data", self.DATA_WIDTH)
        be_write_data_valid = m.Reg("be_write_data_valid")
        be_read_write_select = m.Reg("be_read_write_select")
        # output buffer assignments
        m.Assign(be_address(be_address_o))
        m.Assign(be_address_valid(be_address_valid_o))
        m.Assign(be_write_data(be_write_data_o))
        m.Assign(be_write_data_valid(be_write_data_valid_o))
        m.Assign(be_read_write_select(be_read_write_select_o))

        ## frontend
        # inputs
        fe_address_i = []
        fe_address_valid_i = []
        fe_write_data_i = []
        fe_write_data_valid_i = []
        fe_read_write_select_i = []
        # outputs
        fe_read_data_o = []
        fe_read_data_valid_o = []
        fe_write_done_o = []
        fe_port_ready_o = []
        # input buffers
        fe_address = []
        fe_address_valid = []
        fe_write_data = []
        fe_write_data_valid = []
        fe_read_write_select = []
        # output buffers
        fe_read_data = []
        fe_read_data_valid = []
        fe_write_done = []
        fe_port_ready = []
        for i in range(self.NUM_PORTS):
            fe_address_i.append(m.Input(f"fe_address_{i}_i", self.ADDRESS_WIDTH))
            fe_address_valid_i.append(m.Input(f"fe_address_valid_{i}_i"))
            fe_write_data_i.append(m.Input(f"fe_write_data_{i}_i", self.DATA_WIDTH))
            fe_write_data_valid_i.append(m.Input(f"fe_write_data_valid_{i}_i"))
            fe_read_write_select_i.append(m.Input(f"fe_read_write_select_{i}_i"))
            # outputs
            fe_read_data_o.append(m.Output(f"fe_read_data_{i}_o", self.DATA_WIDTH))
            fe_read_data_valid_o.append(m.Output(f"fe_read_data_valid_{i}_o"))
            fe_write_done_o.append(m.Output(f"fe_write_done_{i}_o"))
            fe_port_ready_o.append(m.Output(f"fe_port_ready_{i}_o"))
            # input buffers
            fe_address.append(m.Reg(f"fe_address_{i}", self.ADDRESS_WIDTH))
            fe_address_valid.append(m.Reg(f"fe_address_valid_{i}"))
            fe_write_data.append(m.Reg(f"fe_write_data_{i}", self.DATA_WIDTH))
            fe_write_data_valid.append(m.Reg(f"fe_write_data_valid_{i}"))
            fe_read_write_select.append(m.Reg(f"fe_read_write_select_{i}"))
            # output buffers
            fe_read_data.append(m.Reg(f"fe_read_data_{i}", self.DATA_WIDTH))
            fe_read_data_valid.append(m.Reg(f"fe_read_data_valid_{i}"))
            fe_write_done.append(m.Reg(f"fe_write_done_{i}"))
            fe_port_ready.append(m.Reg(f"fe_port_ready_{i}"))
            # output buffer assignments
            m.Assign(fe_read_data_o[i](fe_read_data[i]))
            m.Assign(fe_read_data_valid_o[i](fe_read_data_valid[i]))
            m.Assign(fe_write_done_o[i](fe_write_done[i]))
            m.Assign(fe_port_ready_o[i](fe_port_ready[i]))

        # internal
        request_valid = m.Wire("request_valid", self.NUM_PORTS)
        for i in range(self.NUM_PORTS):
            m.Assign(
                request_valid[i](
                    And(
                        fe_address_valid[i],
                        Or(Not(fe_read_write_select[i]), fe_write_data_valid[i]),
                    )
                )
            )
        next_request = m.Wire("next_request")
        enable_encoder = m.Reg("enable_encoder")
        state_reg = m.Reg("state_reg", ceil(log2(len(States))))
        selected_request = m.Reg("selected_request", ceil(log2(self.NUM_PORTS)))

        Submodule(
            m,
            PriorityEncoderGenerator(self.NUM_PORTS).generate_module(),
            "arbiter_priority_encoder",
            arg_ports=(
                ("clk_i", clk_i),
                ("reset_n_i", reset_n_i),
                ("unencoded_i", request_valid),
                ("encoded_o", next_request),
                ("enable_i", enable_encoder),
            ),
        )

        m.Always(Posedge(clk_i), Negedge(reset_n_i))(
            If(Not(reset_n_i))(
                # backend buffers
                be_address(0),
                be_address_valid(0),
                be_write_data(0),
                be_write_data_valid(0),
                # frontend buffers
                [
                    (
                        fe_address[i](0),
                        fe_address_valid[i](0),
                        fe_write_data[i](0),
                        fe_write_data_valid[i](0),
                        fe_read_write_select[i](0),
                        fe_read_data[i](0),
                        fe_read_data_valid[i](0),
                        fe_write_done[i](0),
                        fe_port_ready[i](1),
                    )
                    for i in range(self.NUM_PORTS)
                ],
                # internal
                enable_encoder(1),
                state_reg(States.READY.value),
                selected_request(0),
            ).Else(
                # Always buffer new requests
                [
                    If(And(fe_port_ready[i], request_valid[i]))(
                        fe_port_ready[i](0),
                        fe_address[i](fe_address_i[i]),
                        fe_address_valid[i](1),
                        fe_write_data[i](fe_write_data_i[i]),
                        fe_write_data_valid[i](fe_write_data_valid_i[i]),
                        fe_read_write_select[i](fe_read_write_select_i[i]),
                        fe_read_data_valid[i](0),
                        fe_write_done[i](0),
                    )
                    for i in range(self.NUM_PORTS)
                ],
                If(
                    AndList(
                        state_reg == States.READY.value,
                        be_port_ready_i,
                        request_valid != 0,
                    )
                )(
                    [
                        If(i == next_request)(
                            be_address(fe_address[i]),
                            be_write_data(fe_write_data[i]),
                            be_write_data_valid(fe_write_data_valid[i]),
                            be_read_write_select(fe_read_write_select[i]),
                        )
                        for i in range(self.NUM_PORTS)
                    ],
                    be_address_valid(1),
                    state_reg(States.WAITING_FOR_MEMORY.value),
                ).Elif(
                    state_reg == States.WAITING_FOR_MEMORY.value
                )(
                    If(be_address_valid)(
                        # invalidate the request
                        be_address_valid(0),
                        be_write_data_valid(0),
                    ).Elif(be_port_ready_i)
                )(
                    state_reg(States.READY.value),
                    [
                        If(i == selected_request)(
                            fe_port_ready[i](1),
                            If((And(be_read_write_select, be_write_done_i)))(
                                # write done
                                fe_write_done[i](1),
                            ).Elif(
                                And(Not(be_read_write_select), be_read_data_valid_i)
                            )(
                                # read done
                                fe_read_data[i](be_read_data_i),
                                fe_read_data_valid[i](1),
                            ),
                        )
                        for i in range(self.NUM_PORTS)
                    ],
                ),
            )
        )

        return m
