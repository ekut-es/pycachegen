from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out
from amaranth.utils import exact_log2


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

        self.num_ways_width = exact_log2(num_ways)

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
        elif self.policy == "plru_tree":
            # Array of the tree bits. Store one tree per set.
            # Imagine that the leaves of a tree are the blocks, so there are num_ways leaves per tree.
            # We only need to store one bit for each node above the leaves (so num_ways-1 bits) since
            # the blocks themselves are not of interest.
            # a 1 means that the newest block is within the left subtree ("first" child),
            # a 0 means that it is within the right subtree ("second" child)
            # This does two noteworthy things:
            # 1) When collecting the bits on the path from the root to the newest leaf, they are the inverse
            #    of the index of that block ("the way of the block"). This is useful for when a block gets accessed
            #    since the inverse of the way_i input is already the bits that we need to place on the path
            # 2) The bits on the path to the oldest block are that block's index. This means that when walking down
            #    to the oldest block, at each layer we can compute the position we're currently at by looking at the
            #    bits we've already visited.
            plru_bits = Array(
                [Signal(unsigned(self.num_ways - 1)) for _ in range(self.num_sets)]
            )

            # For each access, update the tree bits
            with m.If(self.access_i):
                # Walk from the leaf up to the root node
                # for each layer, compute the index of the bit in the tree
                for i in range(1, self.num_ways_width + 1):
                    # this is the index of the bit to modify within the layer of the bit itself
                    # i starts at 1 and it will give us the index within the last layer of the tree
                    index_within_layer = self.way_i >> i
                    # now find out the index of the first bit of the current layer with respect to the whole tree
                    # this is just the number of nodes above the current layer
                    index_of_first_bit = (self.num_ways >> i) - 1
                    # so if we add those two together, we get the index of the bit we want to modify
                    total_bit_index = index_within_layer + index_of_first_bit

                    # When we access a block, we want to update all the bits along the path
                    # so that that specific block becomes the newest one
                    # to do so, we just have to enter the negated i-th bit (index i-1) of the accessed way/block
                    new_bit = ~self.way_i[i - 1]

                    # finally update the bit
                    m.d.sync += (
                        plru_bits[self.set_i].bit_select(total_bit_index, 1).eq(new_bit)
                    )

            # Compute the next way to replace for each set
            for next_replacement, bits in zip(next_replacement_regs, plru_bits):
                # To do this, we basically do the opposite of what we did when a way gets accessed
                # Walk from the root down to the leaf. Each layer will add one bit the the way to replace (next_replacement).
                # At the first layer, the next_replacement bit simply gets set to bits[0]
                # At the following layers, use the previous bits (next_replacement[self.num_ways_width-i:]) to compute
                # the position we're currently at. Then use that current position to compute the position of the left/right child,
                # depending on what the current bit is. With this new position, we can lookup the new bit for next_replacement[self.num_ways_width - 1 - i].
                for i in range(self.num_ways_width):
                    # the previous next_replacement bits indicate the index of the current bit within the current row/layer
                    index_within_layer = next_replacement[self.num_ways_width - i :]
                    # the index of the first bit inside this layer is just the number of nodes in the previous layers
                    index_of_first_bit = 2**i - 1
                    # if we add those two together, we get the total index
                    total_bit_index = index_within_layer + index_of_first_bit

                    # now assign the plru_bits bit at that position to the next_replacement bit
                    m.d.comb += next_replacement[self.num_ways_width - 1 - i].eq(
                        bits.bit_select(total_bit_index, 1)
                    )

        return m
