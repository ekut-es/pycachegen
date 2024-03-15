import os

from acadl_object_verilog_template import ACADLObjectVerilogTemplate
from pipeline_stage_verilog_template import PipelineStageVerilogTemplate
from utils import read_write_template
from acadl import ExecuteStage
from math import ceil, log2
from typing import Dict
from veriloggen import *


class ExecuteStageVerilogTemplate(PipelineStageVerilogTemplate):

    def __init__(self, execute_stage: ExecuteStage,
                instruction_size: int = 32) -> None:
        super().__init__(execute_stage)

        self.execute_stage_verilog_file_name = "ExecuteStage.v"
        self.tb_file_name = "ExecuteStage_tb.cc"
        self.execute_stage_template_dir_path = f"{self.verilog_template_dir_path}/execute_stage"
        self.execute_stage_verilog_template_path = f"{self.execute_stage_template_dir_path}/{self.execute_stage_verilog_file_name}"
        self.tb_template_path = f"{self.execute_stage_template_dir_path}/{self.tb_file_name}"

        self.instruction_size = instruction_size

    def generate_module(self) -> Module:
        # generate execute stage module
    
        m = Module(f"{self.name}_ExecuteStage")
            
        LATENCY = m.Parameter('LATENCY', self.acadl_object.latency.int_latency - 1)

        clk_i = m.Input('clk_i')
        reset_n_i = m.Input('reset_n_i')

        instruction_i = m.Input('instruction_i', self.instruction_size)
        instruction_valid_i = m.Input('instruction_valid_i')
        next_stage_ready_i = m.Input('next_stage_ready_i')

        instruction_o = m.Output('instruction_o', self.instruction_size)
        instruction_valid_o = m.Output('instruction_valid_o')
        
        ready_o = m.Output('ready_o')

        LATENCY_COUNTER_SIZE = m.Localparam('LATENCY_COUNTER_SIZE', ceil(log2(self.acadl_object.latency.int_latency)) + 1)
        latency_counter = m.Reg('latency_counter', LATENCY_COUNTER_SIZE)

        instruction = m.Reg('instruction', self.instruction_size)
        instruction_valid = m.Reg('instruction_valid')
        ready = m.Reg('ready')
        
        instruction_cond = m.Wire('instruction_cond')
        m.Assign(instruction_cond(Cond(AndList(instruction_valid == 1, latency_counter == 0, next_stage_ready_i == 1), 1, 0)))
        m.Assign(instruction_o(Cond(instruction_cond, instruction, 0)))
        m.Assign(instruction_valid_o(instruction_cond))
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

                # forward instruction (i.e. reset) if latency counter is 0 and next stage is ready
                If(AndList(latency_counter == 0, ready == 0, next_stage_ready_i == 1))(
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
        self.generate_module().to_verilog(filename = target_dir_path + f"/{self.name}_{self.execute_stage_verilog_file_name}", for_verilator = True)

        """instruction_generation_map = {}

        for forward_port in self.forward_port_map.values():
            for target_id in self.forward_port_map.keys():
                if self.forward_port_map[target_id] == forward_port:
                    instruction_generation_map[forward_port] = target_id
                    break"""

        # generate SystemC testbench
        read_write_template(
            self.tb_template_path,
            target_dir_path + f"/{self.name}_{self.tb_file_name}",
            vcd_dir_path=target_dir_path,
            name=self.name,
            latency=self.acadl_object.latency.int_latency,
            instruction_size=self.instruction_size,)

        # generate CMakeLists.txt
        read_write_template(self.execute_stage_template_dir_path +
                            "/CMakeLists.txt",
                            target_dir_path + f"/CMakeLists.txt",
                            name=self.name)
        
        # copy assertv
        os.system(f"cp {self.dir_path}/assertv.h {target_dir_path}")
