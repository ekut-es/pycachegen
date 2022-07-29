import os

from .acadl_object_verilog_template import ACADLObjectVerilogTemplate, LatencyIsNotAnInteger, TargetDirNotEmptyException
from acadl import Memory

from jinja2 import Template


class MemoryVerilogTemplate(ACADLObjectVerilogTemplate):

    def __init__(self, memory: Memory) -> None:
        super().__init__(memory)

        self.memory_verilog_file_name = "Memory.v"
        self.tb_file_name = "Memory_tb.cc"

        self.memory_template_dir_path = f"{self.verilog_template_dir_path}/memory"
        self.memory_verilog_template_path = f"{self.memory_template_dir_path}/{self.memory_verilog_file_name}"
        self.tb_template_path = f"{self.memory_template_dir_path}/{self.tb_file_name}"

    def generate_verilog(self, target_dir_path: str) -> None:
        # check if latencies are integers
        if self.acadl_object.read_latency.int_latency == -1:
            raise LatencyIsNotAnInteger(self.acadl_object,
                                        self.acadl_object.read_latency)

        if self.acadl_object.write_latency.int_latency == -1:
            raise LatencyIsNotAnInteger(self.acadl_object,
                                        self.acadl_object.write_latency)

        # generate memory stage verilog
        with open(self.memory_verilog_template_path) as f:
            memory_verilog_template = Template(f.read())

        with open(
                target_dir_path +
                f"/{self.name}_{self.memory_verilog_file_name}", "w+") as f:
            f.write(
                memory_verilog_template.render(
                    name=self.name,
                    data_width=self.acadl_object.data_width,
                    max_concurrent_requests=self.acadl_object.
                    max_concurrent_requests,
                    read_write_ports=self.acadl_object.read_write_ports,
                    port_width=self.acadl_object.port_width,
                    read_latency=self.acadl_object.read_latency,
                    write_latency=self.acadl_object.write_latency,
                    address_width=16  #TODO
                ))

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
                tb_template.render(
                    name=self.name,
                    data_width=self.acadl_object.data_width,
                    max_concurrent_requests=self.acadl_object.
                    max_concurrent_requests,
                    read_write_ports=self.acadl_object.read_write_ports,
                    port_width=self.acadl_object.port_width,
                    read_latency=self.acadl_object.read_latency,
                    write_latency=self.acadl_object.write_latency,
                    address_width=16  #TODO
                ))

        # generate CMakeLists.txt
        with open(self.memory_template_dir_path + "/CMakeLists.txt") as f:
            cmake_lists_template = Template(f.read())

        with open(target_dir_path + f"/CMakeLists.txt", "w+") as f:
            f.write(cmake_lists_template.render(name=self.name))
