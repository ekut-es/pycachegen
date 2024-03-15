import os

from acadl_object_verilog_template import ACADLObjectVerilogTemplate
from utils import read_write_template
from acadl import RegisterFile
from math import ceil, log2
from typing import Dict
from veriloggen import *


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

class RegisterFileVerilogTemplate(ACADLObjectVerilogTemplate):

    def __init__(self, register_file: RegisterFile) -> None:
        super().__init__(register_file)

        self.register_file_verilog_file_name = "RegisterFile.v"
        self.tb_file_name = "RegisterFile_tb.cc"
        self.register_file_template_dir_path = f"{self.verilog_template_dir_path}/register_file"
        self.register_file_verilog_template_path = f"{self.register_file_template_dir_path}/{self.register_file_verilog_file_name}"
        self.tb_template_path = f"{self.register_file_template_dir_path}/{self.tb_file_name}"

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
        # generate register file module
        
        m = Module(f"{self.name}_RegisterFile")

        REGISTER_SIZE = m.Parameter('REGISTER_SIZE', len(self.registers))
        ADDRESS_WIDTH = m.Parameter('ADDRESS_WIDTH', ceil(log2(len(self.registers))))

        clk_i = m.Input('clk_i')
        reset_n_i = m.Input('reset_n_i')

        read_address_i = m.Input('read_address_i', ADDRESS_WIDTH)
        write_address_i = m.Input('write_address_i', ADDRESS_WIDTH)
        write_data_i = m.Input('write_data_i', self.data_width)
        read_write_select_i = m.Input('read_write_select_i')
        
        read_address_valid_o = m.Output('read_address_valid_o')
        write_address_valid_o = m.Output('write_address_valid_o')
        read_data_o = m.Output('read_data_o', self.data_width, value = 1)
        write_done_o = m.Output('write_done_o')
        
        read_address = m.Reg('read_address', ADDRESS_WIDTH)
        write_address = m.Reg('write_address', ADDRESS_WIDTH)
        read_address_valid = m.Wire('read_address_valid')
        write_address_valid = m.Wire('write_address_valid')
        write_data = m.Reg('write_data', self.data_width)
        read_data = m.Wire('read_data', self.data_width)
        read_write_select = m.Reg('read_write_select')
        write_done = m.Reg('write_done')

        # generate registers
        registers = m.Reg('registers', self.data_width, len(self.registers))
        _initial_registers = []
        for i in range (len(self.registers)):
            _initial_registers.append(registers[i](self.registers[i].payload.int_payload))
        _initial_registers.append(write_done(0))

        m.Assign(read_address(read_address_i))
        m.Assign(write_address(write_address_i))
        m.Assign(write_data(write_data_i))
        m.Assign(read_write_select(read_write_select_i))

        m.Assign(read_address_valid(Cond(AndList(read_write_select == 0, read_address < REGISTER_SIZE), 1, 0)))
        m.Assign(write_address_valid(Cond(AndList(read_write_select == 1, write_address < REGISTER_SIZE), 1, 0)))
        m.Assign(read_data(Cond(AndList(read_write_select == 0, read_address_valid == 1), registers[read_address], 0)))

        m.Assign(read_address_valid_o(read_address_valid))
        m.Assign(write_address_valid_o(write_address_valid))
        m.Assign(read_data_o(read_data))
        m.Assign(write_done_o(write_done))
        
        m.Always(Posedge(clk_i), Negedge(reset_n_i))(
            If(reset_n_i == 0)(
                _initial_registers
            ).Else(
                If(write_done == 0)(
                    # write
                    If(write_address_valid == 1)(
                        registers[write_address](write_data),
                        write_done(1)
                    )
                ).Else(
                    write_done(0)
                )
            )
        )
        
        return m

    def generate_test_bench(self,
                            target_dir_path: str,
                            ignore_target_dir_contents: bool = False) -> None:
        super().generate_test_bench(target_dir_path,
                                    ignore_target_dir_contents)
        
        if not os.path.isdir(target_dir_path):
            os.mkdir(target_dir_path)

        # generate verilog
        self.generate_module().to_verilog(filename = target_dir_path + f"/{self.name}_{self.register_file_verilog_file_name}", for_verilator = True)

        # generate SystemC testbench
        read_write_template(
            self.tb_template_path,
            target_dir_path + f"/{self.name}_{self.tb_file_name}",
            vcd_dir_path=target_dir_path,
            name=self.name,
            data_width=self.data_width,
            registers=self.registers,
            register_size=len(self.registers),
        )

        # generate CMakeLists.txt
        read_write_template(self.register_file_template_dir_path +
                            "/CMakeLists.txt",
                            target_dir_path + f"/CMakeLists.txt",
                            name=self.name)
        
        # copy assertv
        os.system(f"cp {self.dir_path}/assertv.h {target_dir_path}")
