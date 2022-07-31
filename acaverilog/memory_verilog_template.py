import os

from .acadl_object_verilog_template import ACADLObjectVerilogTemplate, LatencyIsNotAnInteger, TargetDirNotEmptyException
from acadl import Memory

from jinja2 import Template


class MemoryAddressRangesOverlap(Exception):

    def __init__(self, memory):
        self.memory = memory

    def __str__(self):
        return f"Address ranges {self.memory.address_ranges} of {type(self.memory)} {self.memory.name} overlap!"


class MemoryVerilogTemplate(ACADLObjectVerilogTemplate):

    def __init__(self, memory: Memory) -> None:
        super().__init__(memory)

        self.memory_verilog_file_name = "Memory.v"
        self.address_translator_verilog_file_name = "AddressTranslator.v"
        self.tb_file_name = "Memory_tb.cc"

        # check if latencies are integers
        if self.acadl_object.read_latency.int_latency == -1:
            raise LatencyIsNotAnInteger(self.acadl_object,
                                        self.acadl_object.read_latency)

        if self.acadl_object.write_latency.int_latency == -1:
            raise LatencyIsNotAnInteger(self.acadl_object,
                                        self.acadl_object.write_latency)

        # sort address ranges by first address of tuple
        self.address_ranges = sorted(self.acadl_object.address_ranges,
                                     key=lambda x: x[0])

        # check that address ranges don't overlap
        previous_address_range = self.address_ranges[0]
        for current_address_range in self.address_ranges[1:]:
            if previous_address_range[1] > current_address_range[0]:
                raise MemoryAddressRangesOverlap(self.acadl_object)

        # calculate memory lines
        self.lines = 0
        for address_range in self.address_ranges:
            self.lines += len(range(address_range[0], address_range[1]))

        self.address_translation_map = {}
        last_address_of_previous_translated_address_range = 0
        for address_range in self.address_ranges:
            self.address_translation_map[address_range] = -address_range[
                0] + last_address_of_previous_translated_address_range
            last_address_of_previous_translated_address_range = address_range[
                0] + self.address_translation_map[
                    address_range] + address_range[1] - address_range[0]

        # calculate address_width
        self.address_width = 16

        self.memory_template_dir_path = f"{self.verilog_template_dir_path}/memory"
        self.memory_verilog_template_path = f"{self.memory_template_dir_path}/{self.memory_verilog_file_name}"
        self.address_translator_verilog_template_path = f"{self.memory_template_dir_path}/{self.address_translator_verilog_file_name}"
        self.tb_template_path = f"{self.memory_template_dir_path}/{self.tb_file_name}"

    def generate_verilog(self, target_dir_path: str) -> None:
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
                    address_width=self.address_width))

        # generate address translator verilog
        with open(self.address_translator_verilog_template_path) as f:
            address_translator_verilog_template = Template(f.read())

        with open(
                target_dir_path +
                f"/{self.name}_{self.address_translator_verilog_file_name}",
                "w+") as f:
            f.write(
                address_translator_verilog_template.render(
                    name=self.name,
                    address_width=self.address_width,
                    address_translation_map=self.address_translation_map))

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
