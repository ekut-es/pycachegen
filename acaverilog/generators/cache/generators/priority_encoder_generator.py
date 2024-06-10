from math import ceil, log2
from veriloggen import (
    Module,
    If
)


class PriorityEncoderGenerator:
    def __init__(self, width_unencoded, prioritize_msb = True):
        self.WIDTH_UNENCODED = width_unencoded
        self.PRIORITIZE_MSB = prioritize_msb
        self.WIDTH_ENCODED = max(1, ceil(log2(width_unencoded)))
        self.ORDER = range(self.WIDTH_UNENCODED)
        if self.PRIORITIZE_MSB:
            self.ORDER = reversed(self.ORDER)

    def generate_module(self) -> Module:
        m = Module("priority_encoder")

        unencoded_i = m.Input("unencoded_i", self.WIDTH_UNENCODED)
        encoded_o = m.OutputReg("encoded_o", self.WIDTH_ENCODED)

        m.Always(unencoded_i)(
            encoded_o(0, blk=True), # set to 0 in case that unencoded_i = 0
            [
                If(unencoded_i[i])(encoded_o(i, blk=True))
                for i in self.ORDER
            ]
        )

        return m
