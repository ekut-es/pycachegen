from acadl import Instruction as ACADLInstruction
from .instruction_format import InstructionFormat
from bitarray.util import int2ba, zeros


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
