from math import ceil, log2
from veriloggen import Module, Posedge, Negedge, If, AndList, Not, For

# from acadl import Memory

# from .acadl_object_generator import ACADLObjectGenerator
# from ..exceptions import LatencyIsNotAnInteger


class MemoryAddressRangesOverlapException(Exception):

    def __init__(self, memory):
        self.memory = memory

    def __str__(self):
        return f"Address ranges {self.memory.address_ranges} of {type(self.memory)} {self.memory.name} overlap!"


class MemoryTestbenchParameterException(Exception):

    def __init__(self, memory, parameter_name, parameter_value):
        self.memory = memory
        self.parameter_name = parameter_name
        self.parameter_value = parameter_value

    def __str__(self):
        return f"Testbench parameter malformed of {type(self.memory)} {self.memory.name} {self.parameter_name}={self.parameter_value}!"


class MemoryFileDoesNotExist(Exception):

    def __init__(self, memory_file_path):
        self.memory_file_path = memory_file_path

    def __str__(self):
        return f"Memory file '{self.memory_file_path}' does not exist!"


# class MemoryGenerator(ACADLObjectGenerator):
class FunctionalMemoryGenerator:

    def __init__(self, data_width: int, address_width: int) -> None:
        self.data_width = data_width
        self.address_width = address_width
        self.BYTE_SIZE = 8
        self.BYTES_PER_WORD = data_width // self.BYTE_SIZE
        # non configurable atm
        self.read_latency = 10
        self.write_latency = 15

    # def __init__(self, memory: Memory) -> None:
    #     super().__init__(memory)

    # self.read_write_ports = memory.read_write_ports

    # # check if latencies are integers
    # if self.acadl_object.read_latency.int_latency == -1:
    #     raise LatencyIsNotAnInteger(self.acadl_object,
    #                                 self.acadl_object.read_latency)

    # if self.acadl_object.write_latency.int_latency == -1:
    #     raise LatencyIsNotAnInteger(self.acadl_object,
    #                                 self.acadl_object.write_latency)

    # if self.acadl_object.read_latency.int_latency == 0:
    #     self.acadl_object.read_latency.int_latency = 1

    # if self.acadl_object.write_latency.int_latency == 0:
    #     self.acadl_object.write_latency.int_latency = 1

    # # check parameters for testbench
    # if self.acadl_object.port_width * self.acadl_object.data_width > 32:
    #     raise MemoryTestbenchParameterException(
    #         self.acadl_object, "port_bits_width",
    #         self.acadl_object.port_width * self.acadl_object.data_width)

    # # sort address ranges by first address of tuple
    # self.address_ranges = sorted(self.acadl_object.address_ranges,
    #                              key=lambda x: x[0])

    # # check that address ranges don't overlap
    # previous_address_range = self.address_ranges[0]
    # for current_address_range in self.address_ranges[1:]:
    #     if previous_address_range[1] > current_address_range[0]:
    #         raise MemoryAddressRangesOverlapException(self.acadl_object)

    # # calculate memory lines
    # self.memory_lines = 0
    # for address_range in self.address_ranges:
    #     self.memory_lines += len(range(address_range[0], address_range[1]))

    # self.address_translation_map = {}
    # last_address_of_previous_translated_address_range = 0
    # for address_range in self.address_ranges:
    #     self.address_translation_map[address_range] = -address_range[
    #         0] + last_address_of_previous_translated_address_range
    #     last_address_of_previous_translated_address_range = address_range[
    #         0] + self.address_translation_map[
    #             address_range] + address_range[1] - address_range[0]

    # # calculate address_width
    # # collabs address ranges List[Tuple[int,int]] into List[int]
    # min_max_addresses = [
    #     address for address_range in self.address_ranges
    #     for address in address_range
    # ]
    # self.address_width = ceil(log2(max(min_max_addresses)))
    # self.max_data_word_distance = 1024  # TODO change

    def generate_module(self) -> Module:

        m = Module("functional_memory")

        # parameters
        READ_LATENCY = m.Parameter("READ_LATENCY", self.read_latency - 1)
        WRITE_LATENCY = m.Parameter("WRITE_LATENCY", self.write_latency - 1)
        DATA_WIDTH = m.Parameter("DATA_WIDTH", self.data_width)
        ADDRESS_WIDTH = m.Parameter("ADDRESS_WIDTH", self.address_width)

        clk_i = m.Input("clk_i")
        reset_n_i = m.Input("reset_n_i")

        # inputs
        address_i = m.Input(f"address_i", ADDRESS_WIDTH)
        address_valid_i = m.Input(f"address_valid_i")
        write_data_i = m.Input(f"write_data_i", DATA_WIDTH)
        write_data_valid_i = m.Input(f"write_data_valid_i")
        read_write_select_i = m.Input(f"read_write_select_i")
        write_strobe_i = m.Input("write_strobe_i", self.BYTES_PER_WORD)

        # outputs
        read_data_o = m.Output(f"read_data_o", DATA_WIDTH)
        read_data_valid_o = m.Output(f"read_data_valid_o")
        write_done_o = m.Output(f"write_done_o")
        port_ready_o = m.Output(f"port_ready_o")

        READ_LATENCY_COUNTER_SIZE = m.Localparam(
            "READ_LATENCY_COUNTER_SIZE", ceil(log2(self.read_latency))
        )
        WRITE_LATENCY_COUNTER_SIZE = m.Localparam(
            "WRITE_LATENCY_COUNTER_SIZE", ceil(log2(self.write_latency))
        )

        read_latency_counter = m.Reg(f"read_latency_counter", READ_LATENCY_COUNTER_SIZE)
        write_latency_counter = m.Reg(
            f"write_latency_counter", WRITE_LATENCY_COUNTER_SIZE
        )

        # input buffer
        address = m.Reg(f"address", ADDRESS_WIDTH)
        address_valid = m.Reg(f"address_valid")
        write_data = m.Reg(f"write_data", DATA_WIDTH)
        write_data_valid = m.Reg(f"write_data_valid")
        read_write_select = m.Reg(f"read_write_select")
        write_strobe = m.Reg("write_strobe", self.BYTES_PER_WORD)

        # output buffer
        read_data = m.Reg(f"read_data", self.BYTE_SIZE, self.BYTES_PER_WORD)
        read_data_valid = m.Reg(f"read_data_valid")
        write_done = m.Reg(f"write_done")

        # internal
        data_memory = m.Reg(
            "data_memory",
            self.BYTE_SIZE,
            dims=(pow(2, ADDRESS_WIDTH.value), self.BYTES_PER_WORD),
        )
        read_in_progress = m.Reg(f"read_in_progress")
        write_in_progress = m.Reg(f"write_in_progress")

        m.Assign(port_ready_o(AndList(read_in_progress == 0, write_in_progress == 0)))

        for i in range(self.BYTES_PER_WORD):
            m.Assign(
                read_data_o[self.BYTE_SIZE * i : self.BYTE_SIZE * (i + 1)](read_data[i])
            )
        m.Assign(read_data_valid_o(read_data_valid))
        m.Assign(write_done_o(write_done))

        m.Always(Posedge(clk_i), Negedge(reset_n_i))(
            If(reset_n_i == 0)(
                read_latency_counter(READ_LATENCY),
                write_latency_counter(WRITE_LATENCY),
                address(0),
                address_valid(0),
                write_data(0),
                write_data_valid(0),
                read_write_select(0),
                [read_data[i](0) for i in range(self.BYTES_PER_WORD)],
                read_data_valid(0),
                write_done(0),
                read_in_progress(0),
                write_in_progress(0),
                write_strobe(0),
                [
                    [
                        data_memory[word_idx][byte_idx](0)
                        for byte_idx in range(self.BYTES_PER_WORD)
                    ]
                    for word_idx in range(pow(2, ADDRESS_WIDTH.value))
                ],
            ).Else(
                # nothing in progress
                If(port_ready_o == 1)(
                    # initialize read: buffer data and set latency counter
                    If(AndList(read_write_select_i == 0, address_valid_i == 1))(
                        read_in_progress(1),
                        read_latency_counter(READ_LATENCY),
                        address(address_i),
                        address_valid(1),
                        read_data_valid(0),
                        write_done(0),
                    ),
                    # initialize write
                    If(
                        AndList(
                            read_write_select_i == 1,
                            address_valid_i == 1,
                            write_data_valid_i == 1,
                        )
                    )(
                        write_in_progress(1),
                        write_latency_counter(WRITE_LATENCY),
                        address(address_i),
                        address_valid(1),
                        write_data(write_data_i),
                        read_data_valid(0),
                        write_done(0),
                        write_strobe(write_strobe_i),
                    ),
                ).Else(
                    # decrement read latency counter if read in progress
                    If(AndList(read_in_progress == 1, read_latency_counter != 0))(
                        read_latency_counter(read_latency_counter - 1)
                    ),
                    # decrement write latency counter if write in progress
                    If(AndList(write_in_progress == 1, write_latency_counter != 0))(
                        write_latency_counter(write_latency_counter - 1)
                    ),
                    # finish read
                    If(AndList(read_in_progress == 1, read_latency_counter == 0))(
                        read_in_progress(0),
                        address_valid(0),
                        [
                            read_data[i](data_memory[address][i])
                            for i in range(self.BYTES_PER_WORD)
                        ],
                        read_data_valid(1),
                    ),
                    # finish write
                    If(AndList(write_in_progress == 1, write_latency_counter == 0))(
                        write_in_progress(0),
                        address_valid(0),
                        write_done(1),
                        [
                            If(write_strobe[i])(
                                data_memory[address][i](
                                    write_data[
                                        self.BYTE_SIZE * i : self.BYTE_SIZE * (i + 1)
                                    ]
                                )
                            )
                            for i in range(self.BYTES_PER_WORD)
                        ],
                    ),
                )
            ),
        )

        return m


if __name__ == "__main__":
    memory_generator = FunctionalMemoryGenerator(data_width=16, address_width=3)
    m = memory_generator.generate_module()
    m.to_verilog("../src/functional_memory.v", for_verilator=True)
