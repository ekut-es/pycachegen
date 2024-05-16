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

from acaverilog.generators.one_hot_to_bin_generator import OneHotToBinGenerator
from acaverilog.generators.replacement_policy_generator import (
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
        self, data_width: int, address_width: int, num_ways: int, num_sets: int, replacement_policy: str
    ) -> None:
        """Cache Generator.

        Args:
            data_width (int): Width of one data word in bits.
            address_width (int): Width of the addresses in bits.
            num_ways (int): Number of ways. Must be a power of 2.
            num_sets (int): Number of sets. Must be a power of 2 and (for now) at least 2.
            replacement_policy (str): Either "fifo" or "plru_tree"
        """
        self.DATA_WIDTH = data_width
        self.ADDRESS_WIDTH = address_width
        self.NUM_WAYS = num_ways
        self.NUM_SETS = num_sets
        self.REPLACEMENT_POLICY = replacement_policy
        # non configurable atm, because everything will be pulled from the acadl object anyway
        self.HIT_LATENCY = 8
        self.MISS_LATENCY = 10
        # derived
        self.NUM_WAYS_W = int(log2(self.NUM_WAYS))

        # Internal Constants
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
        valid_memory = m.Reg(f"valid_memory", 1, dims=(self.NUM_WAYS, self.NUM_SETS))
        data_memory = m.Reg(
            f"data_memory", self.DATA_WIDTH, dims=(self.NUM_WAYS, self.NUM_SETS)
        )
        m.Assign(fe_port_ready_o(state_reg == States.READY.value))
        m.Assign(address_tag(fe_address_i_reg[self.INDEX_WIDTH :]))
        m.Assign(address_index(fe_address_i_reg[: self.INDEX_WIDTH]))
        m.Assign(fe_hit_o(hit_vector != 0))

        # Replacement policy
        if self.NUM_WAYS > 1:
            hit_index = m.Reg("hit_index", self.NUM_WAYS_W)
            update_repl_pol = m.Reg("update_repl_pol_o")
            repl_pol_way = m.Reg("repl_pol_way_o", max(1, self.NUM_WAYS_W))
            next_to_replace = m.Reg(
                "next_to_replace", max(1, self.NUM_WAYS_W), dims=self.NUM_SETS
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
                    ("access_valid_i", update_repl_pol),
                    ("way_i", repl_pol_way),
                    ("index_i", address_index),
                    ("next_replacement_o", next_to_replace),
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
                )
            )
        )

        m.Always(Posedge(clk_i))(
            If(state_reg == States.HIT_LOOKUP.value)(
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
        )

        m.Always(Posedge(clk_i))(
            If(state_reg == States.HIT_LOOKUP_DONE.value)(
                # Hit lookup has finished
                latency_counter.inc(),
                If(fe_hit_o == 1)(
                    # We have a hit
                    # Update the PLRU Bits
                    (
                        [
                            repl_pol_way(hit_index),
                            update_repl_pol(1),
                        ]
                        if self.NUM_WAYS > 1
                        else []
                    ),
                    If(fe_read_write_select_i_reg == 0)(
                        # handle read
                        [
                            If(hit_vector[i] == 1)(
                                fe_read_data_o_reg(data_memory[i][address_index])
                            )
                            for i in range(self.NUM_WAYS)
                        ],
                        state_reg(States.STALL.value),
                    ).Elif(fe_read_write_select_i_reg == 1)(
                        # handle write
                        [
                            If(hit_vector[i] == 1)(
                                data_memory[i][address_index](fe_write_data_i_reg)
                            )
                            for i in range(self.NUM_WAYS)
                        ]
                    ),
                ),
                If(OrList(fe_hit_o == 0, fe_read_write_select_i_reg == 1))(
                    # We have a miss or we need to write
                    # Request read/write from lower memory
                    be_address_o_reg(fe_address_i_reg),
                    be_address_valid_o_reg(1),
                    be_read_write_select_o_reg(fe_read_write_select_i_reg),
                    be_write_data_o_reg(fe_write_data_i_reg),
                    be_write_data_valid_o_reg(fe_read_write_select_i_reg),
                    If(be_port_ready_i == 1)(
                        state_reg(States.REQUEST_TO_LOWER_MEM_SENT.value)
                    ),
                ),
            )
        )

        m.Always(Posedge(clk_i))(
            If(state_reg == States.REQUEST_TO_LOWER_MEM_SENT.value)(
                # Stall one cycle so the lower memory can accept the request and switch to port not ready
                state_reg(States.WAIT_FOR_LOWER_MEM.value)
            )
        )

        m.Always(Posedge(clk_i))(
            If(state_reg == States.WAIT_FOR_LOWER_MEM.value)(
                # Waiting for the lower memory to fulfill the request
                If(
                    OrList(
                        AndList(be_read_data_valid_i, Not(fe_read_write_select_i_reg)),
                        AndList(be_write_done_i, fe_read_write_select_i_reg),
                    )
                )(
                    # Request to main memory was processed, we can now
                    # a) hand the data out and write it to the cache in case of a read
                    # b) do nothing in case of a write
                    latency_counter.inc(),
                    state_reg(States.STALL.value),
                    If(fe_read_write_select_i_reg == 0)(
                        fe_read_data_o_reg(be_read_data_i),
                        data_memory[
                            next_to_replace[address_index] if self.NUM_WAYS > 1 else 0
                        ][address_index](be_read_data_i),
                        valid_memory[
                            next_to_replace[address_index] if self.NUM_WAYS > 1 else 0
                        ][address_index](1),
                        tag_memory[
                            next_to_replace[address_index] if self.NUM_WAYS > 1 else 0
                        ][address_index](address_tag),
                        (
                            [  # Update the PLRU Bits
                                repl_pol_way(next_to_replace[address_index]),
                                update_repl_pol(1),
                            ]
                            if self.NUM_WAYS > 1
                            else []
                        ),
                    ),
                ).Else(
                    # Invalidate the address so as to not send another request
                    be_address_valid_o_reg(0)
                )
            )
        )

        m.Always(Posedge(clk_i))(
            If(state_reg == States.STALL.value)(
                # Stall for the remaining time (or error if this took too much time...?)
                latency_counter.inc(),
                update_repl_pol(0) if self.NUM_WAYS > 1 else [],
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
                ),
            )
        )
        return m
