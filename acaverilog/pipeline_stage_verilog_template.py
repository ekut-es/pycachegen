import os

from .acadl_object_verilog_template import ACADLObjectVerilogTemplate, LatencyIsNotAnInteger, TargetDirNotEmptyException
from .instruction.target_id_config import TargetIdConfig
from .utils import read_write_template
from acadl import PipelineStage
from math import ceil, log2
from typing import Dict


class PipelineStageVerilogTemplate(ACADLObjectVerilogTemplate):

    def __init__(self, pipeline_stage: PipelineStage, instruction_size: int,
                 target_id_config: TargetIdConfig,
                 forward_port_map: Dict[int, int]) -> None:
        super().__init__(pipeline_stage)

        self.pipeline_stage_verilog_file_name = "PipelineStage.v"
        self.forward_lookup_table_verilog_file_name = "ForwardLookupTable.v"
        self.tb_file_name = "PipelineStage_tb.cc"

        self.instruction_size = instruction_size
        self.target_id_config = target_id_config
        self.forward_ports = max(forward_port_map.values()) + 1
        self.forward_port_map = forward_port_map

        # check if latency is an integer
        if self.acadl_object.latency.int_latency == -1:
            raise LatencyIsNotAnInteger(self.acadl_object,
                                        self.acadl_object.latency)

        self.pipeline_stage_template_dir_path = f"{self.verilog_template_dir_path}/pipeline_stage"
        self.pipeline_stage_verilog_template_path = f"{self.pipeline_stage_template_dir_path}/{self.pipeline_stage_verilog_file_name}"
        self.forward_lookup_table_verilog_template_path = f"{self.pipeline_stage_template_dir_path}/{self.forward_lookup_table_verilog_file_name}"
        self.tb_template_path = f"{self.pipeline_stage_template_dir_path}/{self.tb_file_name}"

    def generate_verilog(self, target_dir_path: str) -> None:
        # generate pipeline stage verilog
        read_write_template(
            self.pipeline_stage_verilog_template_path,
            target_dir_path +
            f"/{self.name}_{self.pipeline_stage_verilog_file_name}",
            name=self.name,
            latency=self.acadl_object.latency,
            target_id_start_bit=self.target_id_config.start_bit,
            target_id_length=self.target_id_config.length,
            instruction_size=self.instruction_size,
            forward_ports=self.forward_ports,
            forward_ports_size=max(ceil(log2(self.forward_ports)), 1),
            forward_port_map=self.forward_port_map)

        # generate forward lookup table verilog
        read_write_template(
            self.forward_lookup_table_verilog_template_path,
            target_dir_path +
            f"/{self.name}_{self.forward_lookup_table_verilog_file_name}",
            name=self.name,
            target_id_length=self.target_id_config.length,
            forward_ports=self.forward_ports,
            forward_ports_size=max(ceil(log2(self.forward_ports)), 1),
            forward_port_map=self.forward_port_map)

    def generate_test_bench(self,
                            target_dir_path: str,
                            ignore_target_dir_contents: bool = False) -> None:
        super().generate_test_bench(target_dir_path,
                                    ignore_target_dir_contents)

        # generate verilog
        self.generate_verilog(target_dir_path)

        # generate SystemC testbench
        read_write_template(
            self.tb_template_path,
            target_dir_path + f"/{self.name}_{self.tb_file_name}",
            name=self.name,
            latency=self.acadl_object.latency,
            instruction_size=self.instruction_size,
            target_id_start_bit=self.target_id_config.start_bit,
            target_id_length=self.target_id_config.length,
            forward_ports=self.forward_ports,
            forward_port_map=self.forward_port_map)

        # generate CMakeLists.txt
        read_write_template(self.pipeline_stage_template_dir_path +
                            "/CMakeLists.txt",
                            target_dir_path + f"/CMakeLists.txt",
                            name=self.name)
