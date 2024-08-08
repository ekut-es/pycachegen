from math import ceil, log2
from veriloggen import Module, Posedge, Negedge, If, AndList, Not, For, Or, And

from pycachegen.cache_config_validation import (
    InternalMemoryConfig,
)


class FunctionalMemoryGenerator:

    def __init__(self, config: InternalMemoryConfig) -> None:
        """Generator for a data memory that can hold data, hence it's called functional.


        Args:
            config (MemoryConfig): Configuration for this memory.
        """
        self.DATA_WIDTH = config.DATA_WIDTH
        self.ADDRESS_WIDTH = config.ADDRESS_WIDTH
        self.READ_LATENCY = config.READ_LATENCY
        self.WRITE_LATENCY = config.WRITE_LATENCY
        self.BYTE_SIZE = config.BYTE_SIZE
        self.MIN_ADDRESS = config.MIN_ADDRESS
        self.MAX_ADDRESS = config.MAX_ADDRESS
        self.ENABLE_RESET = config.ENABLE_RESET

        # internal constants
        self.BYTES_PER_WORD = self.DATA_WIDTH // self.BYTE_SIZE
        self.LATENCY_COUNTER_SIZE = ceil(
            log2(max(self.WRITE_LATENCY, self.READ_LATENCY))
        )

    def generate_module(self) -> Module:

        m = Module("functional_memory")

        # inputs
        clk_i = m.Input("clk_i")
        reset_n_i = m.Input("reset_n_i")
        address_i = m.Input("address_i", self.ADDRESS_WIDTH)
        address_valid_i = m.Input("address_valid_i")
        write_data_i = m.Input("write_data_i", self.DATA_WIDTH)
        write_data_valid_i = m.Input("write_data_valid_i")
        read_write_select_i = m.Input("read_write_select_i")
        write_strobe_i = m.Input("write_strobe_i", self.BYTES_PER_WORD)

        # outputs
        read_data_o = m.Output("read_data_o", self.DATA_WIDTH)
        read_data_valid_o = m.Output("read_data_valid_o")
        write_done_o = m.Output("write_done_o")
        port_ready_o = m.Output("port_ready_o")

        # input buffer
        address = m.Reg("address", self.ADDRESS_WIDTH)
        write_data = m.Reg("write_data", self.DATA_WIDTH)
        read_write_select = m.Reg("read_write_select")
        write_strobe = m.Reg("write_strobe", self.BYTES_PER_WORD)

        # output buffer
        read_data = m.Reg("read_data", self.BYTE_SIZE, self.BYTES_PER_WORD)
        read_data_valid = m.Reg("read_data_valid")
        write_done = m.Reg("write_done")

        # internal
        latency_counter = m.Reg("latency_counter", self.LATENCY_COUNTER_SIZE)
        data_memory = []
        for i in range(self.BYTES_PER_WORD):
            data_memory.append(
                m.Reg(
                    f"data_memory_{i}",
                    self.BYTE_SIZE,
                    dims=(self.MAX_ADDRESS - self.MIN_ADDRESS),
                )
            )
        processing_request = m.Reg("processing_request")

        # output buffer assignments
        for i in range(self.BYTES_PER_WORD):
            m.Assign(
                read_data_o[self.BYTE_SIZE * i : self.BYTE_SIZE * (i + 1)](read_data[i])
            )
        m.Assign(read_data_valid_o(read_data_valid))
        m.Assign(write_done_o(write_done))
        m.Assign(port_ready_o(Not(processing_request)))

        rst_i = m.Integer("rst_i")

        m.Always(Posedge(clk_i))(
            # nothing in progress
            If(And(self.ENABLE_RESET, Not(reset_n_i)))(
                # Use a Verilog For Loop so we do not create a huge number of lines here
                [
                    For(
                        rst_i(0),
                        rst_i < (self.MAX_ADDRESS - self.MIN_ADDRESS),
                        rst_i.inc(),
                    )(data_memory[i][rst_i](0, blk=True))
                    for i in range(self.BYTES_PER_WORD)
                ],
                latency_counter(0),
                address(0),
                write_data(0),
                read_write_select(0),
                [read_data[i](0) for i in range(self.BYTES_PER_WORD)],
                read_data_valid(0),
                write_done(0),
                processing_request(0),
                write_strobe(0),
            ).Else(
                If(Not(processing_request))(
                    If(
                        AndList(
                            address_valid_i == 1,
                            Or(
                                read_write_select_i == 0,
                                And(read_write_select_i == 1, write_data_valid_i == 1),
                            ),
                            (
                                address_i < self.MAX_ADDRESS
                                if (2**self.ADDRESS_WIDTH != self.MAX_ADDRESS)
                                else True
                            ),
                            (
                                address_i >= self.MIN_ADDRESS
                                if (self.MIN_ADDRESS != 0)
                                else True
                            ),
                        )
                    )(
                        # incoming request is valid
                        address(address_i),
                        write_data(write_data_i),
                        write_strobe(write_strobe_i),
                        read_write_select(read_write_select_i),
                        read_data_valid(0),
                        write_done(0),
                        processing_request(1),
                        latency_counter.inc(),
                    ),
                ).Else(
                    If(
                        Not(
                            Or(
                                And(
                                    read_write_select == 0,
                                    latency_counter == self.READ_LATENCY - 1,
                                ),
                                And(
                                    read_write_select == 1,
                                    latency_counter == self.WRITE_LATENCY - 1,
                                ),
                            )
                        )
                    )(
                        # we still need to stall
                        latency_counter.inc()
                    ).Else(
                        # we have stalled for long enough
                        processing_request(0),
                        latency_counter(0),
                        If(read_write_select == 0)(
                            # finish read
                            [
                                read_data[i](data_memory[i][address - self.MIN_ADDRESS])
                                for i in range(self.BYTES_PER_WORD)
                            ],
                            read_data_valid(1),
                        ).Else(
                            # finish write
                            write_done(1),
                            [
                                If(write_strobe[i])(
                                    data_memory[i][address - self.MIN_ADDRESS](
                                        write_data[
                                            self.BYTE_SIZE
                                            * i : self.BYTE_SIZE
                                            * (i + 1)
                                        ]
                                    )
                                )
                                for i in range(self.BYTES_PER_WORD)
                            ],
                        ),
                    ),
                )
            )
        ),

        return m
