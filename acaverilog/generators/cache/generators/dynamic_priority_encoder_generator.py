from math import ceil, log2
from veriloggen import Module, Submodule
from acaverilog.generators.cache.generators.priority_encoder_generator import (
    PriorityEncoderGenerator,
)


class DynamicPriorityEncoderGenerator:
    def __init__(self, width_unencoded: int, prefix: str, prioritize_msb: bool):
        """Generator for a priority encoder where the highest priority bit can be set
        "at runtime"/dynamically.

        Args:
            width_unencoded (int): Width of the input signal
            prefix (str): Prefix to be used for this module's name
            prioritize_msb (bool): Whether more significant bits should have higher or lower priority.
        """
        self.WIDTH_UNENCODED = width_unencoded
        self.PREFIX = prefix
        self.PRIORITIZE_MSB = prioritize_msb

        self.WIDTH_ENCODED = max(1, ceil(log2(width_unencoded)))
        self.WIDTH_UNENCODED_CEILED = 2**self.WIDTH_ENCODED

    def generate_module(self) -> Module:
        m = Module(f"{self.PREFIX}dynamic_priority_encoder")

        priority_i = m.Input("priority_i", self.WIDTH_ENCODED)
        unencoded_i = m.Input("unencoded_i", self.WIDTH_UNENCODED)
        encoded_o = m.OutputReg("encoded_o", self.WIDTH_ENCODED)

        # Add zero padding to the input signal to give it a length of a power of two
        zext_input = m.Wire("zext_input", self.WIDTH_UNENCODED_CEILED)
        m.Assign(zext_input[: self.WIDTH_UNENCODED](unencoded_i))
        if self.WIDTH_UNENCODED != self.WIDTH_UNENCODED_CEILED:
            m.Assign(zext_input[self.WIDTH_UNENCODED :](0))

        # Shift the signal circularly so that the prioritized bit is at the correct position
        reordered_input = m.Wire("reordered_input", self.WIDTH_UNENCODED_CEILED)
        # Output signal for the normal priority encoder
        reordered_encoded = m.Wire("reordered_encoded", self.WIDTH_ENCODED)
        if self.PRIORITIZE_MSB:
            m.Assign(
                reordered_input(
                    (zext_input << (self.WIDTH_UNENCODED_CEILED - 1 - priority_i))
                    | (zext_input >> (1 + priority_i))
                )
            )
            # Subtract shift amount to get original index. Overflow works as it should thanks to zext.
            m.Assign(
                encoded_o(
                    reordered_encoded - self.WIDTH_UNENCODED_CEILED - 1 - priority_i
                )
            )
        else:
            m.Assign(
                reordered_input(
                    (zext_input >> priority_i)
                    | (zext_input << (self.WIDTH_UNENCODED_CEILED - priority_i))
                )
            )
            # Add shift amount to get original index. Overflow works as it should thanks to zext.
            m.Assign(encoded_o(reordered_encoded + priority_i))

        Submodule(
            m,
            PriorityEncoderGenerator(
                self.WIDTH_UNENCODED, self.PREFIX, self.PRIORITIZE_MSB
            ).generate_module(),
            f"{self.PREFIX}priority_encoder",
            arg_ports=(
                ("unencoded_i", reordered_input),
                ("encoded_o", reordered_encoded),
            ),
        )

        return m
