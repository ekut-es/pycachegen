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
)

from acaverilog.generators.one_hot_to_bin_generator import OneHotToBinGenerator


class ReplacementPolicyGenerator:

    def __init__(self, num_ways: int, num_sets: int, policy: str) -> None:
        """Replacement policy generator.

        Args:
            num_ways (int): Number of ways. Must be a power of 2.
            num_sets (int): Number of sets. Must be a power of 2 and (for now) at least 2.
            policy (str): Can be either "fifo" or "plru_tree"
        """
        # This module will only be generated if num_ways > 1
        self.NUM_WAYS = num_ways
        self.NUM_SETS = num_sets
        self.POLICY = policy
        # derived
        self.NUM_WAYS_W = int(log2(self.NUM_WAYS))
        self.NUM_SETS_W = int(log2(self.NUM_SETS))

    def generate_module(self) -> Module:
        m = Module("replacement_policy")
        clk_i = m.Input("clk_i")
        access_valid_i = m.Input("access_valid_i")
        index_i = m.Input("index_i", self.NUM_SETS_W)
        way_i = m.Input("way_i", self.NUM_WAYS_W)

        next_replacement_o = m.Output(
            f"next_replacement_o", self.NUM_WAYS_W, dims=self.NUM_SETS
        )

        next_replacement_o_reg = m.Reg(
            "next_replacement_o_reg", self.NUM_WAYS_W, dims=self.NUM_SETS
        )

        m.Assign(next_replacement_o(next_replacement_o_reg))

        if self.POLICY == "fifo":
            m.Always(Posedge(clk_i))(
                If(AndList(access_valid_i, way_i == next_replacement_o_reg[index_i]))(
                    next_replacement_o_reg[index_i](next_replacement_o_reg[index_i] + 1, blk=True)
                )
            )
        else:
            plru_bits = m.Reg("plru_bits", self.NUM_WAYS - 1, self.NUM_SETS)
            tmp_repl = m.Reg("tmp_repl", self.NUM_WAYS_W + 1)

            m.Always(Posedge(clk_i))(
                If(access_valid_i)(
                    [
                        plru_bits[index_i][
                            ((way_i >> i)) + (2 ** (self.NUM_WAYS_W - i) - 1)
                        ](way_i[i - 1], blk=True)
                        for i in range(1, self.NUM_WAYS_W + 1)
                    ],
                    tmp_repl(0, blk=True),
                    [
                        tmp_repl(2 * tmp_repl + 2 - plru_bits[index_i][tmp_repl[:self.NUM_WAYS_W]], blk=True)
                        for _ in range(self.NUM_WAYS_W)
                    ],
                    tmp_repl(tmp_repl - self.NUM_WAYS + 1, blk=True),
                    next_replacement_o_reg[index_i](tmp_repl[:self.NUM_WAYS_W], blk=True),
                )
            )

        return m
