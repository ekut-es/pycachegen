from math import ceil, log2
from typing import Dict
from veriloggen import Module, Submodule, Posedge, Negedge, If, For, AndList, Cond

from acadl import MemoryAccessUnit

from .functional_unit_generator import FunctionalUnitGenerator
from ..instruction.instruction_format import InstructionFormat


class MemoryAccessUnitGenerator(FunctionalUnitGenerator):

    def __init__(self,
                 memory_access_unit: MemoryAccessUnit,
                 instruction_format: InstructionFormat,
                 data_width=32) -> None:
        super().__init__(memory_access_unit, instruction_format, data_width)

        self.opcode_start_bit = instruction_format.opcode_config.start_bit
        self.opcode_end_bit = instruction_format.opcode_config.end_bit
        self.opcode_length = instruction_format.opcode_config.length

    def generate_module(self) -> Module:

        m = Module(self.base_file_name)

        LATENCY = m.Parameter('LATENCY',
                              self.acadl_object.latency.int_latency - 1)
        INSTRUCTION_LENGTH = m.Parameter('INSTRUCTION_LENGTH',
                                         self.instruction_length)
        INSTRUCTION_ID_LENGTH = m.Parameter('INSTRUCTION_ID_LENGTH',
                                            self.instruction_id_length)
        OPCODE_START_BIT = m.Parameter('OPCODE_START_BIT',
                                       self.opcode_start_bit)
        OPCODE_LENGTH = m.Parameter('OPCODE_LENGTH', self.opcode_length)
        READ_REGISTERS_START_BIT = m.Parameter('READ_REGISTERS_START_BIT',
                                               self.read_registers_start_bit)
        WRITE_REGISTER_START_BIT = m.Parameter('WRITE_REGISTER_START_BIT',
                                               self.write_register_start_bit)
        REGISTER_LENGTH = m.Parameter('REGISTER_LENGTH', self.register_length)
        IMMEDIATE_START_BIT = m.Parameter('IMMEDIATE_START_BIT',
                                          self.immediate_start_bit)
        IMMEDIATE_LENGTH = m.Parameter('IMMEDIATE_LENGTH',
                                       self.immediate_length)
        READ_ADDRESS_START_BIT = m.Parameter('READ_ADDRESS_START_BIT',
                                             self.read_address_start_bit)
        READ_ADDRESS_LENGTH = m.Parameter('READ_ADDRESS_LENGTH',
                                          self.read_address_length)
        WRITE_ADDRESS_START_BIT = m.Parameter('WRITE_ADDRESS_START_BIT',
                                              self.write_address_start_bit)
        WRITE_ADDRESS_LENGTH = m.Parameter('WRITE_ADDRESS_LENGTH',
                                           self.write_address_length)

        clk_i = m.Input('clk_i')
        reset_n_i = m.Input('reset_n_i')

        instruction_id_i = m.Input('instruction_id_i', INSTRUCTION_ID_LENGTH)
        target_id_i = m.Input('target_id_i', TARGET_ID_LENGTH)
        instruction_i = m.Input('instruction_i', INSTRUCTION_LENGTH)
        instruction_valid_i = m.Input('instruction_valid_i')
        register_ready_i = m.Input('register_ready_i')
        memory_ready_i = m.Input('memory_ready_i')
        scoreboard_green_light_i = m.Input('scoreboard_green_light_i')
        read_register_i = m.Input('read_i', INSTRUCTION_LENGTH)
        write_register_done_i = m.Input('write_done_i')
        read_memory_i = m.Input('read_memory_i', INSTRUCTION_LENGTH)
        write_memory_done_i = m.Input('write_memory_done_i')

        scoreboard_request_o = m.Output('scoreboard_request_o',
                                        INSTRUCTION_ID_LENGTH)
        register_o = m.Output('register_o', REGISTER_LENGTH)
        register_valid_o = m.Output('register_valid_o')
        register_read_write_select_o = m.Output('read_write_select_o')
        write_register_o = m.Output('write_o', INSTRUCTION_LENGTH)
        memory_read_address_o = m.Output('memory_read_address_o',
                                         READ_ADDRESS_LENGTH)
        memory_read_valid_o = m.Output('memory_read_valid_o')
        memory_write_address_o = m.Output('memory_write_address_o',
                                          WRITE_ADDRESS_LENGTH)
        memory_write_data_o = m.Output('memory_write_data_o',
                                       INSTRUCTION_LENGTH)
        memory_write_valid_o = m.Output('memory_write_valid_o')
        ready_o = m.Output('ready_o')

        LATENCY_COUNTER_LENGTH = m.Localparam(
            'LATENCY_COUNTER_LENGTH',
            ceil(log2(self.acadl_object.latency.int_latency)) + 1)
        latency_counter = m.Reg('latency_counter', LATENCY_COUNTER_LENGTH)

        ready = m.Reg('ready')
        working_status = m.Reg('working_status', 4, value=0)
        instruction_id_buffer = m.Reg('instruction_id_buffer',
                                      INSTRUCTION_ID_LENGTH)
        instruction_buffer = m.Reg('instruction_buffer', INSTRUCTION_LENGTH)

        instruction_type = m.Wire('instruction_type', OPCODE_LENGTH)
        read_register1 = m.Wire('read_register1', REGISTER_LENGTH)
        read_register2 = m.Wire('read_register2', REGISTER_LENGTH)
        write_register = m.Wire('write_register', REGISTER_LENGTH)
        immediate = m.Wire('immediate', IMMEDIATE_LENGTH)
        read_address = m.Wire('read_address', READ_ADDRESS_LENGTH)
        write_address = m.Wire('write_address', WRITE_ADDRESS_LENGTH)

        scoreboard_request = m.Wire('scoreboard_request',
                                    INSTRUCTION_ID_LENGTH)

        m.Assign(
            instruction_type(instruction_i[OPCODE_START_BIT:OPCODE_LENGTH]))
        m.Assign(
            read_register1(
                instruction_buffer[READ_REGISTERS_START_BIT:REGISTER_LENGTH]))
        m.Assign(
            read_register2(
                instruction_buffer[READ_REGISTERS_START_BIT +
                                   REGISTER_LENGTH:REGISTER_LENGTH * 2]))
        m.Assign(
            write_register(
                instruction_buffer[WRITE_REGISTER_START_BIT:REGISTER_LENGTH]))
        m.Assign(
            immediate(
                instruction_buffer[IMMEDIATE_START_BIT:IMMEDIATE_LENGTH]))
        m.Assign(
            read_address(
                instruction_buffer[READ_ADDRESS_START_BIT:READ_ADDRESS_LENGTH])
        )
        m.Assign(
            write_address(instruction_buffer[
                WRITE_ADDRESS_START_BIT:WRITE_ADDRESS_LENGTH]))

        m.Assign(scoreboard_request_o(scoreboard_request))
        m.Assign(ready_o(ready))

        m.Always(Posedge(clk_i), Negedge(reset_n_i))(
            If(reset_n_i == 0)(
                latency_counter(LATENCY),
                ready(1),
            ).Else(
                # buffer instruction if ready and valid; request scoreboard green light
                If(
                    AndList(instruction_i != 0, instruction_valid_i == 1,
                            ready == 1))
                (instruction_id_buffer(instruction_id_i),
                 instruction_buffer(instruction_i),
                 scoreboard_request(instruction_id_i), ready(0)),

                # green light received; start processing instruction
                If(AndList(ready == 0, working_status == 0))
                (If(scoreboard_green_light_i == 1)(working_status(1),
                                                   scoreboard_request(0),
                                                   latency_counter(LATENCY))),

                # decrement latency counter if instruction is being processed
                If(AndList(latency_counter > 0,
                           ready == 0))(latency_counter(latency_counter - 1)),
                If(AndList(latency_counter == 0, ready == 0))(
                    If(instruction_type == 0)(  # MOVI
                        If(AndList(working_status == 1,
                                   register_ready_i))(
                                       register_o(write_register),
                                       register_valid_o(1),
                                       read_write_select_o(1),
                                       write_o(immediate), ready(1),
                                       working_status(0))).Elif(
                                           instruction_type == 1)(  # R-Type
                                               # TODO
                                           )),

                # stop write signal when write is done
                If(AndList(write_done_i == 1,
                           ready == 1))(register_valid_o(0))))

        return m
