from math import ceil, log2
from enum import Enum
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

from acaverilog.generators.cache.generators.one_hot_to_bin_generator import (
    OneHotToBinGenerator,
)
from acaverilog.generators.cache.generators.replacement_policy_generator import (
    ReplacementPolicyGenerator,
)

# from acadl import ACADLObject

# from .acadl_object_generator import ACADLObjectGenerator


class States(Enum):
    READY = 0
    HIT_LOOKUP = 1
    HIT_LOOKUP_DONE = 2
    REQUEST_TO_LOWER_MEM_SENT = 3
    WAIT_FOR_LOWER_MEM = 4
    STALL = 5


# class CacheGenerator(ACADLObjectGenerator):
class CacheGenerator:

    # def __init__(
    #     self,
    #     acadl_object: ACADLObject,
    # ) -> None:
    #     super().__init__(acadl_object)

    def __init__(
        self,
        data_width: int,
        address_width: int,
        num_ways: int,
        num_sets: int,
        replacement_policy: str,
        hit_latency: int,
        miss_latency: int,
        write_through: bool,
        write_allocate: bool,
    ) -> None:
        """Cache Generator.

        Args:
            data_width (int): Width of one data word in bits.
            address_width (int): Width of the addresses in bits.
            num_ways (int): Number of ways. Must be a power of 2.
            num_sets (int): Number of sets. Must be a power of 2 and (for now) at least 2.
            replacement_policy (str): Either "fifo" or "plru_tree"
            hit_latency (int): hit latency of the cache (in addition to any time the lower memory might need). Must be at least 6.
            miss_latency (int): miss latency of the cache (in addition to any time the lower memory might need). Must be at least 6.
            write_through (bool): Use write-through or write-back policy
            write_allocate (bool): Use write-allocate or write-no-allocate policy
        """
        self.DATA_WIDTH = data_width
        self.ADDRESS_WIDTH = address_width
        self.NUM_WAYS = num_ways
        self.NUM_SETS = num_sets
        self.REPLACEMENT_POLICY = replacement_policy
        self.HIT_LATENCY = hit_latency
        self.MISS_LATENCY = miss_latency
        self.WRITE_BACK = not write_through
        self.WRITE_ALLOCATE = write_allocate

        # Internal Constants
        self.NUM_WAYS_W = int(log2(self.NUM_WAYS))
        self.LATENCY_COUNTER_SIZE = ceil(log2(max(self.HIT_LATENCY, self.MISS_LATENCY)))
        self.INDEX_WIDTH = int(log2(self.NUM_SETS))
        self.TAG_WIDTH = self.ADDRESS_WIDTH - self.INDEX_WIDTH
        self.STATE_REG_WIDTH = ceil(log2(len(States)))

    def generate_module(self) -> Module:
        # m = Module(self.base_file_name)
        m = Module("cache")

        # Front End Inputs
        clk_i = m.Input("clk_i")
        reset_n_i = m.Input("reset_n_i")
        fe_address_i = m.Input("fe_address_i", self.ADDRESS_WIDTH)
        fe_address_valid_i = m.Input("fe_address_valid_i")
        fe_write_data_i = m.Input("fe_write_data_i", self.DATA_WIDTH)
        fe_write_data_valid_i = m.Input("fe_write_data_valid_i")
        fe_read_write_select_i = m.Input("fe_read_write_select_i")

        # Front End Outputs
        fe_read_data_o = m.Output("fe_read_data_o", self.DATA_WIDTH)
        fe_read_data_valid_o = m.Output("fe_read_data_valid_o")
        fe_write_done_o = m.Output("fe_write_done_o")
        fe_port_ready_o = m.Output("fe_port_ready_o")
        fe_hit_o = m.Output("fe_hit_o")

        # Back End Inputs
        be_read_data_i = m.Input("be_read_data_i", self.DATA_WIDTH)
        be_read_data_valid_i = m.Input("be_read_data_valid_i")
        be_write_done_i = m.Input("be_write_done_i")
        be_port_ready_i = m.Input("be_port_ready_i")

        # Back End Outputs
        be_address_o = m.Output("be_address_o", self.ADDRESS_WIDTH)
        be_address_valid_o = m.Output("be_address_valid_o")
        be_write_data_o = m.Output("be_write_data_o", self.DATA_WIDTH)
        be_write_data_valid_o = m.Output("be_write_data_valid_o")
        be_read_write_select_o = m.Output("be_read_write_select_o")

        # Front End Input Buffers
        fe_address_i_reg = m.Reg("fe_address_i_reg", self.ADDRESS_WIDTH)
        fe_write_data_i_reg = m.Reg("fe_write_data_i_reg", self.DATA_WIDTH)
        fe_read_write_select_i_reg = m.Reg("fe_read_write_select_i_reg")

        # Front End Output Buffers
        fe_read_data_o_reg = m.Reg("fe_read_data_o_reg", self.DATA_WIDTH)
        fe_read_data_valid_o_reg = m.Reg("fe_read_data_valid_o_reg")
        fe_write_done_o_reg = m.Reg("fe_write_done_o_reg")

        # Back End Output Buffers
        be_address_o_reg = m.Reg("be_address_o_reg", self.ADDRESS_WIDTH)
        be_address_valid_o_reg = m.Reg("be_address_valid_o_reg")
        be_write_data_o_reg = m.Reg("be_write_data_o_reg", self.DATA_WIDTH)
        be_write_data_valid_o_reg = m.Reg("be_write_data_valid_o_reg")
        be_read_write_select_o_reg = m.Reg("be_read_write_select_o_reg")

        # Frontend Output Buffer Assignments
        m.Assign(fe_read_data_o(fe_read_data_o_reg))
        m.Assign(fe_read_data_valid_o(fe_read_data_valid_o_reg))
        m.Assign(fe_write_done_o(fe_write_done_o_reg))

        # Backend Output Buffer Assignments
        m.Assign(be_address_o(be_address_o_reg))
        m.Assign(be_address_valid_o(be_address_valid_o_reg))
        m.Assign(be_write_data_o(be_write_data_o_reg))
        m.Assign(be_write_data_valid_o(be_write_data_valid_o_reg))
        m.Assign(be_read_write_select_o(be_read_write_select_o_reg))

        # Internal
        state_reg = m.Reg("state_reg", self.STATE_REG_WIDTH)
        latency_counter = m.Reg("latency_counter", self.LATENCY_COUNTER_SIZE)
        hit_valid = m.Reg("hit_valid")
        address_tag = m.Wire("address_tag", self.TAG_WIDTH)
        address_index = m.Wire("address_index", self.INDEX_WIDTH)
        hit_vector = m.Reg("hit_vector", self.NUM_WAYS)
        tag_memory = m.Reg(
            f"tag_memory", self.TAG_WIDTH, dims=(self.NUM_WAYS, self.NUM_SETS)
        )
        valid_memory = m.Reg("valid_memory", 1, dims=(self.NUM_WAYS, self.NUM_SETS))
        data_memory = m.Reg(
            f"data_memory", self.DATA_WIDTH, dims=(self.NUM_WAYS, self.NUM_SETS)
        )
        next_block_replacement = m.Reg(
            "next_block_replacement", max(1, self.NUM_WAYS_W)
        )  # the index of the block to be replaced next (for the current address index)

        if self.WRITE_BACK:
            dirty_memory = m.Reg("dirty_memory", 1, dims=(self.NUM_WAYS, self.NUM_SETS))
            # Buffers for read requests if data was dirty and needs to be written back before the read request
            dirty_address = m.Reg("dirty_address", self.ADDRESS_WIDTH)
            dirty_req_valid = m.Reg("dirty_address_valid")
        m.Assign(fe_port_ready_o(state_reg == States.READY.value))
        m.Assign(address_tag(fe_address_i_reg[self.INDEX_WIDTH :]))
        m.Assign(address_index(fe_address_i_reg[: self.INDEX_WIDTH]))
        m.Assign(fe_hit_o(hit_vector != 0))

        if self.NUM_WAYS == 1:
            hit_index = m.Reg(
                "hit_index"
            )  # the index of the way that created a hit (as binary, not one hot)
            m.Assign(hit_index(0))
            m.Assign(next_block_replacement(0))
        else:
            hit_index = m.Reg("hit_index", self.NUM_WAYS_W)
            repl_pol_access = m.Reg("repl_pol_access")
            repl_pol_replace = m.Reg("repl_pol_replace")
            repl_pol_block_index_o = m.Reg("repl_pol_block_index_o", max(1, self.NUM_WAYS_W))
            next_to_replace_regs = m.Reg(
                "next_to_replace_regs", max(1, self.NUM_WAYS_W), dims=self.NUM_SETS
            )
            Submodule(
                m,
                OneHotToBinGenerator(self.NUM_WAYS).generate_module(),
                "hit_one_hot_to_bin",
                arg_ports=(("one_hot_i", hit_vector), ("bin_o", hit_index)),
            )
            Submodule(
                m,
                ReplacementPolicyGenerator(
                    self.NUM_WAYS, self.NUM_SETS, self.REPLACEMENT_POLICY
                ).generate_module(),
                "replacement_policy",
                arg_ports=(
                    ("clk_i", clk_i),
                    ("reset_n_i", reset_n_i),
                    ("access_i", repl_pol_access),
                    ("replace_i", repl_pol_replace),
                    ("block_index_i", repl_pol_block_index_o),
                    ("set_index_i", address_index),
                    ("next_replacement_o", next_to_replace_regs),
                ),
            )

        m.Always(Posedge(clk_i))(
            If(state_reg == States.READY.value)(
                # Cache is ready for a new request
                If(
                    OrList(
                        AndList(fe_read_write_select_i == 0, fe_address_valid_i == 1),
                        AndList(
                            fe_read_write_select_i == 1,
                            fe_write_data_valid_i == 1,
                            fe_address_valid_i == 1,
                        ),
                    )
                )(
                    # Read Request
                    state_reg(States.HIT_LOOKUP.value),
                    fe_read_data_valid_o_reg(0),
                    fe_write_done_o_reg(0),
                    # Buffer Inputs
                    fe_address_i_reg(fe_address_i),
                    fe_write_data_i_reg(fe_write_data_i),
                    fe_read_write_select_i_reg(fe_read_write_select_i),
                    # Get the index of the block that should be replaced next in case we need to replace something
                    (
                        [next_block_replacement(next_to_replace_regs[address_index])]
                        if self.NUM_WAYS > 1
                        else []
                    ),
                )
            )
            .Elif(state_reg == States.HIT_LOOKUP.value)(
                # Check whether we have a hit
                [
                    hit_vector[i](
                        AndList(
                            tag_memory[i][address_index] == address_tag,
                            valid_memory[i][address_index] == 1,
                        )
                    )
                    for i in range(self.NUM_WAYS)
                ],
                hit_valid(1),
                latency_counter.inc(),
                state_reg(States.HIT_LOOKUP_DONE.value),
            )
            .Elif(state_reg == States.HIT_LOOKUP_DONE.value)(
                # Hit lookup has finished
                If(fe_read_write_select_i_reg == 0)(
                    # Read Request
                    If(fe_hit_o == 1)(
                        # We have a hit
                        # Simply read the data from the cache
                        fe_read_data_o_reg(data_memory[hit_index][address_index]),
                        state_reg(States.STALL.value),
                        # Update replacement policy
                        (
                            [
                                repl_pol_access(1),
                                repl_pol_block_index_o(hit_index),
                            ]
                            if self.NUM_WAYS > 1
                            else []
                        ),
                    ).Else(
                        # We have a miss
                        (
                            (
                                [
                                    # In case of write back...
                                    If(
                                        dirty_memory[next_block_replacement][address_index]
                                        == 1
                                    )(
                                        # Write the data to be replaced back if it is dirty
                                        be_address_o_reg[: self.INDEX_WIDTH](
                                            address_index
                                        ),
                                        be_address_o_reg[self.INDEX_WIDTH :](
                                            tag_memory[next_block_replacement][address_index]
                                        ),
                                        be_address_valid_o_reg(1),
                                        be_read_write_select_o_reg(1),
                                        be_write_data_o_reg(
                                            data_memory[next_block_replacement][
                                                address_index
                                            ]
                                        ),
                                        be_write_data_valid_o_reg(1),
                                        # Buffer a read request to the lower memory
                                        dirty_address(fe_address_i_reg),
                                        dirty_req_valid(1),
                                        state_reg(
                                            States.REQUEST_TO_LOWER_MEM_SENT.value
                                        ),
                                    ).Else(
                                        # Send a read request to the lower memory
                                        be_address_o_reg(fe_address_i_reg),
                                        be_address_valid_o_reg(1),
                                        be_read_write_select_o_reg(0),
                                        state_reg(
                                            States.REQUEST_TO_LOWER_MEM_SENT.value
                                        ),
                                    ),
                                    # Mark the cache block to be replaced as non-dirty
                                    dirty_memory[next_block_replacement][address_index](0),
                                ]
                                if self.WRITE_BACK
                                else [
                                    # Send a read request to the lower memory
                                    be_address_o_reg(fe_address_i_reg),
                                    be_address_valid_o_reg(1),
                                    be_read_write_select_o_reg(0),
                                    state_reg(States.REQUEST_TO_LOWER_MEM_SENT.value),
                                ]
                            ),
                            # Update replacement policy
                            (
                                [
                                    repl_pol_access(1),
                                    repl_pol_replace(1),
                                    repl_pol_block_index_o(next_block_replacement),
                                ]
                                if self.NUM_WAYS > 1
                                else []
                            ),
                        ),
                    )
                ).Else(
                    # Write Request
                    If(fe_hit_o)(
                        # We have a hit
                        # update data in cache;
                        # valid and tag dont need to be updated
                        data_memory[hit_index][address_index](fe_write_data_i_reg),
                        # Update replacement policy
                        (
                            [
                                repl_pol_access(1),
                                repl_pol_block_index_o(hit_index),
                            ]
                            if self.NUM_WAYS > 1
                            else []
                        ),
                        (
                            # In case of write back, mark the cache block as dirty
                            [
                                dirty_memory[hit_index][address_index](1),
                                state_reg(States.STALL.value),
                            ]
                            if self.WRITE_BACK
                            else [
                                # In case of write through, send write request to lower memory
                                be_address_o_reg(fe_address_i_reg),
                                be_address_valid_o_reg(1),
                                be_read_write_select_o_reg(1),
                                be_write_data_o_reg(fe_write_data_i_reg),
                                be_write_data_valid_o_reg(1),
                                state_reg(States.REQUEST_TO_LOWER_MEM_SENT.value),
                            ]
                        ),
                    ).Else(
                        # We have a miss
                        [
                            # In case of write allocate...
                            # Write data to the cache
                            valid_memory[next_block_replacement][address_index](1),
                            data_memory[next_block_replacement][address_index](
                                fe_write_data_i_reg
                            ),
                            # Update replacement policy
                            tag_memory[next_block_replacement][address_index](address_tag),
                            (
                                (
                                    [
                                        repl_pol_access(1),
                                        repl_pol_replace(1),
                                        repl_pol_block_index_o(next_block_replacement),
                                    ]
                                    if self.NUM_WAYS > 1
                                    else []
                                ),
                                (
                                    [
                                        # In case of write back...
                                        # Mark block as dirty
                                        dirty_memory[next_block_replacement][address_index](
                                            1
                                        ),
                                        If(
                                            dirty_memory[next_block_replacement][
                                                address_index
                                            ]
                                        )(
                                            # Write back data to be replaced if it is dirty
                                            be_address_o_reg[: self.INDEX_WIDTH](
                                                address_index
                                            ),
                                            be_address_o_reg[self.INDEX_WIDTH :](
                                                tag_memory[next_block_replacement][
                                                    address_index
                                                ]
                                            ),
                                            be_address_valid_o_reg(1),
                                            be_read_write_select_o_reg(1),
                                            be_write_data_o_reg(
                                                data_memory[next_block_replacement][
                                                    address_index
                                                ]
                                            ),
                                            be_write_data_valid_o_reg(1),
                                            state_reg(
                                                States.REQUEST_TO_LOWER_MEM_SENT.value
                                            ),
                                        ).Else(
                                            state_reg(States.STALL.value)
                                        ),
                                    ]
                                    if self.WRITE_BACK
                                    else [
                                        # write data to lower memory
                                        be_address_o_reg(fe_address_i_reg),
                                        be_address_valid_o_reg(1),
                                        be_write_data_o_reg(fe_write_data_i_reg),
                                        be_write_data_valid_o_reg(1),
                                        be_read_write_select_o_reg(1),
                                        state_reg(
                                            States.REQUEST_TO_LOWER_MEM_SENT.value
                                        ),
                                    ]
                                ),
                            ),
                        ]
                        if self.WRITE_ALLOCATE
                        else [
                            # write data to lower memory
                            be_address_o_reg(fe_address_i_reg),
                            be_address_valid_o_reg(1),
                            be_write_data_o_reg(fe_write_data_i_reg),
                            be_write_data_valid_o_reg(1),
                            be_read_write_select_o_reg(1),
                            state_reg(States.REQUEST_TO_LOWER_MEM_SENT.value),
                        ]
                    )
                ),
                latency_counter.inc(),
            )
            .Elif(state_reg == States.REQUEST_TO_LOWER_MEM_SENT.value)(
                # Stall one cycle so the lower memory can accept the request and switch to port not ready
                state_reg(States.WAIT_FOR_LOWER_MEM.value),
                # Add one cycle to the latency counter because we're only gonna react to the response of the lower memory one cycle later
                latency_counter.inc(),
                # stop updating the replacement policy
                [repl_pol_access(0), repl_pol_replace(0)] if self.NUM_WAYS > 1 else [],
            )
            .Elif(state_reg == States.WAIT_FOR_LOWER_MEM.value)(
                # Waiting for the lower memory to fulfill the request
                If(
                    # Check if the lower memory is done
                    OrList(be_read_data_valid_i, be_write_done_i),
                )(
                    # Request to main memory was processed, we can now
                    # a) hand the data out and write it to the cache in case of a read.
                    #    The dirty bit will already have been set in case of write back.
                    # b) do nothing in case of a write - in case of write_back, the data
                    # will already have been written to the cache before. In case of write_through,
                    # nothing needs to be done anyway
                    latency_counter.inc(),
                    state_reg(States.STALL.value),
                    If(be_read_write_select_o_reg == 0)(
                        fe_read_data_o_reg(be_read_data_i),
                        data_memory[next_block_replacement][address_index](be_read_data_i),
                        valid_memory[next_block_replacement][address_index](1),
                        tag_memory[next_block_replacement][address_index](address_tag),
                    ),
                    [
                        (
                            If(dirty_req_valid)(
                                be_address_o_reg(dirty_address),
                                be_address_valid_o_reg(1),
                                be_read_write_select_o_reg(0),
                                state_reg(States.REQUEST_TO_LOWER_MEM_SENT.value),
                                dirty_req_valid(0),
                            )
                            if self.WRITE_BACK
                            else []
                        )
                    ],
                ).Else(
                    # Invalidate the address so as to not send another request
                    be_address_valid_o_reg(0)
                )
            )
            .Elif(state_reg == States.STALL.value)(
                # Stall for the remaining time (or error if this took too much time...?)
                latency_counter.inc(),
                [repl_pol_access(0), repl_pol_replace(0)] if self.NUM_WAYS > 1 else [],
                If(
                    OrList(
                        AndList(latency_counter == self.HIT_LATENCY - 1, fe_hit_o == 1),
                        AndList(
                            latency_counter == self.MISS_LATENCY - 1, fe_hit_o == 0
                        ),
                    )
                )(
                    # We have stalled enough, finish the request
                    fe_read_data_valid_o_reg(Not(fe_read_write_select_i_reg)),
                    fe_write_done_o_reg(fe_read_write_select_i_reg),
                    state_reg(States.READY.value),
                    hit_valid(0),
                    latency_counter(0),
                    [dirty_req_valid(0)] if self.WRITE_BACK else [],
                ),
            )
        )
        return m
