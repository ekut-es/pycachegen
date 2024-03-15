from typing import Dict

from acaverilog.pipeline_stage_verilog_template import PipelineStageVerilogTemplate
from .instruction_memory_verilog_template import InstructionMemoryVerilogTemplate
from .scoreboard_verilog_template import ScoreboardVerilogTemplate
from acadl import Memory, InstructionFetchStage, latency_t
from acadl import Instruction as ACADLInstruction
from .instruction.instruction import Instruction, create_memory_file_from_instructions
from .instruction.target_id_config import TargetIdConfig
from .instruction.opcode_config import OpcodeConfig
from .instruction.data_field_config import DataFieldConfig, DataFieldType
from .instruction.instruction_format import InstructionFormat
from .utils import read_write_template
from math import ceil, log2
from veriloggen import *


class IssueBufferSmallerThanPortWidth(Exception):

    def __init__(self, instruction_fetch_stage: InstructionFetchStage,
                 instruction_memory: Memory):
        self.instruction_fetch_stage = instruction_fetch_stage
        self.instruction_memory = instruction_memory

    def __str__(self):
        return f"InstructionFetchStage '{self.instruction_fetch_stage.name}'.issue_buffer_size = {self.instruction_fetch_stage.issue_buffer_size}! smaller than Memory '{self.instruction_memory.name}.'.port_width = {self.instruction_memory.port_width}!"


class NotAllForwardPortsUsedForTestBench(Exception):

    def __init__(self, forward_port_map, forward_ports):
        self.forward_port_map = forward_port_map
        self.forward_ports = forward_ports

    def __str__(self):
        return f"forward_port_map: {self.forward_port_map} does not use all {self.forward_ports} forward ports!"


class InstructionFetchStageVerilogTemplate(PipelineStageVerilogTemplate):

    def __init__(self, instruction_fetch_stage: InstructionFetchStage,
                 instruction_memory_verilog_template:
                 InstructionMemoryVerilogTemplate,
                 target_id_config: TargetIdConfig = None,
                 forward_port_map: Dict[int, int] = None) -> None:

        super().__init__(pipeline_stage=instruction_fetch_stage,
                         instruction_size=instruction_memory_verilog_template.
                         acadl_object.data_width,
                         target_id_config=target_id_config,
                         forward_port_map=forward_port_map)

        self.instruction_fetch_stage_verilog_file_name = "InstructionFetchStage.v"
        self.pop_count_verilog_file_name = "PopCount.v"
        self.scoreboard_verilog_file_name = "Scoreboard.v"
        self.tb_file_name = "InstructionFetchStage_tb.cc"
        self.instruction_memory_fetch_stage_wrapper_verilog_file_name = "InstructionMemoryFetchStageWrapper.v"

        self.instruction_memory_verilog_template = instruction_memory_verilog_template

        # issue_buffer_size has to be at least as large as the port_width
        """if self.acadl_object.issue_buffer_size < instruction_memory_verilog_template.acadl_object.port_width:
            raise IssueBufferSmallerThanPortWidth(
                self.acadl_object,
                self.instruction_memory_verilog_template.acadl_object)"""

        # TODO checks

        self.instruction_fetch_stage_template_dir_path = f"{self.verilog_template_dir_path}/instruction_fetch_stage"
        self.instruction_fetch_stage_verilog_template_path = f"{self.instruction_fetch_stage_template_dir_path}/{self.instruction_fetch_stage_verilog_file_name}"
        self.pop_count_verilog_template_path = f"{self.instruction_fetch_stage_template_dir_path}/{self.pop_count_verilog_file_name}"
        self.scoreboard_verilog_template_path = f"{self.instruction_fetch_stage_template_dir_path}/{self.scoreboard_verilog_file_name}"
        self.instruction_memory_fetch_stage_wrapper_template_path = f"{self.instruction_fetch_stage_template_dir_path}/{self.instruction_memory_fetch_stage_wrapper_verilog_file_name}"
        self.tb_template_path = f"{self.instruction_fetch_stage_template_dir_path}/{self.tb_file_name}"

    def generate_verilog(self, target_dir_path: str) -> None:
        # generate instruction fetch stage verilog
        
        m = Module(f"{self.name}_InstructionFetchStage")
        
        data_width = Parameter('DATA_WIDTH', self.instruction_memory_verilog_template.acadl_object.data_width)
        instruction_width = Parameter('INSTRUCTION_WIDTH', data_width)
        max_data_word_distance = Parameter('MAX_DATA_WORD_DISTANCE', self.instruction_memory_verilog_template.max_data_word_distance)
        address_width = Parameter('ADDRESS_WIDTH', self.instruction_memory_verilog_template.address_width)

        clk_i = m.Input('clk_i')
        reset_n_i = m.Input('reset_n_i')

        read_write_select_o = m.Output('read_write_select_o')
        address_o = m.Output('address_o', address_width)
        data_word_distace_o = m.Output('data_word_distace_o', ceil(log2(max_data_word_distance)))
        address_valid_o = m.Output('address_valid_o')
        write_data_o = m.Output('write_data_o', data_width)
        write_data_valid_o = m.Output('write_data_valid_o')
        write_done_i = m.Input('write_done_i')
        read_data_i = m.Input('read_data_i', data_width)
        read_data_valid_i = m.Input('read_data_valid_i')
        instruction_memory_ready_i = m.Input('instruction_memory_ready_i')

        next_stage_ready_i = m.Input('next_stage_ready_i')
        instruction_o = m.Output('instruction_o', instruction_width)
        instruction_valid_o = m.Output('instruction_valid_o')


        address_valid = m.Reg('address_valid')
        read_data = m.Reg('read_data', data_width)
        initialize_read = m.Reg('initialize_read')
        read_in_progress = m.Reg('read_in_progress')
        read_done = m.Reg('read_done')
        read_last_instruction = m.Reg('read_last_instruction')
        instruction_valid = m.Reg('instruction_valid')
        
        # instruction fetch stage only reads from instruction memory
        m.Assign(read_write_select_o(0))
        m.Assign(address_o(0)) # TODO PROGRAM_COUNTER !!!!!!!!!
        m.Assign(data_word_distace_o(1))
        m.Assign(address_valid_o(address_valid))
        m.Assign(write_data_o(0))
        m.Assign(write_data_valid_o(0))
        m.Assign(instruction_valid_o(instruction_valid))
        m.Assign(instruction_o(0))   # TODO

        m.Always(Posedge(clk_i), Negedge(reset_n_i))(
            If(reset_n_i == 0)(
                # TODO reset PC
                address_valid(0),
                initialize_read(1),
                read_in_progress(0),
                read_done(0),
                read_last_instruction(0),
                instruction_valid(0)
            ).Else(
                # initialize read from memory
                If(AndList(read_done == 1, initialize_read == 0, instruction_memory_ready_i == 1, read_last_instruction == 0))(
                    initialize_read(1),
                    read_done(0)
                ),

                # start read from memory
                If(AndList(initialize_read == 1, instruction_memory_ready_i == 1))( 
                    address_valid(1),
                    initialize_read(0),
                    read_in_progress(1),
                    read_done(0)
                ),

                # read in progress and memory has valid data
                If(AndList(read_in_progress == 1, initialize_read == 0, read_data_valid_i == 1))(
                    read_data(read_data_i),
                    If(read_data_i == 0)(
                        read_last_instruction(1)
                    ).Else(
                        read_last_instruction(0)
                    ),
                    If(AndList(read_last_instruction == 0, instruction_memory_ready_i == 1)(
                        initialize_read(1)
                    )).Else(
                        read_done(1)
                    ),

                    address_valid(0),
                    read_in_progress(0)
                    # TODO PC++
                ),

                If(next_stage_ready_i == 1)(
                    instruction_valid(1)
                ).Else(
                    instruction_valid(0)
                ),

                
            )
        )




        
        """read_write_template(
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
            target_id_start_bit=self.target_id_config.start_bit,
            target_id_length=self.target_id_config.length,
            issue_buffer_size=self.acadl_object.issue_buffer_size,
            initial_address=0,
            forward_ports=self.forward_ports,
            forward_port_map=self.forward_port_map)"""

        # generate pop count verilog
        read_write_template(self.pop_count_verilog_template_path,
                            target_dir_path +
                            f"/{self.name}_{self.pop_count_verilog_file_name}",
                            name=self.name)

        # generate forward lookup tables verilog
        for i in range(self.acadl_object.issue_buffer_size):
            read_write_template(
                self.forward_lookup_table_verilog_template_path,
                target_dir_path +
                f"/{self.name}_{i}_{self.forward_lookup_table_verilog_file_name}",
                name=f"{self.name}_{i}",
                target_id_length=self.target_id_config.length,
                forward_ports=self.forward_ports,
                forward_ports_size=ceil(log2(self.forward_ports)),
                forward_port_map=self.forward_port_map)

    def generate_test_bench(self,
                            target_dir_path: str,
                            ignore_target_dir_contents: bool = False) -> None:
        super().generate_test_bench(target_dir_path,
                                    ignore_target_dir_contents)

        # check if forward_port_map assigns at least one target id to a forward_port
        forward_port_map_values = set(self.forward_port_map.values())
        for i in range(self.forward_ports):
            if i not in forward_port_map_values:
                raise NotAllForwardPortsUsedForTestBench(
                    self.forward_port_map, self.forward_ports)

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

        num_instructions = 2 * self.forward_ports

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

        # generate verilog for scoreboard
        s0 = ScoreboardVerilogTemplate(
            max_instructions=8,
            functional_units=2,
            max_source_registers=2,
            max_destination_registers=1,
            max_instruction_issues=self.forward_ports,
            instruction_size=self.instruction_memory_verilog_template.
            acadl_object.data_width)
        s0.generate_verilog(target_dir_path)

        # generate verilog for mem-ifs-scoreboard wrapper
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
            address_width,
            forward_ports=self.forward_ports,
            scoreboard_name=s0.acadl_object.name)

        # generate systemc test bench
        read_write_template(
            self.tb_template_path,
            target_dir_path + f"/{self.name}_{self.tb_file_name}",
            instruction_memory_fetch_stage_wrapper_name=imfsw_name,
            forward_ports=self.forward_ports)

        # generate CMakeLists.txt
        read_write_template(
            self.instruction_fetch_stage_template_dir_path + "/CMakeLists.txt",
            target_dir_path + f"/CMakeLists.txt",
            instruction_fetch_stage_name=self.name,
            instruction_memory_name=self.instruction_memory_verilog_template.
            acadl_object.name,
            instruction_memory_fetch_stage_wrapper_name=imfsw_name,
            issue_buffer_size=self.acadl_object.issue_buffer_size,
            scoreboard_name=s0.acadl_object.name)
