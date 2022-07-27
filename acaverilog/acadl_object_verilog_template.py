import os

from acadl import ACADLObject


class ACADLObjectVerilogTemplate():

    def __init__(self, acadl_object: ACADLObject) -> None:
        self.acadl_object = acadl_object
        dir_path = os.path.dirname(os.path.realpath(__file__))
        self.name = acadl_object.name
        self.verilog_template_dir_path = dir_path + "/verilog_templates/"

    def generate_verilog(self, target_dir_path: str) -> None:
        pass
