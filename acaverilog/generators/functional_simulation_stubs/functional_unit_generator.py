from math import ceil, log2
from typing import Dict
from veriloggen import Module, Submodule, Posedge, Negedge, If, For, AndList, Cond

from acadl import FunctionalUnit

from .acadl_object_generator import ACADLObjectGenerator
from ..instruction.instruction_format import InstructionFormat
from ..exceptions import LatencyIsNotAnInteger


class FunctionalUnitGenerator(ACADLObjectGenerator):

    def __init__(self, functional_unit: FunctionalUnit,
                 instruction_format: InstructionFormat,
                 data_width: int) -> None:
        super().__init__(functional_unit)
        self.instruction_format = instruction_format
        self.data_width = data_width

        self.instruction_length = instruction_format.length
        self.instruction_id_start_bit = instruction_format.id_config.start_bit
        self.instruction_id_end_bit = instruction_format.id_config.end_bit
        self.instruction_id_length = instruction_format.id_config.length

        # check if latency is an integer
        if self.acadl_object.latency.int_latency == -1:
            raise LatencyIsNotAnInteger(self.acadl_object,
                                        self.acadl_object.latency)

    def generate_module(self) -> Module:

        m = Module(self.base_file_name)

        LATENCY = m.Parameter('LATENCY',
                              self.acadl_object.latency.int_latency - 1)
        INSTRUCTION_LENGTH = m.Parameter('INSTRUCTION_LENGTH',
                                         self.instruction_length)
        INSTRUCTION_ID_START_BIT = m.Parameter('INSTRUCTION_ID_START_BIT',
                                               self.instruction_id_start_bit)
        INSTRUCTION_ID_END_BIT = m.Parameter('INSTRUCTION_ID_END_BIT',
                                             self.instruction_id_end_bit)
        INSTRUCTION_ID_LENGTH = m.Parameter('INSTRUCTION_ID_LENGTH',
                                            self.instruction_id_length)
        REGISTER_LENGTH = m.Parameter('REGISTER_LENGTH', 1)  # Dummy value
        DATA_WIDTH = m.Parameter('DATA_WIDTH', self.data_width)

        clk_i = m.Input('clk_i')
        reset_n_i = m.Input('reset_n_i')

        instruction_i = m.Input('instruction_i', INSTRUCTION_LENGTH)
        instruction_valid_i = m.Input('instruction_valid_i')
        register_ready_i = m.Input('register_ready_i')
        scoreboard_green_light_i = m.Input('scoreboard_green_light_i')
        read_i = m.Input('read_i', DATA_WIDTH)
        write_done_i = m.Input('write_done_i')

        scoreboard_request_o = m.Output('scoreboard_request_o',
                                        INSTRUCTION_ID_LENGTH)
        scoreboard_request_valid_o = m.Output('scoreboard_request_valid_o')
        register_o = m.Output('register_o', REGISTER_LENGTH)
        register_valid_o = m.Output('register_valid_o')
        read_write_select_o = m.Output('read_write_select_o')
        write_o = m.Output('write_o', DATA_WIDTH)
        ready_o = m.Output('ready_o')

        LATENCY_COUNTER_LENGTH = m.Localparam(
            'LATENCY_COUNTER_LENGTH',
            ceil(log2(self.acadl_object.latency.int_latency + 1)))
        latency_counter = m.Reg('latency_counter', LATENCY_COUNTER_LENGTH)

        ready = m.Reg('ready')
        instruction_buffer = m.Reg('instruction_buffer', INSTRUCTION_LENGTH)

        instruction_type = m.Wire('instruction_type', OPCODE_LENGTH)
        read_register1 = m.Wire('read_register1', REGISTER_LENGTH)
        read_register2 = m.Wire('read_register2', REGISTER_LENGTH)
        write_register = m.Wire('write_register', REGISTER_LENGTH)
        immediate = m.Wire('immediate', IMMEDIATE_LENGTH)

        scoreboard_request = m.Reg('scoreboard_request', INSTRUCTION_ID_LENGTH)

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

        m.Assign(scoreboard_request_o(scoreboard_request))
        m.Assign(scoreboard_request_valid_o(scoreboard_request != 0))
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
