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
    Or,
    And,
)

from acaverilog.generators.cache.generators.one_hot_to_bin_generator import (
    OneHotToBinGenerator,
)
from acaverilog.generators.cache.generators.replacement_policy_generator import (
    ReplacementPolicyGenerator,
)
from acaverilog.generators.cache.generators.priority_encoder_generator import (
    PriorityEncoderGenerator,
)

# from acadl import ACADLObject

# from .acadl_object_generator import ACADLObjectGenerator


class States(Enum):
    READY = 0
    HIT_LOOKUP = 1
    HIT_LOOKUP_DONE = 2
    WRITE_BACK_BLOCK = 3
    READ_BLOCK = 4
    READ_BLOCK_DONE = 5
    SEND_MEM_REQUEST = 6
    SEND_MEM_REQUEST_WAIT = 7
    STALL = 8
    FLUSH_COMPUTE_NEXT = 9
    FLUSH_PREPARE_WRITE_BACK = 10


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
        block_size: int,
        prefix: str,
    ) -> None:
        """Cache Generator.

        Args:
            data_width (int): Width of one data word in bits.
            address_width (int): Width of the addresses in bits.
            num_ways (int): Number of ways. Must be a power of 2.
            num_sets (int): Number of sets. Must be a power of 2.
            replacement_policy (str): Can be either "fifo", "plru_mru" or "plru_tree"
            hit_latency (int): hit latency of the cache (in addition to any time the lower memory might need). Must be at least 6.
            miss_latency (int): miss latency of the cache (in addition to any time the lower memory might need). Must be at least 6.
            write_through (bool): Use write-through or write-back policy
            write_allocate (bool): Use write-allocate or write-no-allocate policy
            block_size (int): Number of words per block. Must be a power of 2.
            prefix (str): Prefix to be used for this module's name
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
        self.BLOCK_SIZE = block_size
        self.PREFIX = prefix

        # Internal Constants
        self.NUM_WAYS_W = int(log2(self.NUM_WAYS))
        self.NUM_SETS_W = int(log2(self.NUM_SETS))
        self.LATENCY_COUNTER_SIZE = ceil(log2(max(self.HIT_LATENCY, self.MISS_LATENCY)))
        self.INDEX_WIDTH = int(log2(self.NUM_SETS))
        self.WORD_OFFSET_W = int(log2(self.BLOCK_SIZE))
        self.TAG_WIDTH = self.ADDRESS_WIDTH - self.INDEX_WIDTH - self.WORD_OFFSET_W
        self.STATE_REG_WIDTH = ceil(log2(len(States)))

    def generate_module(self) -> Module:
        # m = Module(self.base_file_name)
        m = Module(f"{self.PREFIX}cache")

        # Front End Inputs
        clk_i = m.Input("clk_i")
        reset_n_i = m.Input("reset_n_i")
        flush_i = m.Input("flush_i")
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
        be_port_ready_i = m.Input(
            "be_port_ready_i"
        )

        # Back End Outputs
        be_address_o = m.Output("be_address_o", self.ADDRESS_WIDTH)
        be_address_valid_o = m.Output("be_address_valid_o")
        be_write_data_o = m.Output("be_write_data_o", self.DATA_WIDTH)
        be_write_data_valid_o = m.Output("be_write_data_valid_o")
        be_read_write_select_o = m.Output("be_read_write_select_o")

        # Front End Input Buffers
        flush_i_reg = m.Reg("flush_i_reg")
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

        ## Internal
        # Registers
        state_reg = m.Reg("state_reg", self.STATE_REG_WIDTH)
        latency_counter = m.Reg("latency_counter", self.LATENCY_COUNTER_SIZE)
        hit_valid = m.Reg("hit_valid")
        hit_vector = m.Reg("hit_vector", self.NUM_WAYS)
        send_mem_request_next_state = m.Reg(
            "send_mem_request_next_state", self.STATE_REG_WIDTH
        )
        read_block_word_offset = m.Reg(
            "read_block_word_offset", max(1, self.WORD_OFFSET_W)
        )

        # Assignments to frontend signals
        m.Assign(fe_port_ready_o(state_reg == States.READY.value))
        m.Assign(fe_hit_o(hit_vector != 0))

        # Wires with assignments
        address_word_offset = m.Wire("address_word_offset", max(1, self.WORD_OFFSET_W))
        address_index = m.Wire("address_index", max(1, self.INDEX_WIDTH))
        address_tag = m.Wire("address_tag", self.TAG_WIDTH)
        if self.BLOCK_SIZE == 1:
            m.Assign(address_word_offset(0))
        else:
            m.Assign(address_word_offset(fe_address_i_reg[: self.WORD_OFFSET_W]))
        if self.NUM_SETS == 1:
            m.Assign(address_index(0))
        else:
            m.Assign(
                address_index(
                    fe_address_i_reg[
                        self.WORD_OFFSET_W : self.WORD_OFFSET_W + self.INDEX_WIDTH
                    ]
                )
            )
        m.Assign(address_tag(fe_address_i_reg[self.WORD_OFFSET_W + self.INDEX_WIDTH :]))

        # Memories
        tag_memory = m.Reg(
            f"tag_memory", self.TAG_WIDTH, dims=(self.NUM_WAYS, self.NUM_SETS)
        )
        valid_memory = m.Reg("valid_memory", 1, dims=(self.NUM_WAYS, self.NUM_SETS))
        data_memory = m.Reg(
            f"data_memory",
            self.DATA_WIDTH,
            dims=(self.NUM_WAYS, self.NUM_SETS, self.BLOCK_SIZE),
        )

        # Things that are only needed for write back
        if self.WRITE_BACK:
            dirty_memory = m.Reg("dirty_memory", 1, dims=(self.NUM_WAYS, self.NUM_SETS))
            write_back_address_index = m.Reg(
                "write_back_address_index", max(1, self.INDEX_WIDTH)
            )
            write_back_block_index = m.Reg(
                "write_back_block_index", max(1, self.NUM_WAYS_W)
            )
            write_back_tag = m.Reg("write_back_tag", self.TAG_WIDTH)
            write_back_word_offset = m.Reg(
                "write_back_word_offset", max(1, self.WORD_OFFSET_W)
            )
            write_back_next_state = m.Reg("write_back_next_state", self.STATE_REG_WIDTH)
            # Flush functionality
            flush_encoder_input = m.Wire("flush_encoder_input", self.NUM_SETS)
            flush_next_set_index = m.Wire(
                "flush_next_set_index", max(1, ceil(log2(self.NUM_SETS)))
            )
            flush_current_block_index = m.Reg(
                "flush_current_block_index", max(1, self.NUM_WAYS_W)
            )
            for i in range(self.NUM_SETS):
                m.Assign(
                    flush_encoder_input[i](
                        And(
                            valid_memory[flush_current_block_index][i],
                            dirty_memory[flush_current_block_index][i],
                        )
                    )
                )

            Submodule(
                m,
                PriorityEncoderGenerator(
                    width_unencoded=self.NUM_SETS, prefix=self.PREFIX
                ).generate_module(),
                f"{self.PREFIX}flush_priority_encoder",
                arg_ports=(
                    ("unencoded_i", flush_encoder_input),
                    ("encoded_o", flush_next_set_index),
                ),
            )

        # Things that are only needed for direct mapped cache
        if self.NUM_WAYS == 1:
            hit_index = m.Wire(
                "hit_index"
            )  # the index of the way that created a hit (as binary, not one hot)
            next_block_replacement = m.Wire(
                "next_block_replacement"
            )  # the index of the block to be replaced next (for the current address index)
            m.Assign(hit_index(0))
            m.Assign(next_block_replacement(0))
        # Things that are only needed for set associative caches
        else:
            hit_index = m.Wire(
                "hit_index", self.NUM_WAYS_W
            )  # the index of the way that created a hit (as binary, not one hot)
            next_block_replacement = m.Reg(
                "next_block_replacement", self.NUM_WAYS_W
            )  # the index of the block to be replaced next (for the current address index)
            repl_pol_access = m.Reg("repl_pol_access")
            repl_pol_replace = m.Reg("repl_pol_replace")
            repl_pol_block_index = m.Reg(
                "repl_pol_block_index_o", max(1, self.NUM_WAYS_W)
            )
            next_replacements = m.Wire(
                "next_replacements", max(1, self.NUM_WAYS_W), dims=self.NUM_SETS
            )
            Submodule(
                m,
                OneHotToBinGenerator(
                    num_inputs=self.NUM_WAYS, prefix=self.PREFIX
                ).generate_module(),
                f"{self.PREFIX}hit_one_hot_to_bin",
                arg_ports=(("one_hot_i", hit_vector), ("bin_o", hit_index)),
            )
            Submodule(
                m,
                ReplacementPolicyGenerator(
                    num_ways=self.NUM_WAYS,
                    num_sets=self.NUM_SETS,
                    policy=self.REPLACEMENT_POLICY,
                    prefix=self.PREFIX,
                ).generate_module(),
                f"{self.PREFIX}replacement_policy",
                arg_ports=(
                    ("clk_i", clk_i),
                    ("reset_n_i", reset_n_i),
                    ("access_i", repl_pol_access),
                    ("replace_i", repl_pol_replace),
                    ("block_index_i", repl_pol_block_index),
                    ("set_index_i", address_index),
                    ("next_replacement_o", next_replacements),
                ),
            )

        m.Always(Negedge(reset_n_i), Posedge(clk_i))(
            If(Not(reset_n_i))(
                ## reset
                # frontend input buffers
                fe_address_i_reg(0),
                fe_write_data_i_reg(0),
                fe_read_write_select_i_reg(0),
                # frontend output buffers
                fe_read_data_o_reg(0),
                fe_read_data_valid_o_reg(0),
                fe_write_done_o_reg(0),
                # backend outputs
                be_address_o_reg(0),
                be_address_valid_o_reg(0),
                be_write_data_o_reg(0),
                be_write_data_valid_o_reg(0),
                be_read_write_select_o_reg(0),
                # internal registers
                state_reg(States.READY.value),
                latency_counter(0),
                hit_valid(0),
                hit_vector(0),
                send_mem_request_next_state(0),
                read_block_word_offset(0),
                # internal memories
                [
                    [
                        [
                            tag_memory[block_idx][set_idx](0),
                            valid_memory[block_idx][set_idx](0),
                            [
                                data_memory[block_idx][set_idx][word_idx](0)
                                for word_idx in range(self.BLOCK_SIZE)
                            ],
                        ]
                        for set_idx in range(self.NUM_SETS)
                    ]
                    for block_idx in range(self.NUM_WAYS)
                ],
                # write back things
                (
                    [
                        write_back_address_index(0),
                        write_back_block_index(0),
                        write_back_next_state(0),
                        write_back_tag(0),
                        write_back_word_offset(0),
                        [
                            [
                                dirty_memory[block_idx][set_idx](0)
                                for set_idx in range(self.NUM_SETS)
                            ]
                            for block_idx in range(self.NUM_WAYS)
                        ],
                    ]
                    if self.WRITE_BACK
                    else []
                ),
                # things for set associative caches
                (
                    [
                        next_block_replacement(0),
                        repl_pol_access(0),
                        repl_pol_replace(0),
                        repl_pol_block_index(0),
                    ]
                    if self.NUM_WAYS > 1
                    else []
                ),
            )
            .Elif(state_reg == States.READY.value)(
                # Cache is ready for a new request
                # Accept flush signals
                flush_i_reg(Or(flush_i_reg, flush_i)),
                If(AndList(self.WRITE_BACK, OrList(flush_i, flush_i_reg)))(
                    state_reg(States.FLUSH_COMPUTE_NEXT.value),
                ).Elif(
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
                ),
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
                # Get the index of the block that should be replaced next in case we need to replace something
                (
                    [next_block_replacement(next_replacements[address_index])]
                    if self.NUM_WAYS > 1
                    else []
                ),
                state_reg(States.HIT_LOOKUP_DONE.value),
            )
            .Elif(state_reg == States.HIT_LOOKUP_DONE.value)(
                latency_counter.inc(),
                If(fe_hit_o)(
                    # we have a hit
                    # update the replacement policy state
                    (
                        [repl_pol_access(1), repl_pol_block_index(hit_index)]
                        if self.NUM_WAYS > 1
                        else []
                    ),
                    If(fe_read_write_select_i_reg)(
                        # write
                        data_memory[hit_index][address_index][address_word_offset](
                            fe_write_data_i_reg
                        ),
                        (
                            [
                                dirty_memory[hit_index][address_index](1),
                                state_reg(States.STALL.value),
                            ]
                            if self.WRITE_BACK
                            else [
                                # in case of write through, we still need to write to the next level memory
                                be_address_o_reg(fe_address_i_reg),
                                be_write_data_valid_o_reg(1),
                                be_write_data_o_reg(fe_write_data_i_reg),
                                be_read_write_select_o_reg(1),
                                state_reg(States.SEND_MEM_REQUEST.value),
                                send_mem_request_next_state(States.STALL.value),
                            ]
                        ),
                    ).Else(
                        # read
                        fe_read_data_o_reg(
                            data_memory[hit_index][address_index][address_word_offset]
                        ),
                        state_reg(States.STALL.value),
                    ),
                ).Else(
                    # we have a miss
                    If(And(not self.WRITE_ALLOCATE, fe_read_write_select_i_reg))(
                        # write request and write-no-allocate -> only write to memory
                        be_address_o_reg(fe_address_i_reg),
                        be_write_data_o_reg(fe_write_data_i_reg),
                        be_write_data_valid_o_reg(1),
                        be_read_write_select_o_reg(1),
                        state_reg(States.SEND_MEM_REQUEST.value),
                        send_mem_request_next_state(States.STALL.value),
                    ).Else(
                        # We have to replace a block
                        # Update valid and dirty bits and the tag
                        valid_memory[next_block_replacement][address_index](1),
                        tag_memory[next_block_replacement][address_index](address_tag),
                        (
                            # mark dirty if write, else remove dirty bit
                            dirty_memory[next_block_replacement][address_index](
                                fe_read_write_select_i_reg
                            )
                            if self.WRITE_BACK
                            else []
                        ),
                        # Update the replacement policy state
                        (
                            [
                                repl_pol_access(1),
                                repl_pol_replace(1),
                                repl_pol_block_index(next_block_replacement),
                            ]
                            if self.NUM_WAYS > 1
                            else []
                        ),
                        If(
                            And(
                                dirty_memory[next_block_replacement][address_index],
                                Or(
                                    Not(fe_read_write_select_i_reg), self.WRITE_ALLOCATE
                                ),
                            )
                            if self.WRITE_BACK
                            else False
                        )(
                            # We need to write back the contents of the block first
                            # needs to be wrapped in if/else because we use stuff that only exists in write_back
                            # even if the above condition would never be true otherwise...
                            [
                                state_reg(States.WRITE_BACK_BLOCK.value),
                                write_back_address_index(address_index),
                                write_back_block_index(next_block_replacement),
                                write_back_tag(
                                    tag_memory[next_block_replacement][address_index]
                                ),
                                If(
                                    Or(
                                        Not(fe_read_write_select_i_reg),
                                        self.BLOCK_SIZE > 1,
                                    )
                                )(write_back_next_state(States.READ_BLOCK.value)).Else(
                                    write_back_next_state(States.READ_BLOCK_DONE.value)
                                ),
                            ]
                            if self.WRITE_BACK
                            else []
                        ).Else(
                            # No write-back needed
                            If(
                                Or(Not(fe_read_write_select_i_reg), self.BLOCK_SIZE > 1)
                            )(
                                # Read the block from the next level memory
                                state_reg(States.READ_BLOCK.value)
                            ).Else(
                                # No need to read from the next level memory
                                state_reg(States.READ_BLOCK_DONE.value)
                            )
                        ),
                    ),
                ),
            )
            .Elif(state_reg == States.WRITE_BACK_BLOCK.value)(
                [
                    latency_counter.inc(),
                    # Stop updating the replacement policy
                    (
                        [repl_pol_access(0), repl_pol_replace(0)]
                        if self.NUM_WAYS > 1
                        else []
                    ),
                    # prepare memory request
                    (
                        [
                            be_address_o_reg[: self.WORD_OFFSET_W](
                                write_back_word_offset
                            ),
                            write_back_word_offset.inc(),  # increment block offset
                        ]
                        if self.BLOCK_SIZE > 1
                        else []
                    ),
                    (
                        be_address_o_reg[
                            self.WORD_OFFSET_W : self.INDEX_WIDTH + self.WORD_OFFSET_W
                        ](write_back_address_index)
                        if self.NUM_SETS > 1
                        else []
                    ),
                    be_address_o_reg[self.INDEX_WIDTH + self.WORD_OFFSET_W :](
                        write_back_tag
                    ),
                    be_read_write_select_o_reg(1),
                    be_write_data_o_reg(
                        data_memory[write_back_block_index][address_index][
                            write_back_word_offset
                        ]
                    ),
                    be_write_data_valid_o_reg(1),
                    # state changes
                    state_reg(States.SEND_MEM_REQUEST.value),
                    If(write_back_word_offset == self.BLOCK_SIZE - 1)(
                        # This is the last word
                        send_mem_request_next_state(write_back_next_state),
                    )(
                        # We're not done yet, come back after mem request has finished
                        send_mem_request_next_state(States.WRITE_BACK_BLOCK.value)
                    ),
                ]
                if self.WRITE_BACK
                else []
            )
            .Elif(state_reg == States.SEND_MEM_REQUEST.value)(
                latency_counter.inc(),
                If(be_port_ready_i)(
                    be_address_valid_o_reg(1),
                    state_reg(States.SEND_MEM_REQUEST_WAIT.value),
                ),
            )
            .Elif(state_reg == States.SEND_MEM_REQUEST_WAIT.value)(
                latency_counter.inc(),
                be_address_valid_o_reg(0),
                # We need to wait at least one cycle here so the backend can accept the request
                If(And(Not(be_address_valid_o_reg), be_port_ready_i))(
                    state_reg(send_mem_request_next_state),
                    If(Not(be_read_write_select_o_reg))(
                        # if we just read something, write it to the cache
                        data_memory[next_block_replacement][address_index][
                            # figure out the correct block offset
                            (
                                be_address_o_reg[: self.WORD_OFFSET_W]
                                if self.BLOCK_SIZE > 1
                                else 0
                            )
                        ](be_read_data_i)
                    ),
                ),
            )
            .Elif(state_reg == States.READ_BLOCK.value)(
                latency_counter.inc(),
                # Stop updating the replacement policy
                [repl_pol_access(0), repl_pol_replace(0)] if self.NUM_WAYS > 1 else [],
                be_address_o_reg(fe_address_i_reg),
                # prepare memory request
                (
                    [
                        be_address_o_reg[: self.WORD_OFFSET_W](read_block_word_offset),
                        read_block_word_offset.inc(),  # increment block offset
                    ]
                    if self.BLOCK_SIZE > 1
                    else []
                ),
                be_address_o_reg[self.WORD_OFFSET_W :](
                    fe_address_i_reg[self.WORD_OFFSET_W :]
                ),
                be_read_write_select_o_reg(0),
                If(read_block_word_offset == self.BLOCK_SIZE - 1)(
                    # We're done, go back
                    send_mem_request_next_state(States.READ_BLOCK_DONE.value)
                ).Else(
                    # Come back, we're not done
                    send_mem_request_next_state(States.READ_BLOCK.value)
                ),
                # Send the memory request except for when its the address to which
                # we want to write anyway
                If(
                    Not(
                        And(
                            fe_read_write_select_i_reg,
                            address_word_offset == read_block_word_offset,
                        )
                    )
                )(state_reg(States.SEND_MEM_REQUEST.value)).Elif(
                    read_block_word_offset + 1 == 0
                )(
                    # If we write to the last word in the block, we have to manually jump
                    # to the next state because the send_mem state won't do it for us
                    state_reg(States.READ_BLOCK_DONE.value)
                ),
            )
            .Elif(state_reg == States.READ_BLOCK_DONE.value)(
                latency_counter.inc(),
                # Stop updating the replacement policy
                [repl_pol_access(0), repl_pol_replace(0)] if self.NUM_WAYS > 1 else [],
                If(fe_read_write_select_i_reg)(
                    # fe write request, write to the cache
                    data_memory[next_block_replacement][address_index][
                        address_word_offset
                    ](fe_write_data_i_reg),
                    # stall if write-back, else write to next level memory
                    (
                        [
                            state_reg(States.STALL.value),
                        ]
                        if self.WRITE_BACK
                        else [
                            be_address_o_reg(fe_address_i_reg),
                            be_write_data_o_reg(fe_write_data_i_reg),
                            be_read_write_select_o_reg(1),
                            be_write_data_valid_o_reg(1),
                            send_mem_request_next_state(States.STALL.value),
                            state_reg(States.SEND_MEM_REQUEST.value),
                        ]
                    ),
                ).Else(
                    # fe read request, hand the data out
                    fe_read_data_o_reg(
                        data_memory[next_block_replacement][address_index][
                            address_word_offset
                        ]
                    ),
                    state_reg(States.STALL.value),
                ),
            )
            .Elif(state_reg == States.STALL.value)(
                # Stall for the remaining time (or error if this took too much time...?)
                latency_counter.inc(),
                # Stop updating the replacement policy
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
                    hit_valid(0),
                    latency_counter(0),
                    If(flush_i_reg)(state_reg(States.FLUSH_COMPUTE_NEXT.value)).Else(
                        state_reg(States.READY.value)
                    ),
                ),
            )
            .Else(
                If(state_reg == States.FLUSH_COMPUTE_NEXT.value)(
                    If(flush_encoder_input == 0)(
                        # No more dirty sets in this block, return or go to next block
                        If(
                            flush_current_block_index == self.NUM_WAYS - 1,
                        )(
                            flush_current_block_index(0),
                            state_reg(States.READY.value),
                            flush_i_reg(0),
                            latency_counter(
                                0
                            ),  # latency counter was incremented all the time by write back state, reset it
                        ).Else(flush_current_block_index.inc())
                    ).Else(
                        # There is a dirty set that we need to write back
                        state_reg(States.FLUSH_PREPARE_WRITE_BACK.value),
                    ),
                ).Elif(state_reg == States.FLUSH_PREPARE_WRITE_BACK.value)(
                    write_back_address_index(flush_next_set_index),
                    write_back_tag(
                        tag_memory[flush_current_block_index][flush_next_set_index]
                    ),
                    write_back_block_index(flush_current_block_index),
                    write_back_next_state(States.FLUSH_COMPUTE_NEXT.value),
                    state_reg(States.WRITE_BACK_BLOCK.value),
                    # clear dirty bit
                    dirty_memory[flush_current_block_index][flush_next_set_index](0),
                )
                if self.WRITE_BACK
                else []
            ),
            If(
                AndList(
                    state_reg != States.READY.value,
                    state_reg != States.FLUSH_COMPUTE_NEXT.value,
                    state_reg != States.FLUSH_PREPARE_WRITE_BACK.value,
                )
            )(flush_i_reg(Or(flush_i_reg, flush_i))),
        )
        return m
