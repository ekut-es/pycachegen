import os
from math import ceil, log2
from typing import Dict, List
from veriloggen import Module, Submodule, Posedge, Negedge, If, For, AndList, Cond, Systask

from .module_generator import ModuleGenerator
from ..instruction.instruction_format import InstructionFormat


class TestGenerator(ModuleGenerator):

    def __init__(
        self,
        instance_name: str,
    ) -> None:
        super().__init__(instance_name, 'Test')

    def generate_module(self) -> Module:

        m = Module('Test')

        reset_n_i = m.Input('reset_n_i')
        clk_i = m.Input('clk_i')

        array = m.Reg('array', dims=6, width=9)

        m.Always(Posedge(clk_i),
                 Negedge(reset_n_i))(If(reset_n_i == 0)(Systask(
                     'writememb', 'table.txt', array)).Else(
                         array[0](1),
                         array[1](2),
                         array[2](3),
                         array[3](4),
                     ))

        return m
