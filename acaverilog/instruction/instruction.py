from acadl import Instruction as ACADLInstruction
from .instruction_format import InstructionFormat
from .instruction_format_config import InstructionFormatConfig
from bitarray.util import int2ba, zeros, ba2hex, ba2int
from typing import List


def create_memory_file_from_instructions(memory_file_path: str,
                                         instructions: List["Instruction"],
                                         instruction_length: int):
    with open(memory_file_path, "w") as memory_file:
        for instruction in instructions:
            hex_instruction = f"{ba2int(instruction.generate_bitarray()):x}".zfill(
                instruction_length // 4)
            memory_file.write(f"{hex_instruction}\n")


class Instruction:

    def __init__(self, acadl_instruction: ACADLInstruction, target_id: int,
                 instruction_format: InstructionFormat) -> None:
        self.acadl_instruction = acadl_instruction
        self.target_id = target_id
        self.instruction_format = instruction_format

        self.generate_data()
        self.generate_bitarray()

    def generate_data(self) -> None:
        self.data: List[int] = []

        self.id = self.acadl_instruction.id
        self.data.append(self.id)
        self.data.append(self.target_id)

        if self.instruction_format.opcode_config is not None:
            if self.acadl_instruction.operation == "store":
                self.opcode = 1
            else:
                self.opcode = 0
            self.data.append(self.opcode)

    def generate_bitarray(self) -> None:
        self.bits = zeros(self.instruction_format.length, endian='little')

        for i, data in enumerate(self.data):
            start_bit = self.instruction_format.configs[i].start_bit
            end_bit = self.instruction_format.configs[i].end_bit
            self.bits[start_bit:end_bit] = int2ba(
                data,
                length=self.instruction_format.configs[i].length,
                endian='little')

    def __repr__(self) -> str:
        return f"{self.acadl_instruction.__repr__()}; target_id={self.target_id}"
