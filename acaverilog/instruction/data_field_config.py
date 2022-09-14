from .instruction_format_config import InstructionFormatConfig
from enum import Enum


class DataFieldType(Enum):
    READ_REGISTER = 0
    WRITE_REGISTER = 1
    READ_ADDRESS = 2
    WRITE_ADDRESS = 3
    IMMEDIATE = 4


class DataFieldConfig(InstructionFormatConfig):

    def __init__(self,
                 start_bit: int,
                 data_field_type: DataFieldType,
                 num_fields: int = 0,
                 field_length: int = 0):
        super().__init__(start_bit)
        self.data_field_type = data_field_type
        self.num_fields = num_fields
        self.field_length = field_length
        self.length = self.field_length * self.num_fields
        self.end_bit = self.start_bit + self.length - 1

    def __repr__(self):
        if self.length == 0:
            return f"DataFieldConfig ({self.data_field_type})=[x:x]"
        else:
            return f"DataFieldConfig ({self.data_field_type})=[{self.start_bit}:{self.end_bit}]"
