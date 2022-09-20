import os
import sys
import subprocess
from pathlib import Path

import distutils

from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext

from setuptools.command.develop import develop as develop_orig
from setuptools.command.install import install as install_orig

from shutil import which


class develop(develop_orig):

    def run(self):
        print("editable install (entry point)")
        global editable_install
        editable_install = True
        super().run()


class install(install_orig):

    def run(self):
        print("non-editable install (entry point)")
        super().run()


class CMakeExtension(Extension):

    def __init__(self, name):
        Extension.__init__(self, name, sources=[])


class CMakeBuild(build_ext):

    def run(self):
        # check if cmake is installed
        try:
            out = subprocess.check_output(['cmake', '--version'])
        except OSError:
            raise RuntimeError(
                "CMake must be installed to build the following extensions: " +
                ", ".join(e.name for e in self.extensions))

        # run cmake
        acaverilog_dir_path = os.path.dirname(os.path.abspath(__file__))
        build_directory = os.path.abspath(self.build_temp)
        cmake_list_dir = os.path.abspath(os.path.dirname(__file__))
        env = os.environ.copy()

        print(
            f"build dir path: {build_directory} ? {os.path.isdir(build_directory)}"
        )

        # check if build dir exists
        if not os.path.exists(self.build_temp):
            os.makedirs(self.build_temp)

        # run cmake command
        cmake_cmd = ['cmake', cmake_list_dir]
        subprocess.check_call(cmake_cmd, cwd=self.build_temp, env=env)

        # run make command to compile and install verilator and systemc
        make_cmd = ['make']
        subprocess.check_call(make_cmd, cwd=self.build_temp, env=env)


ext_modules = [
    CMakeExtension('acaverilog'),
]

setup(name="acaverilog",
      version="1.0.0",
      packages=["acaverilog"],
      package_dir={"acaverilog": "acaverilog"},
      zip_safe=False)

setup(
    name="acaverilog",
    version="1.0.0",
    packages=["acaverilog"],
    package_dir={"acaverilog": "acaverilog"},
    ext_modules=ext_modules,
    cmdclass={
        'develop': develop,
        'install': install,
        'build_ext': CMakeBuild
    },
    zip_safe=False,
)
