import os

from acadl_object_verilog_template import ACADLObjectVerilogTemplate, LatencyIsNotAnInteger
from utils import read_write_template
from acadl import MemoryAccessUnit
from math import ceil, log2
from typing import Dict
from veriloggen import *


class MemoryAccessUnitVerilogTemplate(ACADLObjectVerilogTemplate):

    def __init__(self, 
                memory_access_unit: MemoryAccessUnit,
                instruction_size: int = 32,
                data_width: int = 32,
                address_width: int = 16,
                register_address_width: int = 5,
                ) -> None:
        super().__init__(memory_access_unit)

        self.memory_access_unit_verilog_file_name = "MemoryAccessUnit.v"
        self.tb_file_name = "MemoryAccessUnit_tb.cc"
        self.memory_access_unit_template_dir_path = f"{self.verilog_template_dir_path}/memory_access_unit"
        self.memory_access_unit_verilog_template_path = f"{self.memory_access_unit_template_dir_path}/{self.memory_access_unit_verilog_file_name}"
        self.tb_template_path = f"{self.memory_access_unit_template_dir_path}/{self.tb_file_name}"

        self.instruction_size = instruction_size
        self.data_width = data_width
        self.address_width = address_width
        self.register_address_width = register_address_width
        
        # check if latency is an integer
        if self.acadl_object.latency.int_latency == -1:
            raise LatencyIsNotAnInteger(self.acadl_object,
                                        self.acadl_object.latency)
        
        if self.acadl_object.latency.int_latency == 0:
            self.acadl_object.latency.int_latency = 1
        

    def generate_module(self) -> Module:
        # generate memory access unit module
    
        m = Module(f"{self.name}_MemoryAccessUnit")

        LATENCY = m.Parameter('LATENCY', self.acadl_object.latency.int_latency - 1)

        # inputs
        clk_i = m.Input('clk_i')
        reset_n_i = m.Input('reset_n_i')

        instruction_i = m.Input('instruction_i', self.instruction_size)
        instruction_valid_i = m.Input('instruction_valid_i')

        memory_read_data_i = m.Input('memory_read_data_i', self.data_width)
        memory_read_data_valid_i = m.Input('memory_read_data_valid_i')
        memory_write_done_i = m.Input('memory_write_done_i')
        memory_ready_i = m.Input('memory_ready_i')

        register_read_data_i = m.Input('register_read_data_i', self.data_width)
        register_read_data_valid_i = m.Input('register_read_data_valid_i')
        register_write_done_i = m.Input('register_write_done_i')

        # outputs
        memory_address_o = m.Output('memory_address_o', self.address_width)
        memory_address_valid_o = m.Output('memory_address_valid_o')
        memory_write_data_o = m.Output('memory_write_data_o', self.data_width)
        memory_write_data_valid_o = m.Output('memory_write_data_valid_o')
        memory_read_write_select_o = m.Output('memory_read_write_select_o')

        register_address_o = m.Output('register_address_o', self.register_address_width)
        register_address_valid_o = m.Output('register_address_valid_o')
        register_write_data_o = m.Output('register_write_data_o', self.data_width)
        register_write_data_valid_o = m.Output('register_write_data_valid_o')
        register_read_write_select_o = m.Output('register_read_write_select_o')

        # internal
        instruction = m.Reg('instruction', self.instruction_size)
        instruction_valid = m.Wire('instruction_valid')

        memory_read_data = m.Reg('memory_read_data', self.data_width)
        memory_read_data_valid = m.Wire('memory_read_data_valid')
        memory_write_done = m.Reg('memory_write_done')
        memory_ready = m.Reg('memory_ready')
        
        register_read_data = m.Reg('register_read_data', self.data_width)
        register_read_data_valid = m.Reg('register_read_data_valid')
        register_write_done = m.Reg('register_write_done')

        memory_address = m.Reg('memory_address', self.address_width)
        memory_address_valid = m.Wire('memory_address_valid')
        memory_write_data = m.Reg('memory_write_data', self.data_width)
        memory_write_data_valid = m.Wire('memory_write_data_valid')
        memory_read_write_select = m.Reg('memory_read_write_select')

        register_address = m.Reg('register_address', self.register_address_width)
        register_address_valid = m.Wire('register_address_valid')
        register_write_data = m.Reg('register_write_data', self.data_width)
        register_write_data_valid = m.Wire('register_write_data_valid')
        register_read_write_select = m.Reg('register_read_write_select')

        # assign
        m.Assign(instruction_valid(instruction_valid_i))

        m.Assign(memory_read_data_valid(memory_read_data_valid_i))









        instruction_read_address_o = m.Output('instruction_read_address_o', ceil(log2(len(self.acadl_object.memory))))
        

    def generate_test_bench(self,
                            target_dir_path: str,
                            ignore_target_dir_contents: bool = False) -> None:
        super().generate_test_bench(target_dir_path,
                                    ignore_target_dir_contents)
        
        if not os.path.isdir(target_dir_path):
            os.mkdir(target_dir_path)

        # generate verilog
        self.generate_module().to_verilog(filename = target_dir_path + f"/{self.name}_{self.memory_access_unit_verilog_file_name}", for_verilator = True)

        # generate SystemC testbench
        read_write_template(
            self.tb_template_path,
            target_dir_path + f"/{self.name}_{self.tb_file_name}",
            vcd_dir_path=target_dir_path,
            name=self.name,
            latency=self.acadl_object.latency.int_latency,
            instruction_size=self.instruction_size,)

        # generate CMakeLists.txt
        read_write_template(self.memory_access_unit_template_dir_path +
                            "/CMakeLists.txt",
                            target_dir_path + f"/CMakeLists.txt",
                            name=self.name)
        
        # copy assertv
        os.system(f"cp {self.dir_path}/assertv.h {target_dir_path}")
