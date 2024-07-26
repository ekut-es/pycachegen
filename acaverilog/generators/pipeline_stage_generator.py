from math import ceil, log2
from typing import Dict
from veriloggen import Module, Submodule, Posedge, Negedge, If, For, AndList

from acadl import PipelineStage

from .acadl_object_generator import ACADLObjectGenerator
from .lookup_table_generator import LookupTableGenerator
from ..instruction.instruction_format import InstructionFormat
from ..exceptions import LatencyIsNotAnInteger, TargetIdEqualOrLessThan0


class PipelineStageGenerator(ACADLObjectGenerator):

    def __init__(
        self,
        pipeline_stage: PipelineStage,
        instruction_format: InstructionFormat,
        forward_port_map: Dict[int, int],
    ) -> None:
        super().__init__(pipeline_stage)

        self.instruction_format = instruction_format
        self.forward_port_map = forward_port_map

        self.instruction_length = instruction_format.length
        self.target_id_start_bit = instruction_format.target_id_config.start_bit
        self.target_id_end_bit = instruction_format.target_id_config.end_bit
        self.target_id_length = instruction_format.target_id_config.length

        self.num_forward_ports = max(self.forward_port_map.values()) + 1
        self.num_forward_ports_length = ceil(log2(self.num_forward_ports + 1))

        # check if latency is an integer
        if self.acadl_object.latency.int_latency == -1:
            raise LatencyIsNotAnInteger(self.acadl_object,
                                        self.acadl_object.latency)

        # check if forward_port_map target ids are all greater than 0
        if min(forward_port_map.keys()) <= 0:
            raise TargetIdEqualOrLessThan0(forward_port_map)

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
        NUM_FORWARD_PORTS_LENGTH = m.Parameter('NUM_FORWARD_PORTS_LENGTH',
                                               self.num_forward_ports_length)

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
        target_id = m.Wire('target_id', TARGET_ID_LENGTH)
        next_stage_ready = m.Wire('next_stage_ready', NUM_FORWARD_PORTS)
        forward_port_select = m.Wire('forward_port_select',
                                     NUM_FORWARD_PORTS_LENGTH)
        forward_port_buffer = m.Reg('forward_port_buffer',
                                    NUM_FORWARD_PORTS_LENGTH)
        forwarding_in_progress = m.Reg('forwarding_in_progress')
        instruction_o_internal = m.Reg('instruction_o_internal',
                                       INSTRUCTION_LENGTH, NUM_FORWARD_PORTS)
        instruction_valid_o_internal = m.Reg('instruction_valid_o_internal',
                                             NUM_FORWARD_PORTS)

        m.Assign(ready_o(ready))
        m.Assign(
            target_id(
                instruction_buffer[TARGET_ID_START_BIT:TARGET_ID_END_BIT + 1]))
        for i in range(self.num_forward_ports):
            m.Assign(next_stage_ready[i](next_stage_ready_i[i]))
            m.Assign(instruction_o[i](instruction_o_internal[i]))
            m.Assign(instruction_valid_o[i](instruction_valid_o_internal[i]))

        lookup_table = LookupTableGenerator(
            self.name, self.target_id_length, self.forward_port_map,
            self.num_forward_ports_length).generate_module()
        fwd_lut = Submodule(m,
                            lookup_table,
                            name='fwd_lut',
                            arg_ports=(('target_id_i', target_id),
                                       ('forward_port_o',
                                        forward_port_select)))

        j = m.Integer('i')

        m.Always(Posedge(clk_i), Negedge(reset_n_i))(
            If(reset_n_i == 0)(latency_counter(LATENCY), ready(1),
                               instruction_buffer(0), forward_port_buffer(0),
                               forwarding_in_progress(0),
                               For(j(0), j < NUM_FORWARD_PORTS, j.inc())(
                                   instruction_o_internal[j](0),
                                   instruction_valid_o_internal[j](0))).
            Else(

                # buffer instruction if ready and valid
                If(
                    AndList(instruction_i != 0, instruction_valid_i == 1,
                            ready == 1))
                (instruction_buffer(instruction_i), ready(0)),

                # decrement latency counter if instruction is buffered
                If(AndList(latency_counter > 0, ready == 0))
                (latency_counter(latency_counter - 1)),

                # forward instruction (and reset) if latency counter is 0 and next stage is ready
                If(
                    AndList(latency_counter == 0, ready == 0,
                            next_stage_ready[forward_port_select] == 1))
                (
                    instruction_o_internal[forward_port_select](
                        instruction_buffer),
                    instruction_valid_o_internal[forward_port_select](1),
                    forward_port_buffer(forward_port_select),
                    forwarding_in_progress(1),
                    # reset
                    instruction_buffer(0),
                    ready(1),
                    latency_counter(LATENCY)),

                # stop forwarding when stage that instruction was forwarded to is no longer ready
                If(
                    AndList(forwarding_in_progress == 1,
                            next_stage_ready[forward_port_buffer] == 0))
                (instruction_o_internal[forward_port_buffer](0),
                 instruction_valid_o_internal[forward_port_buffer](0),
                 forwarding_in_progress(0))))

        return m

    def generate_test_bench(self,
                            target_dir_path: str,
                            ignore_target_dir_contents: bool = False) -> None:
        super().generate_test_bench(
            target_dir_path,
            ignore_target_dir_contents,
            latency=self.acadl_object.latency.int_latency,
            num_forward_ports=self.num_forward_ports)
