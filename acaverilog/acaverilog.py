from typing import List, Dict

from acadl import (
    ArchitectureGraph,
    Memory,
    InstructionMemoryAccessUnit,
    RegisterFile,
    InstructionFetchStage,
    PipelineStage,
    ExecuteStage,
    FunctionalUnit,
    MemoryAccessUnit,
    ACADLEdge,
    Instruction as ACADLInstruction,
)
from acadl.utils import get_acadl_objects_from_instruction_memory_to_functional_unit

from .instruction.instruction import Instruction
from .instruction.instruction_format import InstructionFormat
from .instruction.id_config import IdConfig
from .instruction.target_id_config import TargetIdConfig
from .instruction.opcode_config import OpcodeConfig
from .generators.pipeline_stage_generator import PipelineStageGenerator


def generate_from_architecture_graph(
        ag: ArchitectureGraph,
        acadl_instruction_trace: List[ACADLInstruction]) -> None:

    pipeline_stages: List[PipelineStage] = list(ag.pipeline_stages)
    execute_stages: List[ExecuteStage] = list(ag.execute_stages)
    instruction_fetch_stages: List[InstructionFetchStage] = list(
        ag.instruction_fetch_stages)
    functional_units: List[FunctionalUnit] = list(ag.functional_units)
    memory_access_units: List[MemoryAccessUnit] = list(ag.memory_access_units)
    instruction_memory_access_units: List[InstructionMemoryAccessUnit] = list(
        ag.instruction_memory_access_units)
    register_files: List[RegisterFile] = list(ag.register_files)
    memories: List[Memory] = list(ag.memories)
    instruction_memories: List[Memory] = list(ag.get_instruction_memories())
    instruction_memory: Memory = instruction_memories[0]

    if len(instruction_memories) != 1:
        raise Exception("Multiple instruction memories are not supported.")

    # determine forward lookup maps for each pipeline stage
    forward_lookup_maps: Dict[PipelineStage, Dict[int, int]] = {}
    target_id_count: int = 0
    for fu in functional_units:
        target_id_count += 1
        instruction_path_objects = get_acadl_objects_from_instruction_memory_to_functional_unit(
            ag, instruction_memory, fu)
        for i in range(len(instruction_path_objects) - 1):
            if type(instruction_path_objects[i]) is PipelineStage:
                if instruction_path_objects[i] not in forward_lookup_maps:
                    forward_lookup_maps[instruction_path_objects[i]] = {}
                forward_lookup_maps[
                    instruction_path_objects[i]][target_id_count] = i + 1

    # build instruction format
    instruction_ids: List[int] = []
    for instruction in acadl_instruction_trace:
        instruction_ids.append(instruction.id)
    id_config: IdConfig = IdConfig(0, max(instruction_ids))
    target_id_config: TargetIdConfig = TargetIdConfig(id_config.end_bit + 1,
                                                      target_id_count)
    opcode_config: OpcodeConfig = OpcodeConfig(target_id_config.end_bit + 1,
                                               1)  # 1 bit for load/store
    instruction_format: InstructionFormat = InstructionFormat(
        id_config, target_id_config, opcode_config)

    # generate instruction objects
    instructions: List[Instruction] = []
    for acadl_instruction in acadl_instruction_trace:
        target_fu = ag.get_target_functional_unit_of_instruction(
            acadl_instruction)
        target_id = functional_units.index(target_fu) + 1
        instructions.append(
            Instruction(acadl_instruction, target_id, instruction_format))

    for ps in pipeline_stages:
        forward_port_map: Dict[int, int] = forward_lookup_maps[ps]
        ps_gen = PipelineStageGenerator(ps, instruction_format,
                                        forward_port_map)
        #ps_gen.generate(target_dir_path)
