from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out


class ReplacementPolicy(wiring.Component):
    def __init__(self, num_ways: int, num_sets: int, policy: str) -> None:
        """Replacement policy generator.

        Args:
            num_ways (int): Number of ways. Must be a power of 2.
            num_sets (int): Number of sets. Must be a power of 2 and (for now) at least 2.
            policy (str): Can be either "fifo", "plru_mru", "plru_tree" or "lru".
        """
        self.num_ways = num_ways
        self.num_sets = num_sets
        self.policy = policy

        io_ports = {
            "access_i": In(1),
            "replace_i": In(1),
            "set_i": In(range(num_sets)),
            "way_i": In(range(num_ways)),
        }

        for i in range(num_sets):
            io_ports[f"next_replacement_{i}_o"] = Out(range(num_ways))

        super().__init__(io_ports)

    def next_replacement(self, index: int):
        return getattr(self, f"next_replacement_{index}_o")

    def elaborate(self, platform) -> Module:
        m = Module()

        # Create an array for the way indices so we can access these registers using signals.
        # Then assign them to the actual outputs.
        next_replacement_regs = Array(
            [Signal(range(self.num_ways)) for _ in range(self.num_sets)]
        )
        for i in range(self.num_sets):
            m.d.comb += self.next_replacement(i).eq(next_replacement_regs[i])

        if self.policy == "fifo":
            with m.If(self.replace_i):
                m.d.sync += next_replacement_regs[self.set_i].eq(
                    next_replacement_regs[self.set_i] + 1
                )

        return m
