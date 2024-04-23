from typing import Dict
from veriloggen import Module, Case, When


class LookupTableGenerator():

    def __init__(self, name: str, target_id_length: int,
                 forward_port_map: Dict[int, int],
                 num_forward_ports_length: int) -> None:
        self.name = name
        self.target_id_length = target_id_length
        self.forward_port_map = forward_port_map
        self.num_forward_ports_length = num_forward_ports_length

    def generate_module(self) -> Module:

        m = Module(self.name + "_LookupTable")

        target_id_i = m.Input("target_id_i", self.target_id_length)
        forward_port_o = m.Output("forward_port_o",
                                  self.num_forward_ports_length)

        forward_port = m.Reg("forward_port", self.num_forward_ports_length)

        m.Assign(forward_port_o(forward_port))

        m.Always(target_id_i)(Case(target_id_i)(*[
            When(key)(forward_port(value, blk=True))
            for key, value in self.forward_port_map.items()
        ], When(None)(forward_port(0, blk=True))))

        return m
