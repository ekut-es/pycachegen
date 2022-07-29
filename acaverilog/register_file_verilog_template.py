from .acadl_object_verilog_template import ACADLObjectVerilogTemplate
from acadl import RegisterFile

from jinja2 import Template


class RegisterFileVerilogTemplate(ACADLObjectVerilogTemplate):

    def __init__(self, register_file: RegisterFile) -> None:
        super().__init__(register_file)

        self.register_file_template_dir_path = f"{self.verilog_template_dir_path}/register_file"
        self.register_file_verilog_template_path = f"{self.register_file_template_dir_path}/RegisterFile.v"
        self.tb_template_path = f"{self.register_file_template_dir_path}/RegisterFile_tb.cc"

    def generate_verilog(self, target_dir_path: str) -> None:
        # generate register file verilog
        with open(self.pipeline_stage_verilog_template_path) as f:
            register_file_verilog_template = Template(f.read())
