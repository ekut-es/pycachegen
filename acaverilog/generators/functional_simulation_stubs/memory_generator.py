from math import ceil, log2
from typing import Dict
import os
from veriloggen import Module, Submodule, Posedge, Negedge, If, For, AndList, Cond, Not, Systask

from acadl import Memory

from acaverilog.generators.acadl_object_generator import ACADLObjectGenerator, LatencyIsNotAnInteger


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


class MemoryGenerator(ACADLObjectGenerator):

    def __init__(self,
                 memory: Memory,
                 memory_file_path: str = None,
                 enable_data_reset=True) -> None:
        super().__init__(memory)

        self.memory_file_path = memory_file_path
        self.enable_data_reset = enable_data_reset

        # check if latencies are integers
        if self.acadl_object.read_latency.int_latency == -1:
            raise LatencyIsNotAnInteger(self.acadl_object,
                                        self.acadl_object.read_latency)

        if self.acadl_object.write_latency.int_latency == -1:
            raise LatencyIsNotAnInteger(self.acadl_object,
                                        self.acadl_object.write_latency)

        if self.acadl_object.read_latency.int_latency == 0:
            self.acadl_object.read_latency.int_latency = 1

        if self.acadl_object.write_latency.int_latency == 0:
            self.acadl_object.write_latency.int_latency = 1

        # check parameters for testbench
        if self.acadl_object.port_width * self.acadl_object.data_width > 32:
            raise MemoryTestbenchParameterException(
                self.acadl_object, "port_bits_width",
                self.acadl_object.port_width * self.acadl_object.data_width)

        # sort address ranges by first address of tuple
        self.address_ranges = sorted(self.acadl_object.address_ranges,
                                     key=lambda x: x[0])

        # check that address ranges don't overlap
        previous_address_range = self.address_ranges[0]
        for current_address_range in self.address_ranges[1:]:
            if previous_address_range[1] > current_address_range[0]:
                raise MemoryAddressRangesOverlapException(self.acadl_object)

        # calculate memory lines
        self.memory_lines = 0
        for address_range in self.address_ranges:
            self.memory_lines += len(range(address_range[0], address_range[1]))

        self.address_translation_map = {}
        last_address_of_previous_translated_address_range = 0
        for address_range in self.address_ranges:
            self.address_translation_map[address_range] = -address_range[
                0] + last_address_of_previous_translated_address_range
            last_address_of_previous_translated_address_range = address_range[
                0] + self.address_translation_map[
                    address_range] + address_range[1] - address_range[0]

        # calculate address_width
        # collabs address ranges List[Tuple[int,int]] into List[int]
        min_max_addresses = [
            address for address_range in self.address_ranges
            for address in address_range
        ]
        self.address_width = ceil(log2(max(min_max_addresses)))
        self.max_data_word_distance = 1024  # TODO change

    def generate_module(self) -> Module:

        # if a memory file path is given, check if it exists
        if self.memory_file_path is not None and not os.path.exists(
                self.memory_file_path):
            raise MemoryFileDoesNotExist(self.memory_file_path)

        # generate memory stage verilog
        m = Module(self.base_file_name)

        READ_LATENCY = m.Parameter(
            'READ_LATENCY', self.acadl_object.read_latency.int_latency - 1)
        WRITE_LATENCY = m.Parameter(
            'WRITE_LATENCY', self.acadl_object.write_latency.int_latency - 1)
        DATA_WIDTH = m.Parameter('DATA_WIDTH', self.acadl_object.data_width)
        MAX_DATA_WORD_DISTANCE = m.Parameter('MAX_DATA_WORD_DISTANCE',
                                             self.max_data_word_distance)
        MAX_CONCURRENT_REQUESTS = m.Parameter(
            'MAX_CONCURRENT_REQUESTS',
            self.acadl_object.max_concurrent_requests)
        ADDRESS_WIDTH = m.Parameter('ADDRESS_WIDTH', self.address_width)
        MEMORY_LINES = m.Parameter('MEMORY_LINES', self.memory_lines)

        clk_i = m.Input('clk_i')
        reset_n_i = m.Input('reset_n_i')

        address_i = m.Input('address_i', ADDRESS_WIDTH)
        address_valid_i = m.Input('address_valid_i')
        write_data_i = m.Input('write_data_i', DATA_WIDTH)
        write_data_valid_i = m.Input('write_data_valid_i')
        read_write_select_i = m.Input('read_write_select_i')

        read_data_o = m.Output('read_data_o', DATA_WIDTH)
        read_data_valid_o = m.Output('read_data_valid_o')
        write_done_o = m.Output('write_done_o')
        ready_o = m.Output('ready_o')

        INTERNAL_ADDRESS_WIDTH = m.Localparam('INTERNAL_ADDRESS_WIDTH',
                                              ceil(log2(self.memory_lines)))
        LATENCY_COUNTER_SIZE = m.Localparam(
            'LATENCY_COUNTER_SIZE',
            ceil(
                log2(
                    max(self.acadl_object.read_latency.int_latency,
                        self.acadl_object.write_latency.int_latency))) + 1)
        read_latency_counter = m.Reg('read_latency_counter',
                                     LATENCY_COUNTER_SIZE)
        write_latency_counter = m.Reg('write_latency_counter',
                                      LATENCY_COUNTER_SIZE)

        mem = m.Reg('mem', DATA_WIDTH, MEMORY_LINES)
        if self.memory_file_path is not None:
            m.Initial(
                Systask('display',
                        f'Loading memory from {self.memory_file_path}.'),
                Systask('readmemh', self.memory_file_path, mem))

        # input
        address = m.Reg('address', ADDRESS_WIDTH)
        address_valid = m.Reg('address_valid')
        write_data = m.Reg('write_data', DATA_WIDTH)
        write_data_valid = m.Wire('write_data_valid')
        read_write_select = m.Wire('read_write_select')

        # output
        read_data = m.Wire('read_data', DATA_WIDTH)
        read_data_valid = m.Reg('read_data_valid')
        write_done = m.Reg('write_done')
        ready = m.Wire('ready')

        # internal
        write_in_progress = m.Reg('write_in_progress')
        read_in_progress = m.Reg('read_in_progress')

        m.Assign(write_data_valid(write_data_valid_i))
        m.Assign(read_write_select(read_write_select_i))
        m.Assign(read_data(mem[address]))
        m.Assign(
            ready(
                Cond(AndList(Not(write_in_progress), Not(read_in_progress)), 1,
                     0)))

        m.Assign(read_data_o(Cond(read_data_valid == 1, read_data, 0)))
        m.Assign(read_data_valid_o(read_data_valid))
        m.Assign(write_done_o(write_done))
        m.Assign(ready_o(ready))

        _reset_list = [
            read_latency_counter(0),
            write_latency_counter(0),
            read_in_progress(0),
            write_in_progress(0),
            address(0),
            address_valid(0),
            write_data(0),
            read_data_valid(0),
            write_done(0)
        ]
        if self.enable_data_reset:
            i = m.Integer('i')
            _reset_list.append(
                For(i(0), i < MEMORY_LINES, i(i + 1))(mem[i](0)))

        m.Always(Posedge(clk_i), Negedge(reset_n_i))(
            If(reset_n_i == 0)(_reset_list).Else(
                # nothing in progress
                If(ready == 1)(
                    # initialize read: buffer data and set latency counter
                    If(AndList(read_write_select == 0, address_valid_i == 1))
                    (read_in_progress(1), read_latency_counter(READ_LATENCY),
                     address(address_i), address_valid(1), read_data_valid(0),
                     write_done(0)),
                    # initialize write
                    If(
                        AndList(read_write_select == 1, address_valid_i == 1,
                                write_data_valid == 1))
                    (write_in_progress(1),
                     write_latency_counter(WRITE_LATENCY), address(address_i),
                     address_valid(1),
                     write_data(write_data_i), mem[address](write_data),
                     read_data_valid(0), write_done(0))).Else(
                         # decrement read latency counter if read in progress
                         If(
                             AndList(read_in_progress == 1,
                                     read_latency_counter != 0))
                         (read_latency_counter(read_latency_counter - 1)),
                         # decrement write latency counter if write in progress
                         If(
                             AndList(write_in_progress == 1,
                                     write_latency_counter != 0))
                         (write_latency_counter(write_latency_counter - 1)),
                         # finish read
                         If(
                             AndList(read_in_progress == 1,
                                     read_latency_counter == 0))
                         (read_in_progress(0), address_valid(0),
                          read_data_valid(1)),
                         # finish write
                         If(
                             AndList(write_in_progress == 1,
                                     write_latency_counter == 0))
                         (write_in_progress(0), address_valid(0),
                          write_done(1)))))

        return m
