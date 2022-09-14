from typing import Tuple
from .instruction_format_config import InstructionFormatConfig
from .data_field_config import DataFieldConfig, DataFieldType
from .target_id_config import TargetIdConfig
from .opcode_config import OpcodeConfig


class MissingInstructionFormatConfig(Exception):

    def __init__(self, instruction_format: "InstructionFormat",
                 missing_config: str):
        self.instruction_format = instruction_format
        self.missing_config = missing_config

    def __str__(self):
        return f"InstructionFormat: '{self.instruction_format.name}' is missing config '{self.missing_config}'"


class InstructionFormatConfigsOverlap(Exception):

    def __init__(self, instruction_format: "InstructionFormat",
                 overlapping_configs: Tuple[InstructionFormatConfig]):
        self.instruction_format = instruction_format
        self.overlapping_configs = overlapping_configs

    def __str__(self):
        return f"InstructionFormat '{self.instruction_format}' has overlapping configs: {self.overlapping_configs[0]}, {self.overlapping_configs[1]}]"


class InstructionFormat:

    def __init__(self, name: str, length: int,
                 target_id_config: TargetIdConfig, opcode_config: OpcodeConfig,
                 read_registers_config: DataFieldConfig,
                 write_registers_config: DataFieldConfig,
                 read_addresses_config: DataFieldConfig,
                 write_addresses_config: DataFieldConfig,
                 immediates_config: DataFieldConfig):

        self.name = name
        self.length = length
        self.target_id_config = target_id_config
        self.opcode_config = opcode_config
        self.read_registers_config = read_registers_config
        self.write_registers_config = write_registers_config
        self.read_addresses_config = read_addresses_config
        self.write_addresses_config = write_addresses_config
        self.immediates_config = immediates_config

        self.configs = [
            self.target_id_config, self.opcode_config,
            self.read_registers_config, self.write_registers_config,
            self.read_addresses_config, self.write_addresses_config,
            self.immediates_config
        ]

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
                                                     data_field_type_to_check)

        # insert each config into bits and check if bits are already set
        self.bits = [None] * self.length

        for i in range(target_id_config.start_bit,
                       target_id_config.end_bit + 1):
            self.bits[i] = target_id_config

        configs_to_check = self.configs[1:]

        for config_to_check in configs_to_check:
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
        return self.name + ": " + ', '.join(
            map(lambda x: x.__repr__(), configs_sorted_by_position))
