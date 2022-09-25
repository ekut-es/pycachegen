import os
import glob
import shutil
import subprocess

from bitarray import bitarray
from typing import List
from .instruction.instruction import Instruction
from jinja2 import Template

__verilator_root_path__ = os.path.dirname(
    os.path.abspath(__file__)) + '/../external/verilator'
__systemc_home_path__ = os.path.dirname(
    os.path.abspath(__file__)) + '/../systemc-2.3.3'

__verilator_cmakelists_dir_path__ = os.path.dirname(
    os.path.abspath(__file__)) + '/'


def ba_to_little_endian_str(bits: bitarray) -> str:
    return str(bits.to01())[::-1]


def read_write_template(path_to_template_file: str, path_to_target_file: str,
                        **kwargs):
    # open template file
    with open(path_to_template_file, "r") as f:
        template = Template(f.read())

    # write target file
    with open(path_to_target_file, "w") as f:
        f.write(template.render(kwargs))


class PathDoesNotExist(Exception):

    def __init__(self, human_readable_path_name, dir_path):
        self.human_readable_path_name = human_readable_path_name
        self.dir_path = dir_path

    def __str__(self):
        return f"{self.human_readable_path_name} '{self._dir_path}' does not exist!"


def is_verilator_installed():
    verilator_path = __verilator_root_path__ + '/bin/verilator'

    # check if verilator binary exists
    if not os.path.exists(verilator_path):
        print(f"does not exist: {verilator_path}")

    verilator_version_cmd = [verilator_path, '--version']
    cmd = ' '.join(verilator_version_cmd)
    output = subprocess.check_output(cmd, shell=True)

    return "Verilator 4.224" in str(output)


def is_systemc_installed():
    files_and_dirs = os.listdir(__systemc_home_path__)
    return 'lib' in files_and_dirs and 'share' in files_and_dirs and 'include' in files_and_dirs


class VerilateFailed(Exception):

    def __str__(self):
        return "Verilate Failed!"


def verilate(build_dir_path: str,
             verilog_out_dir_path: str,
             clean_build_dir: bool = False) -> None:

    # check if build directory exists and if not create it
    if not os.path.isdir(build_dir_path):
        os.mkdir(build_dir_path)

    # check if verilog_out_dir_path exists
    if not os.path.isdir(verilog_out_dir_path):
        raise PathDoesNotExist('Verilog output directory',
                               verilog_out_dir_path)

    # clean directory
    if clean_build_dir:
        dir_contents = glob.glob(build_dir_path + '/*')
        for dir_content in dir_contents:
            if os.path.isdir(dir_content):
                shutil.rmtree(dir_content)
            else:
                os.remove(dir_content)

    # run cmake
    cmake_command = [
        'cmake', '-GNinja', f'-DVERILATOR_ROOT="{__verilator_root_path__}"',
        f'-DSYSTEMC_HOME="{__systemc_home_path__}"',
        f'-DVERILOG_OUT_DIR_PATH="{verilog_out_dir_path}"',
        __verilator_cmakelists_dir_path__
    ]
    cmake_command = ' '.join(cmake_command)

    cmake_subprocess = subprocess.Popen(cmake_command,
                                        cwd=build_dir_path,
                                        shell=True,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT)

    stdout_iterator = iter(cmake_subprocess.stdout.readline, b"")

    for line in stdout_iterator:
        print(line.decode("utf-8"), end="")

    # run ninja
    ninja_command = 'ninja'

    ninja_subprocess = subprocess.Popen(ninja_command,
                                        cwd=build_dir_path,
                                        shell=True,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT)

    stdout_iterator = iter(ninja_subprocess.stdout.readline, b"")

    for line in stdout_iterator:
        print(line.decode("utf-8"), end="")

    streamdata = ninja_subprocess.communicate()[0]
    return_code = ninja_subprocess.returncode

    if return_code != 0:
        raise VerilateFailed


class SimulationTargetDoesNotExist(Exception):

    def __init__(self, simulation_target_path):
        self.simulation_target_path = simulation_target_path

    def __str__(self):
        return f"Simulation target '{self.simulation_target_path}' does not exist!"


class SimulationFailed(Exception):

    def __str__(self):
        return f"Simulation failed!"


def simulate(simulation_target_path: str, args: List[str] = None) -> None:
    # check if simulation target exists
    if not os.path.exists(simulation_target_path):
        raise SimulationTargetDoesNotExist(simulation_target_path)

    if args is not None:
        simluation_command = './' + simulation_target_path + ' ' + ' '.join(
            args)
    else:
        simluation_command = './' + simulation_target_path

    simulation_subprocess = subprocess.Popen(simluation_command,
                                             shell=True,
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.STDOUT)

    stdout_iterator = iter(simulation_subprocess.stdout.readline, b"")

    for line in stdout_iterator:
        print(line.decode("utf-8"), end="")

    streamdata = simulation_subprocess.communicate()[0]
    return_code = simulation_subprocess.returncode

    if return_code != 0:
        raise SimulationFailed
