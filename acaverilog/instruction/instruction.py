from acadl import Instruction as ACADLInstruction
from .instruction_format import InstructionFormat
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
                 instruction_format: InstructionFormat):
        self.acadl_instruction = acadl_instruction
        # TODO infer target id from AG
        self.target_id = target_id
        self.instruction_format = instruction_format

    def generate_bitarray(self):
        # TODO generate bits for all config fields
        #np_array = np.zeros(self.instruction_format.length, dtype=bool)

        target_id_bits = int2ba(self.target_id, endian='little')

        bits = zeros(self.instruction_format.length, endian='little')

        for target_id_i, bits_i in enumerate(
                range(self.instruction_format.target_id_config.start_bit,
                      self.instruction_format.target_id_config.end_bit + 1)):
            if target_id_i < len(target_id_bits):
                bits[bits_i] = target_id_bits[target_id_i]

        return bits

    def __repr__(self):
        return f"{self.acadl_instruction.__repr__()}; target_id={self.target_id}"
