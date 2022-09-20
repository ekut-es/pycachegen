import os
import glob
import shutil
import subprocess

from bitarray import bitarray
from typing import List
from .instruction.instruction import Instruction

__verilator_root_path__ = os.path.dirname(
    os.path.abspath(__file__)) + '/../external/verilator'
__systemc_home_path__ = os.path.dirname(
    os.path.abspath(__file__)) + '/../systemc-2.3.3'


def ba_to_little_endian_str(bits: bitarray) -> str:
    return str(bits.to01())[::-1]


class TargetDirPathDoesNotExist(Exception):

    def __init__(self, target_dir_path):
        self.target_dir_path = target_dir_path

    def __str__(self):
        return f"Target directory '{self.target_dir_path}' does not exist!"


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


def verilate(build_dir_path: str,
             target_dir_path: str,
             clean_build_dir: bool = False) -> None:
    # check if target_dir_path exists
    if not os.path.isdir(target_dir_path):
        raise TargetDirPathDoesNotExist(target_dir_path)

    # check if build directory exists and if not create it
    if not os.path.isdir(build_dir_path):
        os.mkdir(build_dir_path)

    # clean directory
    if clean_build_dir:
        dir_contents = glob.glob(build_dir_path + '/*')
        for dir_content in dir_contents:
            if os.path.isdir(dir_content):
                shutil.rmtree(dir_content)
            else:
                os.remove(dir_content)

    # run cmake
    current_file_dir_path = os.path.dirname(os.path.abspath(__file__))
    cmake_command = [
        'cmake', '-GNinja', f'-DVERILATOR_ROOT="{__verilator_root_path__}"',
        f'-DSYSTEMC_HOME="{__systemc_home_path__}"', '..'
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


class SimulationTargetDoesNotExist(Exception):

    def __init__(self, simulation_target_path):
        self.simulation_target_path = simulation_target_path

    def __str__(self):
        return f"Simulation target '{self.simulation_target_path}' does not exist!"


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
