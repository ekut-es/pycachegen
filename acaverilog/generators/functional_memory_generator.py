from math import ceil, log2
from veriloggen import Module, Posedge, Negedge, If, AndList

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
        # non configurable atm
        self.read_write_ports = 1
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
        READ_LATENCY = m.Parameter(
            'READ_LATENCY', self.read_latency - 1)
        WRITE_LATENCY = m.Parameter(
            'WRITE_LATENCY', self.write_latency - 1)
        DATA_WIDTH = m.Parameter('DATA_WIDTH', self.data_width)
        ADDRESS_WIDTH = m.Parameter('ADDRESS_WIDTH', self.address_width)

        clk_i = m.Input('clk_i')
        reset_n_i = m.Input('reset_n_i')

        # inputs
        address_i = []
        address_valid_i = []
        write_data_i = []
        write_data_valid_i = []
        read_write_select_i = []
        for i in range(self.read_write_ports):
            address_i.append(m.Input(f'address_{i}_i', ADDRESS_WIDTH))
            address_valid_i.append(m.Input(f'address_valid_{i}_i'))
            write_data_i.append(m.Input(f'write_data_{i}_i', DATA_WIDTH))
            write_data_valid_i.append(m.Input(f'write_data_valid_{i}_i'))
            read_write_select_i.append(m.Input(f'read_write_select_{i}_i'))

        # outputs
        read_data_o = []
        read_data_valid_o = []
        write_done_o = []
        port_ready_o = []
        for i in range(self.read_write_ports):
            read_data_o.append(m.Output(f'read_data_{i}_o', DATA_WIDTH))
            read_data_valid_o.append(m.Output(f'read_data_valid_{i}_o'))
            write_done_o.append(m.Output(f'write_done_{i}_o'))
            port_ready_o.append(m.Output(f'port_ready_{i}_o'))

        READ_LATENCY_COUNTER_SIZE = m.Localparam(
            'READ_LATENCY_COUNTER_SIZE',
            ceil(log2(self.read_latency)))
        WRITE_LATENCY_COUNTER_SIZE = m.Localparam(
            'WRITE_LATENCY_COUNTER_SIZE',
            ceil(log2(self.write_latency)))

        read_latency_counter = []
        write_latency_counter = []
        for i in range(self.read_write_ports):
            read_latency_counter.append(
                m.Reg(f'read_latency_counter_{i}', READ_LATENCY_COUNTER_SIZE))
            write_latency_counter.append(
                m.Reg(f'write_latency_counter_{i}',
                      WRITE_LATENCY_COUNTER_SIZE))

        # input buffer
        address = []
        address_valid = []
        write_data = []
        write_data_valid = []
        read_write_select = []
        for i in range(self.read_write_ports):
            address.append(m.Reg(f'address_{i}', ADDRESS_WIDTH))
            address_valid.append(m.Reg(f'address_valid_{i}'))
            write_data.append(m.Reg(f'write_data_{i}', DATA_WIDTH))
            write_data_valid.append(m.Reg(f'write_data_valid_{i}'))
            read_write_select.append(m.Reg(f'read_write_select_{i}'))

        # output buffer
        read_data = []
        read_data_valid = []
        write_done = []
        port_ready = []
        for i in range(self.read_write_ports):
            read_data.append(m.Reg(f'read_data_{i}', DATA_WIDTH))
            read_data_valid.append(m.Reg(f'read_data_valid_{i}'))
            write_done.append(m.Reg(f'write_done_{i}'))
            port_ready.append(m.Reg(f'port_ready_{i}'))

        # internal
        data_memory = m.Reg("data_memory", DATA_WIDTH, dims=pow(2, ADDRESS_WIDTH.value))
        read_in_progress = []
        write_in_progress = []
        for i in range(self.read_write_ports):
            read_in_progress.append(m.Reg(f'read_in_progress_{i}'))
            write_in_progress.append(m.Reg(f'write_in_progress_{i}'))

        for i in range(self.read_write_ports):
            m.Assign(port_ready[i](AndList(read_in_progress[i] == 0,
                                           write_in_progress[i] == 0)))

        for i in range(self.read_write_ports):
            m.Assign(read_data_o[i](read_data[i]))
            m.Assign(read_data_valid_o[i](read_data_valid[i]))
            m.Assign(write_done_o[i](write_done[i]))
            m.Assign(port_ready_o[i](port_ready[i]))

        for i in range(self.read_write_ports):
            m.Always(Posedge(clk_i), Negedge(reset_n_i))(
                If(reset_n_i == 0)
                (read_latency_counter[i](READ_LATENCY),
                 write_latency_counter[i](WRITE_LATENCY), address[i](0),
                 address_valid[i](0), write_data[i](0), write_data_valid[i](0),
                 read_write_select[i](0), read_data[i](0),
                 read_data_valid[i](0), write_done[i](0)).Else(
                     # nothing in progress
                     If(port_ready[i] == 1)
                     (
                         # initialize read: buffer data and set latency counter
                         If(
                             AndList(read_write_select_i[i] == 0,
                                     address_valid_i[i] == 1))
                         (read_in_progress[i](1),
                          read_latency_counter[i](READ_LATENCY),
                          address[i](address_i[i]), address_valid[i](1),
                          read_data_valid[i](0), write_done[i](0)),
                         # initialize write
                         If(
                             AndList(read_write_select_i[i] == 1,
                                     address_valid_i[i] == 1,
                                     write_data_valid_i[i] == 1))
                         (write_in_progress[i](1),
                          write_latency_counter[i](WRITE_LATENCY),
                          address[i](address_i[i]), address_valid[i](1),
                          write_data[i](write_data_i[i]),
                          read_data_valid[i](0), write_done[i](0))
                     ).Else(
                         # decrement read latency counter if read in progress
                         If(
                             AndList(read_in_progress[i] == 1,
                                     read_latency_counter[i] != 0))
                         (read_latency_counter[i](read_latency_counter[i] - 1)
                          ),
                         # decrement write latency counter if write in progress
                         If(
                             AndList(write_in_progress[i] == 1,
                                     write_latency_counter[i] != 0))
                         (write_latency_counter[i](write_latency_counter[i] -
                                                   1)),
                         # finish read
                         If(
                             AndList(read_in_progress[i] == 1,
                                     read_latency_counter[i] == 0))
                         (
                             read_in_progress[i](0),
                             address_valid[i](0),
                             read_data[i](data_memory[address[i]]),
                             read_data_valid[i](1)),
                         # finish write
                         If(
                             AndList(write_in_progress[i] == 1,
                                     write_latency_counter[i] == 0))
                         (write_in_progress[i](0), address_valid[i](0),
                          write_done[i](1)), data_memory[address[i]](write_data[i])),

                     # reset write_done after one cycle
                     If(write_done[i] == 1)(write_done[i](0))))

        return m


if __name__ == "__main__":
    memory_generator = FunctionalMemoryGenerator()
    m = memory_generator.generate_module()
    m.to_verilog("../src/functional_memory.v", for_verilator=True)
