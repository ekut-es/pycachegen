import os
from typing import Dict, Any

from veriloggen import Module
import veriloggen.core.vtypes as vtypes

from ..exceptions import TargetDirNotEmptyException
from ..utils import load_file_to_string, read_write_template


class ModuleGenerator():

    def __init__(self,
                 instance_name: str,
                 object_name: str = "Module") -> None:
        self.instance_name = instance_name
        self.object_name = object_name

        self.dir_path = os.path.dirname(os.path.realpath(__file__))
        self.templates_dir_path = self.dir_path + "/../templates"
        self.tb_testing_templates_dir_path = self.templates_dir_path + "/tb_tests"

        self.cmakelists_template_file_name = "CMakeLists_template.txt"
        self.tb_template_file_name = "tb.cc_template"
        self.tb_tests_file_name = self.object_name + "_tb_tests.cc_template"

        self.base_file_name = self.instance_name + "_" + self.object_name
        self.verilog_file_name = self.base_file_name + ".v"
        self.tb_base_file_name = self.base_file_name + "_tb"
        self.tb_file_name = self.tb_base_file_name + ".cc"

    def generate_module(self) -> Module:
        return Module(self.base_file_name)

    def generate_verilog(self,
                         target_dir_path: str,
                         ignore_target_dir_contents: bool = False) -> str:
        if not ignore_target_dir_contents:
            file_list = os.listdir(target_dir_path)

            if '.gitkeep' in file_list:
                file_list.remove('.gitkeep')

            if len(file_list) != 0:
                raise TargetDirNotEmptyException(target_dir_path)

        if not os.path.isdir(target_dir_path):
            os.mkdir(target_dir_path)

        m = self.generate_module()

        return m.to_verilog(target_dir_path + f"/{self.verilog_file_name}",
                            for_verilator=True)

    def _generate_port_tb_kwargs(self) -> Dict[str, Any]:
        ports = self.generate_module().get_ports()

        kwarg_clk: str = ""
        kwarg_reset: str = ""
        kwarg_inputs: Dict[str, str] = {}
        kwarg_outputs: Dict[str, str] = {}
        kwarg_snake_case_object_name: str = ''.join([
            '_' + i.lower() if i.isupper() else i for i in self.object_name
        ]).lstrip('_')

        for name, port in ports.items():
            if name in ['clk_i', 'clk', 'clock', 'clock_i']:
                kwarg_clk = name
            elif name in ['reset_n_i', 'reset', 'reset_i']:
                kwarg_reset = name
            elif isinstance(port, vtypes.Input):
                if isinstance(port.width, vtypes.Parameter):
                    port.width = port.width.value
                if port.width is None or port.width <= 1:
                    kwarg_inputs[name] = 'bool'
                elif port.width <= 32:
                    kwarg_inputs[name] = 'uint32_t'
                else:
                    kwarg_inputs[name] = f"sc_bv<{port.width}>"
            elif isinstance(port, vtypes.Output):
                if isinstance(port.width, vtypes.Parameter):
                    port.width = port.width.value
                if port.width is None or port.width <= 1:
                    kwarg_outputs[name] = 'bool'
                elif port.width <= 32:
                    kwarg_outputs[name] = 'uint32_t'
                else:
                    kwarg_outputs[name] = f"sc_bv<{port.width}>"

        return {
            'kwarg_clk': kwarg_clk,
            'kwarg_reset': kwarg_reset,
            'kwarg_inputs': kwarg_inputs,
            'kwarg_outputs': kwarg_outputs,
            'kwarg_snake_case_object_name': kwarg_snake_case_object_name
        }

    def generate_test_bench(self,
                            target_dir_path: str,
                            ignore_target_dir_contents: bool = False,
                            default_runtime_ns: int = 0,
                            use_cassert: bool = False,
                            **kwargs) -> None:
        if not ignore_target_dir_contents:
            file_list = os.listdir(target_dir_path)

            if '.gitkeep' in file_list:
                file_list.remove('.gitkeep')

            if len(file_list) != 0:
                raise TargetDirNotEmptyException(target_dir_path)

        if not os.path.isdir(target_dir_path):
            os.mkdir(target_dir_path)

        # copy assertv
        os.system(f"cp {self.templates_dir_path}/assertv.h {target_dir_path}")

        # generate SystemC testbench
        port_tb_kwargs: Dict[str, Any] = self._generate_port_tb_kwargs()
        kwarg_tests: str = load_file_to_string(
            self.tb_testing_templates_dir_path + f"/{self.tb_tests_file_name}")
        read_write_template(self.templates_dir_path +
                            f"/{self.tb_template_file_name}",
                            target_dir_path + f"/{self.tb_file_name}",
                            default_vcd_dir_path=target_dir_path,
                            use_cassert=use_cassert,
                            base_file_name=self.base_file_name,
                            kwarg_tests=kwarg_tests,
                            default_runtime_ns=default_runtime_ns,
                            **port_tb_kwargs,
                            **kwargs)

        # generate CMakeLists.txt
        read_write_template(self.templates_dir_path +
                            f"/{self.cmakelists_template_file_name}",
                            target_dir_path + f"/CMakeLists.txt",
                            tb_base_file_name=self.tb_base_file_name,
                            tb_file_name=self.tb_file_name,
                            verilog_file_name=self.verilog_file_name)
