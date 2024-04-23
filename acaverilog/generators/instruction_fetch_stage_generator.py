from math import ceil, log2
from typing import Dict
from veriloggen import Module, Submodule, Posedge, Negedge, If, For, AndList

from acadl import InstructionFetchStage

from .execute_stage_generator import ExecuteStageGenerator
from .lookup_table_generator import LookupTableGenerator
from ..instruction.instruction_format import InstructionFormat


class InstructionFetchStageGenerator(ExecuteStageGenerator):

    def __init__(self, instruction_fetch_stage: InstructionFetchStage,
                 instruction_format: InstructionFormat,
                 forward_port_map: Dict[int, int]) -> None:
        super().__init__(instruction_fetch_stage, instruction_format,
                         forward_port_map)

        self.issue_buffer_size = instruction_fetch_stage.issue_buffer_size

    def generate_module(self) -> Module:
        m = Module(self.base_file_name)

        LATENCY = m.Parameter('LATENCY', self.acadl_object.latency.int_latency)
        INSTRUCTION_LENGTH = m.Parameter('INSTRUCTION_LENGTH',
                                         self.instruction_length)
        TARGET_ID_START_BIT = m.Parameter('TARGET_ID_START_BIT',
                                          self.target_id_start_bit)
        TARGET_ID_END_BIT = m.Parameter('TARGET_ID_END_BIT',
                                        self.target_id_end_bit)
        TARGET_ID_LENGTH = m.Parameter('TARGET_ID_LENGTH',
                                       self.target_id_length)
        NUM_FORWARD_PORTS = m.Parameter('NUM_FORWARD_PORTS',
                                        self.num_forward_ports)
        NUM_FORWARD_PORTS_LENGTH = m.Parameter(
            'NUM_FORWARD_PORTS_LENGTH', ceil(log2(self.num_forward_ports)))
        ISSUE_BUFFER_SIZE = m.Parameter('ISSUE_BUFFER_SIZE',
                                        self.issue_buffer_size)

        clk_i = m.Input('clk_i')
        reset_n_i = m.Input('reset_n_i')

        instruction_i = m.Input('instruction_i', INSTRUCTION_LENGTH)
        instruction_valid_i = m.Input('instruction_valid_i')
        next_stage_ready_i = []
        for i in range(self.num_forward_ports):
            next_stage_ready_i.append(m.Input(f'next_stage_ready_{i}_i'))

        instruction_o = []
        for i in range(self.num_forward_ports):
            instruction_o.append(
                m.Output(f'instruction_{i}_o', INSTRUCTION_LENGTH))
        instruction_valid_o = []
        for i in range(self.num_forward_ports):
            instruction_valid_o.append(m.Output(f'instruction_valid_{i}_o'))
        ready_o = m.Output('ready_o')

        LATENCY_COUNTER_LENGTH = m.Localparam(
            'LATENCY_COUNTER_LENGTH',
            max(1, ceil(log2(self.acadl_object.latency.int_latency + 1))))
        latency_counter = m.Reg('latency_counter', LATENCY_COUNTER_LENGTH)

        ready = m.Reg('ready')
        instruction_buffer = m.Reg('instruction_buffer', INSTRUCTION_LENGTH)
        issue_buffer = m.Reg('issue_buffer', INSTRUCTION_LENGTH,
                             ISSUE_BUFFER_SIZE)
        issue_buffer_write_pointer = m.Reg('issue_buffer_write_pointer', 0)
        issue_buffer_full = m.Wire('issue_buffer_full')
        target_id = m.Wire('target_id', TARGET_ID_LENGTH, ISSUE_BUFFER_SIZE)
        forward_port_select = m.Wire('forward_port_select',
                                     NUM_FORWARD_PORTS_LENGTH,
                                     ISSUE_BUFFER_SIZE)
        forwarding_buffer = m.Reg('forwarding_buffer', INSTRUCTION_LENGTH,
                                  NUM_FORWARD_PORTS)
        forwarding_buffer_valid = m.Reg('forwarding_buffer_valid',
                                        NUM_FORWARD_PORTS)

        m.Assign(
            issue_buffer_full(issue_buffer_write_pointer == ISSUE_BUFFER_SIZE))
        instruction = []
        for i in range(self.issue_buffer_size):
            instruction.append(issue_buffer[i])
            m.Assign(target_id[0](0))

        fwd_lut = []
        for i in range(self.issue_buffer_size):
            lookup_table = LookupTableGenerator(
                self.name, self.target_id_length, self.forward_port_map,
                ceil(log2(self.num_forward_ports + 1))).generate_module()
            fwd_lut.append(
                Submodule(m,
                          lookup_table,
                          name=f'fwd_lut_{i}',
                          arg_ports=(('target_id_i', target_id[i]),
                                     ('forward_port_o',
                                      forward_port_select[i]))))

        m.Assign(ready_o(ready))
        for i in range(self.num_forward_ports):
            m.Assign(instruction_o[i](forwarding_buffer[i]))
            m.Assign(instruction_valid_o[i](forwarding_buffer_valid[i]))

        j = m.Integer('i')
        k = m.Integer('j')

        m.Always(Posedge(clk_i), Negedge(reset_n_i))(
            If(reset_n_i == 0)(latency_counter(LATENCY), ready(1),
                               instruction_buffer(0),
                               For(j(0), j < ISSUE_BUFFER_SIZE,
                                   j.inc())(issue_buffer[j](0)),
                               issue_buffer_write_pointer(0, blk=True),
                               For(j(0), j < NUM_FORWARD_PORTS,
                                   j.inc())(forwarding_buffer[j](0),
                                            forwarding_buffer_valid[j](0))).
            Else(

                # prepare instruction for buffering if issue buffer is not full and instruction is valid
                If(
                    AndList(ready == 1, instruction_i != 0,
                            instruction_valid_i == 1, issue_buffer_full == 0))
                (instruction_buffer(instruction_i), ready(0)),

                # forward instructions each cycle for all ready ports
                For(j(ISSUE_BUFFER_SIZE), j >= 0, j.dec())(
                    # match instruction to forward port and buffer it if port is ready
                    If(
                        AndList(
                            issue_buffer[j] != 0,
                            next_stage_ready_i[forward_port_select[j]] == 1,
                            forwarding_buffer[forward_port_select[j]] == 0))
                    (
                        forwarding_buffer[forward_port_select[j]](
                            issue_buffer[j]),
                        forwarding_buffer_valid[forward_port_select[j]](1),
                        issue_buffer_write_pointer(issue_buffer_write_pointer -
                                                   1,
                                                   blk=True),
                        # move up instructions in issue buffer
                        For(k(j), k < ISSUE_BUFFER_SIZE - 1, k.inc())
                        (issue_buffer[k](issue_buffer[k + 1])),
                    )),

                # decrement latency counter if instruction is being prepared for buffering
                If(AndList(latency_counter > 0,
                           ready == 0))(latency_counter(latency_counter - 1)),

                # add instruction to issue buffer if latency counter is 0
                If(AndList(latency_counter == 0, ready == 0))
                (issue_buffer[issue_buffer_write_pointer](instruction_buffer),
                 issue_buffer_write_pointer(issue_buffer_write_pointer + 1,
                                            blk=True), instruction_buffer(0),
                 ready(1), latency_counter(LATENCY)),

                # stop forwarding when port that instruction was forwarded to is no longer ready
                For(j(0), j < NUM_FORWARD_PORTS, j.inc())(If(
                    AndList(forwarding_buffer_valid[j] == 1,
                            next_stage_ready_i[j] == 0))(
                                forwarding_buffer[j](0),
                                forwarding_buffer_valid[j](0)))))

        return m
