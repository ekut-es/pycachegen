from math import log2
from veriloggen import Module, If, Or


class OneHotToBinGenerator:
    def __init__(self, num_inputs: int) -> None:
        self.num_inputs = num_inputs
        self.num_outputs = int(log2(num_inputs))

    def generate_module(self) -> Module:
        m = Module("one_hot_to_bin")
        one_hot_i = m.Input("one_hot_i", self.num_inputs)
        bin_o = m.Output("bin_o", self.num_outputs)

        bin_o_reg = m.Reg("bin_o_reg", self.num_outputs)

        tmp_bin = m.Reg("tmp_bin", self.num_outputs)

        m.Assign(bin_o(bin_o_reg))

        m.Always(one_hot_i)(
            tmp_bin(0, blk=True),
            [If(one_hot_i[i] == 1)(tmp_bin(Or(tmp_bin, i), blk=True)) for i in range(self.num_inputs)],
            bin_o_reg(tmp_bin, blk=True)
        )

        return m
