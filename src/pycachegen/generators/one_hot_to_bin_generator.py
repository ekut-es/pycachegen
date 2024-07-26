from math import log2
from veriloggen import Module, If, Or


class OneHotToBinGenerator:
    def __init__(self, num_inputs: int, prefix: str) -> None:
        """One Hot to Binary Generator

        Args:
            num_inputs (int): Width of the input signal.
            prefix (str): Prefix to be used for this module's name
        """
        self.NUM_INPUTS = num_inputs
        self.PREFIX = prefix

        self.NUM_OUTPUTS = int(log2(num_inputs))

    def generate_module(self) -> Module:
        m = Module(f"{self.PREFIX}one_hot_to_bin")
        one_hot_i = m.Input("one_hot_i", self.NUM_INPUTS)
        bin_o = m.Output("bin_o", self.NUM_OUTPUTS)

        bin_o_reg = m.Reg("bin_o_reg", self.NUM_OUTPUTS)

        tmp_bin = m.Reg("tmp_bin", self.NUM_OUTPUTS)

        m.Assign(bin_o(bin_o_reg))

        m.Always(one_hot_i)(
            tmp_bin(0, blk=True),
            [If(one_hot_i[i] == 1)(tmp_bin(Or(tmp_bin, i), blk=True)) for i in range(self.NUM_INPUTS)],
            bin_o_reg(tmp_bin, blk=True)
        )

        return m
