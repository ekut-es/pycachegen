from .instruction_format_config import InstructionFormatConfig
from math import ceil, log2


class OpcodeConfig(InstructionFormatConfig):

    def __init__(self, start_bit: int, max_id: int):
        self.start_bit = start_bit
        self.max_id = max_id
        self.length = ceil(log2(self.max_id + 1))
        self.end_bit = self.start_bit + self.length - 1

    def __repr__(self):
        return f"OpcodeConfig=[{self.end_bit}:{self.start_bit}]"
