import os

from acadl import ACADLObject


class TargetDirNotEmptyException(Exception):

    def __init__(self, target_dir_path):
        self.target_dir_path = target_dir_path

    def __str__(self):
        return f"Target directory '{self.target_dir_path}' not empty!"


class LatencyIsNotAnInteger(Exception):

    def __init__(self, acadl_object, latency):
        self.acadl_object = acadl_object
        self.latency = latency

    def __str__(self):
        return f"Latency {self.latency} of {type(self.acadl_object)} {self.acadl_object.name} is not an integer!"


class ACADLObjectVerilogTemplate():

    def __init__(self, acadl_object: ACADLObject) -> None:
        self.acadl_object = acadl_object
        dir_path = os.path.dirname(os.path.realpath(__file__))
        self.name = acadl_object.name
        self.verilog_template_dir_path = dir_path + "/verilog_templates/"

    def generate_verilog(self, target_dir_path: str) -> None:
        pass

    def generate_test_bench(self,
                            target_dir_path: str,
                            ignore_target_dir_contents: bool = False) -> None:
        if not ignore_target_dir_contents:
            file_list = os.listdir(target_dir_path)

            if '.gitkeep' in file_list:
                file_list.remove('.gitkeep')

            if len(file_list) != 0:
                raise TargetDirNotEmptyException(target_dir_path)
