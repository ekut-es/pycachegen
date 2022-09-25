from .acadl_object_verilog_template import ACADLObjectVerilogTemplate
from .instruction_memory_verilog_template import InstructionMemoryVerilogTemplate
from acadl import Memory, InstructionFetchStage, latency_t
from acadl import Instruction as ACADLInstruction
from .instruction.instruction import Instruction, create_memory_file_from_instructions
from .instruction.target_id_config import TargetIdConfig
from .instruction.opcode_config import OpcodeConfig
from .instruction.data_field_config import DataFieldConfig, DataFieldType
from .instruction.instruction_format import InstructionFormat
from .utils import read_write_template

from jinja2 import Template


class IssueBufferSmallerThanPortWidth(Exception):

    def __init__(self, instruction_fetch_stage: InstructionFetchStage,
                 instruction_memory: Memory):
        self.instruction_fetch_stage = instruction_fetch_stage
        self.instruction_memory = instruction_memory

    def __str__(self):
        return f"InstructionFetchStage '{self.instruction_fetch_stage.name}'.issue_buffer_size = {self.instruction_fetch_stage.issue_buffer_size}! smaller than Memory '{self.instruction_memory.name}.'.port_width = {self.instruction_memory.port_width}!"


class InstructionFetchStageVerilogTemplate(ACADLObjectVerilogTemplate):

    def __init__(
        self, instruction_fetch_stage: InstructionFetchStage,
        instruction_memory_verilog_template: InstructionMemoryVerilogTemplate
    ) -> None:
        super().__init__(instruction_fetch_stage)

        self.instruction_fetch_stage_verilog_file_name = "InstructionFetchStage.v"
        self.pop_count_verilog_file_name = "PopCount.v"
        self.tb_file_name = "InstructionFetchStage_tb.cc"
        self.instruction_memory_fetch_stage_wrapper_verilog_file_name = "InstructionMemoryFetchStageWrapper.v"

        self.instruction_memory_verilog_template = instruction_memory_verilog_template

        # issue_buffer_size has to be at least as large as the port_width
        if self.acadl_object.issue_buffer_size < instruction_memory_verilog_template.acadl_object.port_width:
            raise IssueBufferSmallerThanPortWidth(
                self.acadl_object,
                self.instruction_memory_verilog_template.acadl_object)

        # TODO checks

        self.instruction_fetch_stage_template_dir_path = f"{self.verilog_template_dir_path}/instruction_fetch_stage"
        self.instruction_fetch_stage_verilog_template_path = f"{self.instruction_fetch_stage_template_dir_path}/{self.instruction_fetch_stage_verilog_file_name}"
        self.pop_count_verilog_template_path = f"{self.instruction_fetch_stage_template_dir_path}/{self.pop_count_verilog_file_name}"
        self.instruction_memory_fetch_stage_wrapper_template_path = f"{self.instruction_fetch_stage_template_dir_path}/{self.instruction_memory_fetch_stage_wrapper_verilog_file_name}"
        self.tb_template_path = f"{self.instruction_fetch_stage_template_dir_path}/{self.tb_file_name}"

    def generate_verilog(self, target_dir_path: str) -> None:
        # generate instruction fetch stage verilog
        read_write_template(
            self.instruction_fetch_stage_verilog_template_path,
            target_dir_path +
            f"/{self.name}_{self.instruction_fetch_stage_verilog_file_name}",
            name=self.name,
            data_width=self.instruction_memory_verilog_template.acadl_object.
            data_width,
            max_data_word_distance=self.instruction_memory_verilog_template.
            max_data_word_distance,
            port_width=self.instruction_memory_verilog_template.acadl_object.
            port_width,
            address_width=self.instruction_memory_verilog_template.
            address_width,
            issue_buffer_size=self.acadl_object.issue_buffer_size,
            initial_address=0)

        # generate pop count verilog
        read_write_template(self.pop_count_verilog_template_path,
                            target_dir_path +
                            f"/{self.name}_{self.pop_count_verilog_file_name}",
                            name=self.name)

    def generate_test_bench(self,
                            target_dir_path: str,
                            ignore_target_dir_contents: bool = False) -> None:
        super().generate_test_bench(target_dir_path,
                                    ignore_target_dir_contents)

        # generate verilog for instruction fetch stage itself
        self.generate_verilog(target_dir_path)

        # generate instructions
        target_id_config = TargetIdConfig(start_bit=0, max_id=10)
        opcode_config = OpcodeConfig(start_bit=target_id_config.end_bit + 1,
                                     max_id=3)
        read_registers_config = DataFieldConfig(
            start_bit=opcode_config.end_bit + 1,
            data_field_type=DataFieldType.READ_REGISTER,
            num_fields=2,
            field_length=3)
        write_registers_config = DataFieldConfig(
            start_bit=read_registers_config.end_bit + 1,
            data_field_type=DataFieldType.WRITE_REGISTER,
            num_fields=1,
            field_length=3)
        read_addresses_config = DataFieldConfig(
            start_bit=write_registers_config.end_bit + 1,
            data_field_type=DataFieldType.READ_ADDRESS,
            num_fields=0,
            field_length=0)
        write_addresses_config = DataFieldConfig(
            start_bit=read_addresses_config.end_bit,
            data_field_type=DataFieldType.WRITE_ADDRESS,
            num_fields=0,
            field_length=0)
        immediates_config = DataFieldConfig(
            start_bit=write_addresses_config.end_bit + 1,
            data_field_type=DataFieldType.IMMEDIATE,
            num_fields=0,
            field_length=0)

        i_form = InstructionFormat(
            name="i_form",
            length=16,
            target_id_config=target_id_config,
            opcode_config=opcode_config,
            read_registers_config=read_registers_config,
            write_registers_config=write_registers_config,
            read_addresses_config=read_addresses_config,
            write_addresses_config=write_addresses_config,
            immediates_config=immediates_config)

        num_instructions = 10

        add_0 = ACADLInstruction(id=0,
                                 size=16,
                                 operation="add",
                                 read_registers=['r0', 'r1'],
                                 write_registers=['r1'],
                                 read_addresses=[],
                                 write_addresses=[],
                                 immediates=[])

        acadl_instructions = [add_0] * num_instructions
        instructions = []

        target_id = 1

        for acadl_instruction in acadl_instructions:
            i = Instruction(acadl_instruction=acadl_instruction,
                            target_id=target_id,
                            instruction_format=i_form)
            instructions.append(i)
            target_id += 1

        memory_file_path = target_dir_path + '/instructions.mem'

        create_memory_file_from_instructions(memory_file_path, instructions,
                                             i_form.length)

        # generate verilog for instruction memory
        imem0v = InstructionMemoryVerilogTemplate(
            self.instruction_memory_verilog_template.acadl_object,
            memory_file_path)
        imem0v.generate_verilog(target_dir_path)

        # generate verilog for mem-ifs wrapper
        imfsw_name = "imfsw0"

        read_write_template(
            self.instruction_memory_fetch_stage_wrapper_template_path,
            target_dir_path +
            f"/{imfsw_name}_{self.instruction_memory_fetch_stage_wrapper_verilog_file_name}",
            name=imfsw_name,
            instruction_fetch_stage_name=self.name,
            instruction_memory_name=self.instruction_memory_verilog_template.
            acadl_object.name,
            data_width=self.instruction_memory_verilog_template.acadl_object.
            data_width,
            max_data_word_distance=self.instruction_memory_verilog_template.
            max_data_word_distance,
            port_width=self.instruction_memory_verilog_template.acadl_object.
            port_width,
            address_width=self.instruction_memory_verilog_template.
            address_width)

        # generate systemc test bench
        read_write_template(
            self.tb_template_path,
            target_dir_path + f"/{self.name}_{self.tb_file_name}",
            instruction_memory_fetch_stage_wrapper_name=imfsw_name)

        # generate CMakeLists.txt
        read_write_template(
            self.instruction_fetch_stage_template_dir_path + "/CMakeLists.txt",
            target_dir_path + f"/CMakeLists.txt",
            instruction_fetch_stage_name=self.name,
            instruction_memory_name=self.instruction_memory_verilog_template.
            acadl_object.name,
            instruction_memory_fetch_stage_wrapper_name=imfsw_name)
