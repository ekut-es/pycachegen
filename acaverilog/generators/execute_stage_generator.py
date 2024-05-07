from typing import Dict

from acadl import ExecuteStage

from .pipeline_stage_generator import PipelineStageGenerator
from ..instruction.instruction_format import InstructionFormat


class ExecuteStageGenerator(PipelineStageGenerator):

    def __init__(
        self,
        execute_stage: ExecuteStage,
        instruction_format: InstructionFormat,
        forward_port_map: Dict[int, int],
    ) -> None:
        super().__init__(execute_stage, instruction_format, forward_port_map)
