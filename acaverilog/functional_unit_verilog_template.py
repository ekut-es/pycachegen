import os

from acadl_object_verilog_template import ACADLObjectVerilogTemplate, LatencyIsNotAnInteger
from utils import read_write_template
from acadl import FunctionalUnit
from math import ceil, log2
from typing import Dict
from veriloggen import *


class FunctionalUnitVerilogTemplate(ACADLObjectVerilogTemplate):

    def __init__(self, functional_unit: FunctionalUnit,
                instruction_size: int = 32) -> None:
        super().__init__(functional_unit)

        self.functional_unit_verilog_file_name = "FunctionalUnit.v"
        self.tb_file_name = "FunctionalUnit_tb.cc"
        self.functional_unit_template_dir_path = f"{self.verilog_template_dir_path}/functional_unit"
        self.functional_unit_verilog_template_path = f"{self.functional_unit_template_dir_path}/{self.functional_unit_verilog_file_name}"
        self.tb_template_path = f"{self.functional_unit_template_dir_path}/{self.tb_file_name}"

        # check if latency is an integer
        if self.acadl_object.latency.int_latency == -1:
            raise LatencyIsNotAnInteger(self.acadl_object,
                                        self.acadl_object.latency)
        
        if self.acadl_object.latency.int_latency == 0:
            self.acadl_object.latency.int_latency = 1

        self.instruction_size = instruction_size

    def generate_module(self) -> Module:
        # generate execute stage module
    
        m = Module(f"{self.name}_FunctionalUnit")
            
        LATENCY = m.Parameter('LATENCY', self.acadl_object.latency.int_latency - 1)

        clk_i = m.Input('clk_i')
        reset_n_i = m.Input('reset_n_i')

        instruction_i = m.Input('instruction_i', self.instruction_size)
        instruction_valid_i = m.Input('instruction_valid_i')
        
        ready_o = m.Output('ready_o')

        LATENCY_COUNTER_SIZE = m.Localparam('LATENCY_COUNTER_SIZE', ceil(log2(self.acadl_object.latency.int_latency)) + 1)
        latency_counter = m.Reg('latency_counter', LATENCY_COUNTER_SIZE)

        instruction = m.Reg('instruction', self.instruction_size)
        instruction_valid = m.Reg('instruction_valid')
        ready = m.Reg('ready')
        
        m.Assign(ready_o(ready))

        
        m.Always(Posedge(clk_i), Negedge(reset_n_i))(
            If(reset_n_i == 0)(
                instruction(0),
                instruction_valid(0),
                ready(1),
                latency_counter(LATENCY)
            ).Else(
                # buffer instruction if ready and valid
                If(AndList(instruction_i != 0, instruction_valid_i == 1, ready == 1))(
                    instruction(instruction_i),
                    instruction_valid(instruction_valid_i),
                    ready(0)
                ),

                # decrement latency counter if instruction is buffered
                If(AndList(latency_counter != 0, ready == 0))(
                    latency_counter(latency_counter - 1)
                ),

                # reset if latency counter is 0 and next stage is ready
                If(AndList(latency_counter == 0, ready == 0))(
                    ready(1),
                    instruction(0),
                    instruction_valid(0),
                    latency_counter(LATENCY)
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
        self.generate_module().to_verilog(filename = target_dir_path + f"/{self.name}_{self.functional_unit_verilog_file_name}", for_verilator = True)

        # generate SystemC testbench
        read_write_template(
            self.tb_template_path,
            target_dir_path + f"/{self.name}_{self.tb_file_name}",
            vcd_dir_path=target_dir_path,
            name=self.name,
            latency=self.acadl_object.latency.int_latency,
            instruction_size=self.instruction_size,)

        # generate CMakeLists.txt
        read_write_template(self.functional_unit_template_dir_path +
                            "/CMakeLists.txt",
                            target_dir_path + f"/CMakeLists.txt",
                            name=self.name)
        
        # copy assertv
        os.system(f"cp {self.dir_path}/assertv.h {target_dir_path}")
