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
    Repeat,
)


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
        reset_n_i = m.Input("reset_n_i")
        clk_i = m.Input("clk_i")
        access_i = m.Input("access_i")
        # some policies might only need to know of normal accesses, other might need to know if an access replaces a block
        replace_i = m.Input("replace_i")
        set_index_i = m.Input("set_index_i", max(1, self.NUM_SETS_W))
        block_index_i = m.Input("block_index_i", self.NUM_WAYS_W)

        next_replacement_o = m.Output(
            f"next_replacement_o", self.NUM_WAYS_W, dims=self.NUM_SETS
        )

        next_replacement_o_reg = m.Reg(
            "next_replacement_o_reg", self.NUM_WAYS_W, dims=self.NUM_SETS
        )

        m.Assign(next_replacement_o(next_replacement_o_reg))

        if self.POLICY == "fifo":
            m.Always(Posedge(clk_i), Negedge(reset_n_i))(
                If(reset_n_i == 0)(
                    [next_replacement_o_reg[i](0) for i in range(self.NUM_SETS)]
                ).Elif(replace_i)(
                    next_replacement_o_reg[set_index_i](
                        next_replacement_o_reg[set_index_i] + 1, blk=True
                    )
                )
            )
        else:
            plru_bits = m.Reg("plru_bits", self.NUM_WAYS - 1, self.NUM_SETS)
            tmp_repl = m.Reg("tmp_repl", self.NUM_WAYS_W + 1)

            m.Always(Posedge(clk_i), Negedge(reset_n_i))(
                If(reset_n_i == 0)(
                    [
                        (
                            plru_bits[i](0),
                            next_replacement_o_reg[i](2**self.NUM_WAYS_W - 1),
                        )
                        for i in range(self.NUM_SETS)
                    ]
                ).Elif(access_i)(
                    # Update the PLRU Bits
                    [
                        plru_bits[set_index_i][
                            ((block_index_i >> i)) + (2 ** (self.NUM_WAYS_W - i) - 1)
                        ](block_index_i[i - 1], blk=True)
                        for i in range(1, self.NUM_WAYS_W + 1)
                    ],
                    # Find out which block should be replaced next
                    tmp_repl(0, blk=True),
                    [
                        (
                            # FIXME This should work but it's not pretty, but there's a problem with verilator
                            # only allowing operands of an arithmetic operation to have the same width
                            # So I cant just say 2*tmp_repl+2-plru_bits[...][...]
                            If(plru_bits[set_index_i][tmp_repl[: self.NUM_WAYS_W]])(
                                tmp_repl(2 * tmp_repl + 1, blk=True),
                            ).Else(
                                tmp_repl(2 * tmp_repl + 2, blk=True),
                            )
                        )
                        for _ in range(self.NUM_WAYS_W)
                    ],
                    tmp_repl(tmp_repl - self.NUM_WAYS + 1, blk=True),
                    next_replacement_o_reg[set_index_i](
                        tmp_repl[: self.NUM_WAYS_W], blk=True
                    ),
                )
            )

        return m
