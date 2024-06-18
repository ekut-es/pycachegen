from math import ceil, log2
from veriloggen import (
    Module,
    If,
    Posedge,
    Negedge,
    Not
)


class DynamicPriorityEncoder:
    def __init__(self, width_unencoded: int, prefix: str):
        """Dynamic Priority Encoder Generator - A priority encoder with
        programmable ("at runtime") highest priority bit.

        Args:
            width_unencoded (int): Width of the input signal
            prefix (str): Prefix to be used for this module's name
        """
        self.WIDTH_UNENCODED = width_unencoded
        self.PREFIX = prefix

        self.WIDTH_ENCODED = max(1, ceil(log2(width_unencoded)))
        self.ORDER = range(self.WIDTH_UNENCODED)
        self.WIDTH_UNENCODED_CEILED = 2 ** self.WIDTH_ENCODED

    def generate_module(self) -> Module:
        m = Module(f"{self.PREFIX}priority_encoder")

        clk_i = m.Input("clk_i")
        reset_n_i = m.Input("reset_n_i")
        priority_i = m.Input("priority_i", self.WIDTH_UNENCODED)
        unencoded_i = m.Input("unencoded_i", self.WIDTH_UNENCODED)
        encoded_o = m.OutputReg("encoded_o", self.WIDTH_ENCODED)

        # pad the unencoded signal to a power of 2, then priority encoded that
        # otherwise we'd need to do modulo
        unencoded = m.Wire("unencoded", self.WIDTH_UNENCODED_CEILED)
        m.Assign(unencoded[:self.WIDTH_UNENCODED](unencoded_i))
        m.Assign(unencoded[self.WIDTH_UNENCODED](0))

        priority = m.Reg("priority", self.WIDTH_UNENCODED)

        # Set/Reset which bit has the highest priority
        m.Always(Posedge(clk_i), Negedge(reset_n_i))(
            If(Not(reset_n_i))(
                priority(0)
            ).Else(
                priority(priority_i)
            )
        )

        # Do the actual encoding
        m.Always(unencoded_i)(
            encoded_o(0, blk=True), # set to 0 in case that unencoded_i = 0
            [
                If(unencoded_i[priority + 1 + i])(encoded_o(i, blk=True))
                for i in range(self.WIDTH_UNENCODED)
            ]
        )

        return m
