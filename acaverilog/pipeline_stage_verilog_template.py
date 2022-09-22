import os

from .acadl_object_verilog_template import ACADLObjectVerilogTemplate, LatencyIsNotAnInteger, TargetDirNotEmptyException
from .instruction.target_id_config import TargetIdConfig
from acadl import PipelineStage
from math import ceil, log2

from jinja2 import Template


class PipelineStageVerilogTemplate(ACADLObjectVerilogTemplate):

    def __init__(self, pipeline_stage: PipelineStage, instruction_size: int,
                 target_id_config: TargetIdConfig,
                 forward_port_map: int) -> None:
        super().__init__(pipeline_stage)

        self.pipeline_stage_verilog_file_name = "PipelineStage.v"
        self.forward_lookup_table_verilog_file_name = "ForwardLookupTable.v"
        self.tb_file_name = "PipelineStage_tb.cc"

        self.instruction_size = instruction_size
        self.target_id_config = target_id_config
        self.forward_ports = len(set(forward_port_map.values()))
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
        with open(self.pipeline_stage_verilog_template_path) as f:
            pipeline_stage_verilog_template = Template(f.read())

        with open(
                target_dir_path +
                f"/{self.name}_{self.pipeline_stage_verilog_file_name}",
                "w") as f:
            f.write(
                pipeline_stage_verilog_template.render(
                    name=self.name,
                    latency=self.acadl_object.latency,
                    target_id_start_bit=self.target_id_config.start_bit,
                    target_id_length=self.target_id_config.length,
                    instruction_size=self.instruction_size,
                    forward_ports=self.forward_ports,
                    forward_ports_size=ceil(log2(self.forward_ports)),
                    forward_port_map=self.forward_port_map))

        # generate forward lookup table verilog
        with open(self.forward_lookup_table_verilog_template_path) as f:
            forward_lookup_table_verilog_template = Template(f.read())

        with open(
                target_dir_path +
                f"/{self.name}_{self.forward_lookup_table_verilog_file_name}",
                "w+") as f:
            f.write(
                forward_lookup_table_verilog_template.render(
                    name=self.name,
                    target_id_length=self.target_id_config.length,
                    forward_ports=self.forward_ports,
                    forward_ports_size=ceil(log2(self.forward_ports)),
                    forward_port_map=self.forward_port_map))

    def generate_test_bench(self,
                            target_dir_path: str,
                            ignore_target_dir_contents: bool = False) -> None:
        super().generate_test_bench(target_dir_path,
                                    ignore_target_dir_contents)

        # generate verilog
        self.generate_verilog(target_dir_path)

        # generate SystemC testbench
        with open(self.tb_template_path) as f:
            tb_template = Template(f.read())

        with open(target_dir_path + f"/{self.name}_{self.tb_file_name}",
                  "w+") as f:
            f.write(
                tb_template.render(
                    name=self.name,
                    latency=self.acadl_object.latency,
                    instruction_size=self.instruction_size,
                    target_id_start_bit=self.target_id_config.start_bit,
                    target_id_length=self.target_id_config.length,
                    forward_ports=self.forward_ports,
                    forward_port_map=self.forward_port_map))

        # generate CMakeLists.txt
        with open(self.pipeline_stage_template_dir_path +
                  "/CMakeLists.txt") as f:
            cmake_lists_template = Template(f.read())

        with open(target_dir_path + f"/CMakeLists.txt", "w+") as f:
            f.write(cmake_lists_template.render(name=self.name))
