from .acadl_object_verilog_template import ACADLObjectVerilogTemplate
from acadl import PipelineStage

from jinja2 import Template


class PipelineStageVerilogTemplate(ACADLObjectVerilogTemplate):

    def __init__(self, pipeline_stage: PipelineStage,
                 instruction_size: int) -> None:
        super().__init__(pipeline_stage)

        self.verilog_file_name = "PipelineStage.v"
        self.tb_file_name = "PipelineStage_tb.cc"

        self.instruction_size = instruction_size

        self.verilog_template_path = self.verilog_template_dir_path + f"/pipeline_stage/{self.verilog_file_name}"
        self.tb_template_path = self.verilog_template_dir_path + "/pipeline_stage/PipelineStage_tb.cc"

    def generate_verilog(self, target_dir_path: str) -> None:
        with open(self.verilog_template_path) as f:
            verilog_template = Template(f.read())

        with open(target_dir_path + f"/{self.name}_{self.verilog_file_name}",
                  "w+") as f:
            f.write(
                verilog_template.render(
                    name=self.name, instruction_size=self.instruction_size))

    def generate_test_bench(self, target_dir_path: str) -> None:
        self.generate_verilog(target_dir_path)

        with open(self.tb_template_path) as f:
            tb_template = Template(f.read())

        with open(target_dir_path + f"/{self.name}_{self.tb_file_name}",
                  "w+") as f:
            f.write(
                tb_template.render(name=self.name,
                                   instruction_size=self.instruction_size))
