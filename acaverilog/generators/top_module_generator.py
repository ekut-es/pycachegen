from math import ceil, log2
from typing import Dict, List
from veriloggen import Module, Submodule, Posedge, Negedge, If, For, AndList

from acadl import (ArchitectureGraph, Instruction as ACADLInstruction,
                   ACADLEdge, ACADLObject, PipelineStage, ExecuteStage,
                   InstructionFetchStage, FunctionalUnit, MemoryAccessUnit,
                   InstructionMemoryAccessUnit, Memory, RegisterFile)
import acadl.utils as acutils

from .module_generator import ModuleGenerator
from .pipeline_stage_generator import PipelineStageGenerator
from .execute_stage_generator import ExecuteStageGenerator
from .instruction_fetch_stage_generator import InstructionFetchStageGenerator
from .functional_unit_generator import FunctionalUnitGenerator
from .memory_access_unit_generator import MemoryAccessUnitGenerator
# from .instruction_memory_access_unit_generator import InstructionMemoryAccessUnitGenerator
from .register_file_generator import RegisterFileGenerator
from .memory_generator import MemoryGenerator

from ..instruction.instruction import Instruction
from ..instruction.instruction_format import InstructionFormat


class TopModuleGenerator(ModuleGenerator):

    def __init__(
        self,
        name: str,
        architecture_graph: ArchitectureGraph,
        instruction_format: InstructionFormat,
        instruction_list: List[Instruction],
    ) -> None:
        super().__init__(name, 'TopModule')
        self.name = name
        self.architecture_graph = architecture_graph
        self.instruction_format = instruction_format
        self.instruction_list = instruction_list

        self.pipeline_stages: List[PipelineStage] = []
        self.execute_stages: List[ExecuteStage] = []
        self.instruction_fetch_stages: List[InstructionFetchStage] = []
        self.functional_units: List[FunctionalUnit] = []
        self.memory_access_units: List[MemoryAccessUnit] = []
        self.instruction_memory_access_units: List[
            InstructionMemoryAccessUnit] = []
        self.register_files: List[RegisterFile] = []
        self.memories: List[Memory] = []

        self.edges: List[ACADLEdge] = list(architecture_graph.get_edges())

        # determine each object type separately, because of inheritance (e.g. ExecuteStage is a subclass of PipelineStage)
        self.acadl_objects = list(architecture_graph.get_nodes())
        for obj in self.acadl_objects:
            if type(obj) is PipelineStage:
                self.pipeline_stages.append(obj)
            elif type(obj) is ExecuteStage:
                self.execute_stages.append(obj)
            elif type(obj) is InstructionFetchStage:
                self.instruction_fetch_stages.append(obj)
            elif type(obj) is FunctionalUnit:
                self.functional_units.append(obj)
            elif type(obj) is MemoryAccessUnit:
                self.memory_access_units.append(obj)
            elif type(obj) is InstructionMemoryAccessUnit:
                self.instruction_memory_access_units.append(obj)
            elif type(obj) is Memory:
                self.memories.append(obj)
            elif type(obj) is RegisterFile:
                self.register_files.append(obj)

        self.forward_lookup_maps: Dict[PipelineStage, Dict[
            int, int]] = self._determine_forward_lookup_maps()

    def _determine_forward_lookup_maps(
            self) -> Dict[PipelineStage, Dict[int, int]]:
        successors_maps: Dict[PipelineStage, List[ACADLObject]] = {}
        forward_lookup_maps: Dict[PipelineStage, Dict[int, int]] = {}

        for ps in self.pipeline_stages:
            successors_maps[ps] = list(
                self.architecture_graph.forward_successors(ps))
            successors_maps[ps] += list(
                self.architecture_graph.contains_successors(ps))

        target_id: int = 0
        for fu in list(self.architecture_graph.functional_units):
            target_id += 1
            instruction_path_objects = acutils.get_acadl_objects_from_instruction_memory_to_functional_unit(
                fu)
            for i in range(len(instruction_path_objects) - 1):
                if isinstance(instruction_path_objects[i], PipelineStage):
                    if instruction_path_objects[i] not in forward_lookup_maps:
                        forward_lookup_maps[instruction_path_objects[i]] = {}
                    forward_lookup_maps[instruction_path_objects[i]][
                        target_id] = successors_maps[
                            instruction_path_objects[i]].index(
                                instruction_path_objects[i + 1])
        return forward_lookup_maps

    def generate_module(self) -> Module:

        m = Module(self.base_file_name)

        instruction_length = m.Parameter('INSTRUCTION_LENGTH',
                                         self.instruction_length)

        clk_i = m.Input('clk_i')
        reset_n_i = m.Input('reset_n_i')

        pipeline_stages = []
        for ps in self.pipeline_stages:
            forward_port_map = self.forward_lookup_maps[ps]
            ps_module = PipelineStageGenerator(
                ps, self.instruction_format,
                forward_port_map).generate_module()
            pipeline_stages.append(
                Submodule(m,
                          ps_module,
                          f'{ps.instance_name}',
                          arg_ports=(
                              ('clk_i', clk_i), ('reset_n_i', reset_n_i),
                              ('instruction_i',
                               self.architecture_graph.forward_predecessor(ps)(
                                   'instruction_valid_i',
                                   'instruction_valid_i'),
                               ('next_stage_ready_i',
                                f'{len(forward_port_map)}'),
                               ('instruction_o', f'{instruction_length}',
                                f'{len(forward_port_map)}'),
                               ('instruction_valid_o', 'instruction_valid_o',
                                f'{len(forward_port_map)}'), ('ready_o',
                                                              'ready_o')))))

        it = m.Integer('it')
