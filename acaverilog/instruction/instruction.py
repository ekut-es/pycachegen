from acadl import Instruction as ACADLInstruction
from .instruction_format import InstructionFormat


class Instruction:

    def __init__(self, acadl_instruction: ACADLInstruction,
                 instruction_format: InstructionFormat):
        self.acadl_instruction = acadl_instruction
        self.instruction_format = instruction_format
