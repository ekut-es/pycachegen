import os

from acadl_object_verilog_template import ACADLObjectVerilogTemplate, LatencyIsNotAnInteger
from utils import read_write_template
from acadl import InstructionMemoryAccessUnit
from math import ceil, log2
from typing import Dict
from veriloggen import *


class InstructionMemoryAccessUnitVerilogTemplate(ACADLObjectVerilogTemplate):

    def __init__(self, 
                instruction_memory_access_unit: InstructionMemoryAccessUnit,
                instruction_size: int = 32,
                ) -> None:
        super().__init__(instruction_memory_access_unit)

        self.instruction_memory_access_unit_verilog_file_name = "InstructionMemoryAccessUnit.v"
        self.tb_file_name = "InstructionMemoryAccessUnit_tb.cc"

        self.instruction_size = instruction_size

        # check if latency is an integer
        if self.acadl_object.latency.int_latency == -1:
            raise LatencyIsNotAnInteger(self.acadl_object,
                                        self.acadl_object.latency)
        
        if self.acadl_object.latency.int_latency == 0:
            self.acadl_object.latency.int_latency = 1
        
        self.instruction_memory_access_unit_template_dir_path = f"{self.verilog_template_dir_path}/instruction_memory_access_unit"
        self.instruction_memory_access_unit_verilog_template_path = f"{self.instruction_memory_access_unit_template_dir_path}/{self.instruction_memory_access_unit_verilog_file_name}"
        self.tb_template_path = f"{self.instruction_memory_access_unit_template_dir_path}/{self.tb_file_name}"

    def generate_module(self) -> Module:
        # generate instruction memory access unit module
    
        m = Module(f"{self.name}_InstructionMemoryAccessUnit")

        LATENCY = m.Parameter('LATENCY', self.acadl_object.latency.int_latency - 1)

        clk_i = m.Input('clk_i')
        reset_n_i = m.Input('reset_n_i')



        instruction_read_address_o = m.Output('instruction_read_address_o', ceil(log2(len(self.acadl_object.instruction_memory))))
        

    def generate_test_bench(self,
                            target_dir_path: str,
                            ignore_target_dir_contents: bool = False) -> None:
        super().generate_test_bench(target_dir_path,
                                    ignore_target_dir_contents)
        
        if not os.path.isdir(target_dir_path):
            os.mkdir(target_dir_path)

        # generate verilog
        self.generate_module().to_verilog(filename = target_dir_path + f"/{self.name}_{self.instruction_memory_access_unit_verilog_file_name}", for_verilator = True)

        # generate SystemC testbench
        read_write_template(
            self.tb_template_path,
            target_dir_path + f"/{self.name}_{self.tb_file_name}",
            vcd_dir_path=target_dir_path,
            name=self.name,
            latency=self.acadl_object.latency.int_latency,
            instruction_size=self.instruction_size,)

        # generate CMakeLists.txt
        read_write_template(self.instruction_memory_access_unit_template_dir_path +
                            "/CMakeLists.txt",
                            target_dir_path + f"/CMakeLists.txt",
                            name=self.name)
        
        # copy assertv
        os.system(f"cp {self.dir_path}/assertv.h {target_dir_path}")
