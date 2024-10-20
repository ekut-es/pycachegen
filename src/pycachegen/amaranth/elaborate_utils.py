from amaranth import *


def one_hot_encode(module: Module, input: Signal) -> Signal:
    """One hot encodes the input to the returned signal. If not exactly
    one bit in the input is set, the output will be 0.

    Args:
        module (Module): Module to which the assignment should be added.
        input (Signal): Signal to encode.

    Returns:
        Signal: Encoded signal.
    """
    m = module
    width = len(input)
    output = Signal(range(width))
    with m.Switch(input):
        for i in range(width):
            with m.Case(1 << i):
                m.d.comb += output.eq(i)
        with m.Default():
            # The default is already set by the initial value of the output Signal
            # but i'll make it more explicit here
            m.d.comb += output.eq(0)
    return output
