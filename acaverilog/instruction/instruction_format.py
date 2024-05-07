from __future__ import annotations
from typing import Tuple, Optional, List

from acadl import Instruction as ACADLInstruction

from .instruction_format_config import InstructionFormatConfig
from .id_config import IdConfig
from .data_field_config import DataFieldConfig, DataFieldType
from .target_id_config import TargetIdConfig
from .opcode_config import OpcodeConfig


class MissingInstructionFormatConfig(Exception):

    def __init__(self, instruction_format: InstructionFormat,
                 missing_config: str):
        self.instruction_format = instruction_format
        self.missing_config = missing_config

    def __str__(self):
        return f"'{self.instruction_format}' is missing config '{self.missing_config}'"


class InstructionFormatConfigsOverlap(Exception):

    def __init__(self, instruction_format: InstructionFormat,
                 overlapping_config_1: InstructionFormatConfig,
                 overlapping_config_2: InstructionFormatConfig):
        self.instruction_format = instruction_format
        self.overlapping_config_1 = overlapping_config_1
        self.overlapping_config_2 = overlapping_config_2

    def __str__(self):
        return f"'{self.instruction_format}' has overlapping configs: {self.overlapping_config_1}, {self.overlapping_config_2}]"


class InstructionFormat:

    def __init__(self,
                 id_config: IdConfig,
                 target_id_config: TargetIdConfig,
                 opcode_config: Optional[OpcodeConfig] = None,
                 read_registers_config: Optional[DataFieldConfig] = None,
                 write_registers_config: Optional[DataFieldConfig] = None,
                 read_addresses_config: Optional[DataFieldConfig] = None,
                 write_addresses_config: Optional[DataFieldConfig] = None,
                 immediates_config: Optional[DataFieldConfig] = None):

        self.id_config = id_config
        self.target_id_config = target_id_config
        self.opcode_config = opcode_config
        self.read_registers_config = read_registers_config
        self.write_registers_config = write_registers_config
        self.read_addresses_config = read_addresses_config
        self.write_addresses_config = write_addresses_config
        self.immediates_config = immediates_config

        self.length: int = id_config.length + target_id_config.length
        self.configs: List[InstructionFormatConfig] = [
            self.id_config, self.target_id_config
        ]
        if opcode_config is not None:
            self.length += opcode_config.length
            self.configs.append(opcode_config)
        if read_registers_config is not None:
            self.length += read_registers_config.length
            self.configs.append(read_registers_config)
        if write_registers_config is not None:
            self.length += write_registers_config.length
            self.configs.append(write_registers_config)
        if read_addresses_config is not None:
            self.length += read_addresses_config.length
            self.configs.append(read_addresses_config)
        if write_addresses_config is not None:
            self.length += write_addresses_config.length
            self.configs.append(write_addresses_config)
        if immediates_config is not None:
            self.length += immediates_config.length
            self.configs.append(immediates_config)
        """
        # check format
        # check if all data field config types are present
        data_field_configs = [
            self.read_registers_config, self.write_registers_config,
            self.read_addresses_config, self.write_addresses_config,
            self.immediates_config
        ]
        set_data_field_types = map(lambda x: x.data_field_type,
                                   data_field_configs)
        data_field_types_to_check = [
            DataFieldType.READ_REGISTER, DataFieldType.WRITE_REGISTER,
            DataFieldType.READ_ADDRESS, DataFieldType.WRITE_ADDRESS,
            DataFieldType.IMMEDIATE
        ]

        for data_field_type_to_check in data_field_types_to_check:
            if not data_field_type_to_check in set_data_field_types:
                raise MissingInstructionFormatConfig(self,
                                                     data_field_type_to_check)"""

        # insert each config into bits and check if bits are already set
        self.bits: List[Optional[InstructionFormatConfig]] = [None
                                                              ] * self.length
        for config_to_check in self.configs:
            for i in range(config_to_check.start_bit,
                           config_to_check.end_bit + 1):
                if self.bits[i] is not None:
                    raise InstructionFormatConfigsOverlap(
                        self, self.bits[i], config_to_check)
                self.bits[i] = config_to_check

    def __repr__(self):
        configs_sorted_by_position = sorted(self.configs,
                                            key=lambda x: x.start_bit,
                                            reverse=True)
        return f"InstructionFormat=[{', '.join(map(str, configs_sorted_by_position))}]"
