from math import ceil, log2
from veriloggen import Module, Posedge, Negedge, If, AndList, Not, For, Or, And

from acaverilog.generators.cache.cache_config_validation import (
    assert_data_width_valid,
    assert_greater_equal
)




class FunctionalMemoryGenerator:

    def __init__(
        self, data_width: int, address_width: int, read_latency: int, write_latency: int
    ) -> None:
        """Generator for a data memory that can hold data, hence it's called functional.

        Args:
            data_width (int): Width of one data word in bits.
            address_width (int): Width of the addresses in bits. Addresses do not include a byte offset.
            read_latency (int): The number of clock cycles required for a read operation. Needs to be at least 2.
            write_latency (int): The number of clock cycles required for a read operation. Needs to be at least 2.
        """
        assert_greater_equal(read_latency, 2, "read_latency")
        assert_greater_equal(write_latency, 2, "write_latency")
        assert_data_width_valid(data_width)

        self.DATA_WIDTH = data_width
        self.ADDRESS_WIDTH = address_width
        self.READ_LATENCY = read_latency
        self.WRITE_LATENCY = write_latency

        # internal constants
        self.BYTE_SIZE = 8
        self.BYTES_PER_WORD = data_width // self.BYTE_SIZE
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
        port_ready = m.Reg("port_ready")

        # internal
        latency_counter = m.Reg("latency_counter", self.LATENCY_COUNTER_SIZE)
        data_memory = []
        for i in range(self.BYTES_PER_WORD):
            data_memory.append(
                m.Reg(
                    f"data_memory_{i}",
                    self.BYTE_SIZE,
                    dims=(pow(2, self.ADDRESS_WIDTH)),
                )
            )

        # output buffer assignments
        for i in range(self.BYTES_PER_WORD):
            m.Assign(
                read_data_o[self.BYTE_SIZE * i : self.BYTE_SIZE * (i + 1)](read_data[i])
            )
        m.Assign(read_data_valid_o(read_data_valid))
        m.Assign(write_done_o(write_done))
        m.Assign(port_ready_o(port_ready))

        m.Always(Posedge(clk_i), Negedge(reset_n_i))(
            # nothing in progress
            If(reset_n_i == 0)(
                # no data_memory reset because that would create a huge number of lines
                latency_counter(0),
                address(0),
                write_data(0),
                read_write_select(0),
                [read_data[i](0) for i in range(self.BYTES_PER_WORD)],
                read_data_valid(0),
                write_done(0),
                port_ready(1),
                write_strobe(0),
            ).Else(
                If(port_ready_o == 1)(
                    If(
                        And(
                            address_valid_i == 1,
                            Or(
                                read_write_select_i == 0,
                                And(read_write_select_i == 1, write_data_valid_i == 1),
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
                        port_ready(0),
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
                        port_ready(1),
                        latency_counter(0),
                        If(read_write_select == 0)(
                            # finish read
                            [
                                read_data[i](data_memory[i][address])
                                for i in range(self.BYTES_PER_WORD)
                            ],
                            read_data_valid(1),
                        ).Else(
                            # finish write
                            write_done(1),
                            [
                                If(write_strobe[i])(
                                    data_memory[i][address](
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


if __name__ == "__main__":
    memory_generator = FunctionalMemoryGenerator(
        data_width=16, address_width=3, read_latency=10, write_latency=15
    )
    m = memory_generator.generate_module()
    m.to_verilog("../src/functional_memory.v", for_verilator=True)
