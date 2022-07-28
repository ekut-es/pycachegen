import os

from .acadl_object_verilog_template import ACADLObjectVerilogTemplate, LatencyIsNotAnInteger, TargetDirNotEmptyException
from acadl import PipelineStage

from jinja2 import Template


class PipelineStageVerilogTemplate(ACADLObjectVerilogTemplate):

    def __init__(self, pipeline_stage: PipelineStage,
                 instruction_size: int) -> None:
        super().__init__(pipeline_stage)

        self.verilog_file_name = "PipelineStage.v"
        self.tb_file_name = "PipelineStage_tb.cc"

        self.instruction_size = instruction_size

        self.pipeline_stage_template_dir_path = self.verilog_template_dir_path + "/pipeline_stage"
        self.pipeline_stage_verilog_template_path = self.pipeline_stage_template_dir_path + f"/{self.verilog_file_name}"
        self.tb_template_path = self.pipeline_stage_template_dir_path + "/PipelineStage_tb.cc"

    def generate_verilog(self, target_dir_path: str) -> None:
        # check if latency is an integer
        if self.acadl_object.latency.int_latency == -1:
            raise LatencyIsNotAnInteger(self.acadl_object,
                                        self.acadl_object.latency)

        with open(self.pipeline_stage_verilog_template_path) as f:
            verilog_template = Template(f.read())

        with open(target_dir_path + f"/{self.name}_{self.verilog_file_name}",
                  "w+") as f:
            f.write(
                verilog_template.render(
                    name=self.name,
                    latency=self.acadl_object.latency,
                    instruction_size=self.instruction_size))

    def generate_test_bench(self, target_dir_path: str) -> None:
        # test bench files can only be generated into an empty target_dir
        if len(os.listdir(target_dir_path)) != 0:
            raise TargetDirNotEmptyException(target_dir_path)

        # generate verilog
        self.generate_verilog(target_dir_path)

        # generate SystemC testbench
        with open(self.tb_template_path) as f:
            tb_template = Template(f.read())

        with open(target_dir_path + f"/{self.name}_{self.tb_file_name}",
                  "w+") as f:
            f.write(
                tb_template.render(name=self.name,
                                   latency=self.acadl_object.latency,
                                   instruction_size=self.instruction_size))

        # generate CMakeLists.txt
        with open(self.pipeline_stage_template_dir_path +
                  "/CMakeLists.txt") as f:
            cmake_lists_template = Template(f.read())

        with open(target_dir_path + f"/CMakeLists.txt", "w+") as f:
            f.write(cmake_lists_template.render(name=self.name))
