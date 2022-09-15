import os

from acadl import Memory
from .acadl_object_verilog_template import TargetDirNotEmptyException
from .memory_verilog_template import MemoryVerilogTemplate
from jinja2 import Template


class InstructionMemoryInstantiationWithoutInstructions(Exception):

    def __init__(self, memory):
        self.memory = memory

    def __str__(self):
        return f"Instruction memory '{self.memory.name}' verilog instantiated without file that contains instructions!"


class InstructionMemoryVerilogTemplate(MemoryVerilogTemplate):

    def __init__(self, memory: Memory, memory_file_path: str = None) -> None:
        # check if instructions are provided
        if memory_file_path is None:
            raise InstructionMemoryInstantiationWithoutInstructions(
                self.acadl_object)

        super().__init__(memory, memory_file_path)

        self.tb_file_name = "InstructionMemory_tb.cc"
        self.instruction_memory_template_dir_path = f"{self.verilog_template_dir_path}/instruction_memory"
        self.tb_template_path = f"{self.instruction_memory_template_dir_path}/{self.tb_file_name}"

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
            f.write(tb_template.render(name=self.name))

        # generate CMakeLists.txt
        with open(self.instruction_memory_template_dir_path +
                  "/CMakeLists.txt") as f:
            cmake_lists_template = Template(f.read())

        with open(target_dir_path + f"/CMakeLists.txt", "w+") as f:
            f.write(cmake_lists_template.render(name=self.name))
