from math import ceil, log2
from typing import Dict
from veriloggen import Module, Submodule, Posedge, Negedge, If, For, AndList, Cond

from acadl import RegisterFile

from acaverilog.generators.acadl_object_generator import ACADLObjectGenerator


class RegisterFileEmptyException(Exception):

    def __init__(self, register_file: RegisterFile):
        self.register_file = register_file

    def __str__(self):
        return f"Register file '{self.register_file.name}' is empty!"


class RegisterFileFloatException(Exception):

    def __init__(self, register_file: RegisterFile):
        self.register_file = register_file

    def __str__(self):
        return f"Register file '{self.register_file.name}' contains a float value!"


class RegisterFileGenerator(ACADLObjectGenerator):

    def __init__(self, register_file: RegisterFile) -> None:
        super().__init__(register_file)

        self.data_width = self.acadl_object.data_width
        self.registers = self.acadl_object.registers

        # check if registers is empty or None
        if self.registers is None or len(self.registers) == 0:
            raise RegisterFileEmptyException(self.acadl_object)

        # check if registers contain floats
        for register in self.registers:
            if self.registers[register].payload.float_payload != 0.0:
                raise RegisterFileFloatException(self.acadl_object)

        # convert registers to list, losing the keys
        self.registers = list(self.registers.values())

    def generate_module(self) -> Module:

        m = Module(f"{self.name}_RegisterFile")

        ADDRESS_WIDTH = m.Parameter('ADDRESS_WIDTH',
                                    max(ceil(log2(len(self.registers))), 1))
        DATA_WIDTH = m.Parameter('DATA_WIDTH', self.data_width)
        REGISTER_SIZE = m.Parameter('REGISTER_SIZE', len(self.registers))

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

        address = m.Reg('address', ADDRESS_WIDTH)
        address_valid = m.Reg('address_valid')
        write_data = m.Reg('write_data', DATA_WIDTH)
        write_data_valid = m.Reg('write_data_valid')
        read_write_select = m.Reg('read_write_select')
        read_data = m.Reg('read_data', DATA_WIDTH)
        read_data_valid = m.Reg('read_data_valid')
        write_done = m.Reg('write_done')

        # generate registers
        registers = m.Reg('registers', DATA_WIDTH, REGISTER_SIZE)
        _reset_list = []
        for i in range(len(self.registers)):
            _reset_list.append(registers[i](
                self.registers[i].payload.int_payload))
        _reset_list.append(write_done(0))

        m.Assign(address(address_i))
        m.Assign(address_valid(address_valid_i))
        m.Assign(write_data(write_data_i))
        m.Assign(write_data_valid(write_data_valid_i))
        m.Assign(read_write_select(read_write_select_i))

        m.Assign(read_data_o(read_data))
        m.Assign(read_data_valid_o(read_data_valid))
        m.Assign(write_done_o(write_done))

        m.Always(Posedge(clk_i), Negedge(reset_n_i))(If(reset_n_i == 0)([
            registers[i](self.registers[i].payload.int_payload)
            for i in range(len(self.registers))
        ] + [read_data(0), read_data_valid(0),
             write_done(0)]).Else(
                 If(address_valid == 1)(If(read_write_select == 0)(
                     read_data(registers[address]), read_data_valid(1),
                     write_done(0)).Else(registers[address](write_data),
                                         read_data_valid(0),
                                         write_done(1))).Else(
                                             read_data_valid(0),
                                             write_done(0))))

        return m
