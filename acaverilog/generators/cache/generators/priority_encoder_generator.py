from math import ceil, log2
from veriloggen import (
    Module,
    Submodule,
    Posedge,
    Negedge,
    If,
    For,
    AndList,
    OrList,
    Not,
    Or,
)


class PriorityEncoderGenerator:
    def __init__(self, width_unencoded):
        self.WIDTH_UNENCODED = width_unencoded
        self.WIDTH_ENCODED = ceil(log2(width_unencoded))

    def generate_module(self) -> Module:
        m = Module("priority_encoder")

        clk_i = m.Input("clk_i")
        reset_n_i = m.Input("reset_n_i")
        enable_i = m.Input("enable_i")
        unencoded_i = m.Input("unencoded_i", self.WIDTH_UNENCODED)
        encoded_o = m.Output("encoded_o", self.WIDTH_ENCODED)

        encoded = m.Reg("encoded", self.WIDTH_ENCODED)
        m.Assign(encoded_o(encoded))

        m.Always(Posedge(clk_i), Negedge(reset_n_i))(
            If(Not(reset_n_i))(encoded(0)).Elif(enable_i)(
                [
                    If(unencoded_i[i])(encoded(i, blk=True))
                    for i in range(self.WIDTH_UNENCODED)
                ]
            )
        )
