from math import log2
from veriloggen import Module, If


class OneHotToBinGenerator:
    def __init__(self, num_inputs: int) -> None:
        self.num_inputs = num_inputs
        self.num_outputs = int(log2(num_inputs))

    def generate_module(self) -> Module:
        m = Module("one_hot_to_bin")
        input = m.Input("input", self.num_inputs)
        output = m.Output("output", self.num_outputs)

        m.Always(input)(
            [If(output[i] == 1)(output(i, blk=True)) for i in range(self.num_inputs)]
        )
