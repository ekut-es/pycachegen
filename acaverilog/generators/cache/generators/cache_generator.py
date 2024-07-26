from math import ceil, log2
from enum import Enum
from veriloggen import (
    Module,
    Submodule,
    Posedge,
    Negedge,
    If,
    AndList,
    OrList,
    Not,
    Or,
    And,
    Cond,
    Case,
    When,
)

from acaverilog.generators.cache.generators.one_hot_to_bin_generator import (
    OneHotToBinGenerator,
)
from acaverilog.generators.cache.generators.replacement_policy_generator import (
    ReplacementPolicyGenerator,
)
from acaverilog.generators.cache.cache_config_validation import (
    ConfigurationError,
    InternalCacheConfig,
)


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
    FLUSH_CACHE = 9
    FLUSH_BACKEND = 10


class CacheGenerator:
    def __init__(
        self,
        config: InternalCacheConfig,
    ) -> None:
        """Cache Generator.

        Args:
            config (CacheConfig): Cache configuration.
        """
        self.DATA_WIDTH = config.DATA_WIDTH
        self.ADDRESS_WIDTH = config.ADDRESS_WIDTH
        self.NUM_WAYS = config.NUM_WAYS
        self.NUM_SETS = config.NUM_SETS
        self.REPLACEMENT_POLICY = config.REPLACEMENT_POLICY
        self.HIT_LATENCY = config.HIT_LATENCY
        self.MISS_LATENCY = config.MISS_LATENCY
        self.WRITE_BACK = config.WRITE_BACK
        self.WRITE_ALLOCATE = config.WRITE_ALLOCATE
        self.BLOCK_SIZE = config.BLOCK_SIZE
        self.BE_DATA_WIDTH = config.BE_DATA_WIDTH
        self.BE_ADDRESS_WIDTH = config.BE_ADDRESS_WIDTH
        self.BYTE_SIZE = config.BYTE_SIZE
        self.PREFIX = config.PREFIX
        self.ENABLE_RESET = config.ENABLE_RESET

        # Internal Constants
        self.NUM_WAYS_W = int(log2(self.NUM_WAYS))
        self.INDEX_WIDTH = int(log2(self.NUM_SETS))
        self.WORD_OFFSET_W = int(log2(self.BLOCK_SIZE))
        self.TAG_WIDTH = self.ADDRESS_WIDTH - self.INDEX_WIDTH - self.WORD_OFFSET_W
        self.LATENCY_COUNTER_SIZE = ceil(
            log2(max(2, self.HIT_LATENCY, self.MISS_LATENCY))
        )
        self.STATE_REG_WIDTH = ceil(log2(len(States)))
        self.BYTE_OFFSET_W = int(log2(self.DATA_WIDTH // self.BYTE_SIZE))
        self.BE_BYTE_OFFSET_W = int(log2(self.BE_DATA_WIDTH // self.BYTE_SIZE))
        self.BYTES_PER_WORD = self.DATA_WIDTH // self.BYTE_SIZE
        self.BE_BYTES_PER_WORD = self.BE_DATA_WIDTH // self.BYTE_SIZE
        self.BE_BYTE_MULTIPLIER = self.BE_BYTES_PER_WORD // self.BYTES_PER_WORD
        self.READ_BLOCK_REQUESTS_NEEDED = ceil(
            self.BYTES_PER_WORD * self.BLOCK_SIZE / self.BE_BYTES_PER_WORD
        )
        self.READ_BLOCK_WC = min(
            self.BE_BYTE_MULTIPLIER, self.BLOCK_SIZE
        )  # the words read from the BE cache can be bigger than our own words so
        # we might be able to extract multiple words from that single word. This
        # variable specifies how many times we can do that per BE word.
        self.validate_latencies()
        min_latencies = self.get_min_worst_case_latencies()
        own_latencies = (self.HIT_LATENCY, self.MISS_LATENCY)
        if min_latencies == own_latencies:
            print(
                f"{self.PREFIX}: using the minimum latencies {min_latencies} (hit/miss)"
            )
        else:
            print(
                f"{self.PREFIX}: latencies {own_latencies} differ from the minimum latencies {min_latencies} (hit/miss)"
            )

    def get_min_worst_case_latencies(self) -> tuple[int, int]:
        """Compute the minimum hit and miss latency for the current configuration
        that occur in the worst case possible. Note that this worst case also
        considers write strobe input signals which are not all ones which can only
        happen in multi layer cache scenarios if the processor doesn't do any byte
        operations.

        Returns:
            tuple[int, int]: hit latency, miss latency.
        """
        min_miss = 0
        min_hit = 0

        # miss latencies
        if self.WRITE_ALLOCATE and self.WRITE_BACK:
            min_miss = max(min_miss, 5)  # write miss
        if self.WRITE_ALLOCATE and not self.WRITE_BACK:
            min_miss = max(min_miss, 7)  # write miss
        if True:
            min_miss = max(
                min_miss, 5 + self.READ_BLOCK_REQUESTS_NEEDED * (2 + self.READ_BLOCK_WC)
            )  # read miss
        if self.WRITE_ALLOCATE and self.WRITE_BACK:
            min_miss = max(
                min_miss, 5 + self.READ_BLOCK_REQUESTS_NEEDED * (2 + self.READ_BLOCK_WC)
            )  # write miss
        if self.WRITE_ALLOCATE and not self.WRITE_BACK:
            min_miss = max(
                min_miss, 7 + self.READ_BLOCK_REQUESTS_NEEDED * (2 + self.READ_BLOCK_WC)
            )  # write miss
        if self.WRITE_BACK and self.BLOCK_SIZE == 1 and self.WRITE_ALLOCATE:
            min_miss = max(min_miss, 5 + 3 * self.BLOCK_SIZE)  # write miss + dirty
        if self.WRITE_BACK:
            min_miss = max(
                min_miss,
                5
                + 3 * self.BLOCK_SIZE
                + self.READ_BLOCK_REQUESTS_NEEDED * (2 + self.READ_BLOCK_WC),
            )  # read miss + dirty
        if self.WRITE_ALLOCATE and self.WRITE_BACK:
            min_miss = max(
                min_miss,
                5
                + 3 * self.BLOCK_SIZE
                + self.READ_BLOCK_REQUESTS_NEEDED * (2 + self.READ_BLOCK_WC),
            )  # write miss + dirty
        if not self.WRITE_ALLOCATE:
            min_miss = max(min_miss, 6)

        # hit latencies
        if True:
            min_hit = max(min_hit, 4)  # read hit
        if not self.WRITE_BACK:
            min_hit = max(min_hit, 6)  # write hit
        if self.WRITE_BACK:
            min_hit = max(min_hit, 4)  # write hit

        return min_hit, min_miss

    def validate_latencies(self) -> None:
        """Validates that the configured latencies are achievable for
        the current configuration. A latency of 0 is also accepted and
        will cause the cache to not stall artificially.

        Raises:
            ConfigurationError: Raises an error if the latencies are set too low.
        """
        min_latencies = self.get_min_worst_case_latencies()
        config_valid = (
            min_latencies[0] <= self.HIT_LATENCY or self.HIT_LATENCY == 0
        ) and (min_latencies[1] <= self.MISS_LATENCY or self.MISS_LATENCY == 0)

        if not config_valid:
            raise ConfigurationError(
                "The configured latencies are too low. "
                + "The minimum worst case latencies for this configuration are "
                f"{min_latencies[0]} (hit) and {min_latencies[1]} (miss)."
            )

    def generate_module(self) -> Module:
        m = Module(f"{self.PREFIX}cache")

        # Front End Inputs
        clk_i = m.Input("clk_i")
        reset_n_i = m.Input("reset_n_i")
        fe_flush_i = m.Input("fe_flush_i")
        fe_address_i = m.Input("fe_address_i", self.ADDRESS_WIDTH)
        fe_address_valid_i = m.Input("fe_address_valid_i")
        fe_write_data_i = m.Input("fe_write_data_i", self.DATA_WIDTH)
        fe_write_data_valid_i = m.Input("fe_write_data_valid_i")
        fe_read_write_select_i = m.Input("fe_read_write_select_i")
        fe_write_strobe_i = m.Input("fe_write_strobe_i", self.BYTES_PER_WORD)

        # Front End Outputs
        fe_read_data_o = m.Output("fe_read_data_o", self.DATA_WIDTH)
        fe_read_data_valid_o = m.Output("fe_read_data_valid_o")
        fe_write_done_o = m.Output("fe_write_done_o")
        fe_port_ready_o = m.Output("fe_port_ready_o")
        fe_hit_o = m.Output("fe_hit_o")
        fe_flush_done_o = m.Output("fe_flush_done_o")

        # Back End Inputs
        be_read_data_i = m.Input("be_read_data_i", self.BE_DATA_WIDTH)
        be_read_data_valid_i = m.Input("be_read_data_valid_i")
        be_write_done_i = m.Input("be_write_done_i")
        be_port_ready_i = m.Input("be_port_ready_i")
        be_flush_done_i = m.Input("be_flush_done_i")

        # Back End Outputs
        be_address_o = m.Output("be_address_o", self.BE_ADDRESS_WIDTH)
        be_address_valid_o = m.Output("be_address_valid_o")
        be_write_data_o = m.Output("be_write_data_o", self.BE_DATA_WIDTH)
        be_write_data_valid_o = m.Output("be_write_data_valid_o")
        be_read_write_select_o = m.Output("be_read_write_select_o")
        be_write_strobe_o = m.Output("be_write_strobe_o", self.BE_BYTES_PER_WORD)
        be_flush_o = m.Output("be_flush_o")

        # Front End Input Buffers
        fe_flush_i_reg = m.Reg("fe_flush_i_reg")
        fe_address_i_reg = m.Reg("fe_address_i_reg", self.ADDRESS_WIDTH)
        fe_write_data_i_reg = m.Reg("fe_write_data_i_reg", self.DATA_WIDTH)
        fe_read_write_select_i_reg = m.Reg("fe_read_write_select_i_reg")
        fe_write_strobe_i_reg = m.Reg("fe_write_strobe_i_reg", self.BYTES_PER_WORD)

        # Front End Output Buffers
        fe_read_data_o_reg = m.Reg(
            "fe_read_data_o_reg", self.BYTE_SIZE, self.BYTES_PER_WORD
        )
        fe_read_data_valid_o_reg = m.Reg("fe_read_data_valid_o_reg")
        fe_write_done_o_reg = m.Reg("fe_write_done_o_reg")
        fe_flush_done_o_reg = m.Reg("fe_flush_done_o_reg")

        # Back End Output Buffers
        be_address_o_reg = m.Reg(
            "be_address_o_reg", self.ADDRESS_WIDTH
        )  # This has the caches own width and we then just cut something off later, much easier
        be_address_valid_o_reg = m.Reg("be_address_valid_o_reg")
        be_write_data_o_reg = m.Reg(
            "be_write_data_o_reg", self.BYTE_SIZE, self.BYTES_PER_WORD
        )
        be_write_data_valid_o_reg = m.Reg("be_write_data_valid_o_reg")
        be_read_write_select_o_reg = m.Reg("be_read_write_select_o_reg")
        be_write_strobe_o_reg = m.Reg("be_write_strobe_o_reg", self.BYTES_PER_WORD)
        be_flush_o_reg = m.Reg("be_flush_o_reg")

        # Frontend Output Buffer Assignments
        for i in range(self.BYTES_PER_WORD):
            m.Assign(
                fe_read_data_o[self.BYTE_SIZE * i : self.BYTE_SIZE * (i + 1)](
                    fe_read_data_o_reg[i]
                )
            )
        m.Assign(fe_read_data_valid_o(fe_read_data_valid_o_reg))
        m.Assign(fe_write_done_o(fe_write_done_o_reg))
        m.Assign(fe_flush_done_o(fe_flush_done_o_reg))

        # Backend Output Buffer Assignments
        m.Assign(be_write_data_valid_o(be_write_data_valid_o_reg))
        m.Assign(be_read_write_select_o(be_read_write_select_o_reg))
        # The output address register has our own address length, so we need to cut it down
        m.Assign(be_address_o(be_address_o_reg[-self.BE_ADDRESS_WIDTH :]))
        m.Assign(be_address_valid_o(be_address_valid_o_reg))
        m.Assign(be_flush_o(be_flush_o_reg))
        # The output data also has our own data width, so we need to
        # shift the output data and the write strobe signal
        for i in range(self.BE_BYTES_PER_WORD):
            if self.ADDRESS_WIDTH == self.BE_ADDRESS_WIDTH:
                m.Assign(
                    be_write_data_o[self.BYTE_SIZE * i : self.BYTE_SIZE * (i + 1)](
                        be_write_data_o_reg[i]
                    )
                )
                m.Assign(be_write_strobe_o[i](be_write_strobe_o_reg[i]))
            else:
                m.Assign(
                    be_write_data_o[self.BYTE_SIZE * i : self.BYTE_SIZE * (i + 1)](
                        Cond(
                            (i >> int(log2(self.BYTES_PER_WORD)))
                            == be_address_o_reg[: -self.BE_ADDRESS_WIDTH],
                            be_write_data_o_reg[i % self.BYTES_PER_WORD],
                            0,
                        )
                    )
                )
                m.Assign(
                    be_write_strobe_o[i](
                        Cond(
                            (i >> int(log2(self.BYTES_PER_WORD)))
                            == be_address_o_reg[: -self.BE_ADDRESS_WIDTH],
                            be_write_strobe_o_reg[i % self.BYTES_PER_WORD],
                            0,
                        )
                    )
                )

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

        # Wires with assignments for basic cache signals
        address_word_offset = m.Wire("address_word_offset", max(1, self.WORD_OFFSET_W))
        if self.BLOCK_SIZE == 1:
            m.Assign(address_word_offset(0))
        else:
            m.Assign(address_word_offset(fe_address_i_reg[: self.WORD_OFFSET_W]))

        address_index = m.Wire("address_index", max(1, self.INDEX_WIDTH))
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

        address_tag = m.Wire("address_tag", self.TAG_WIDTH)
        m.Assign(address_tag(fe_address_i_reg[self.WORD_OFFSET_W + self.INDEX_WIDTH :]))

        # The BE might return read data that is wider than our own data.
        # Therefore we should slice the be read data accordingly (based on the address we requested)
        resized_be_read_data = m.Reg("resized_be_read_data", self.DATA_WIDTH)
        if self.ADDRESS_WIDTH == self.BE_ADDRESS_WIDTH:
            m.Always(be_read_data_i)(resized_be_read_data(be_read_data_i, blk=True))
        else:
            if self.READ_BLOCK_WC > 1:
                be_read_data_word_offset = m.Reg(
                    "be_read_data_word_offset", max(1, self.WORD_OFFSET_W)
                )
            else:
                be_read_data_word_offset = m.Wire(
                    "be_read_data_word_offset", max(1, self.WORD_OFFSET_W)
                )
                m.Assign(be_read_data_word_offset(0))

            # this variable specifies the index of the word (our word width) inside the
            # BE read data. It depends on the address we set and the be_read_data_word_offset,
            # which will get incremented when reading a block into this cache (we do this because
            # we only want to send one memory request and get as many of our word from that read data
            # as possible). So what I'd like to do is actually just use
            # be_address_o_reg[: -self.BE_ADDRESS_WIDTH]+be_read_data_word_offset
            # But I cant do that because these two things might have different widths and verilator does
            # not like that but Veriloggen does not seem to offer any padding functionality...
            be_read_data_total_word_offset = m.Wire(
                "be_read_data_total_word_offset",
                self.ADDRESS_WIDTH - self.BE_ADDRESS_WIDTH,
            )
            if self.BLOCK_SIZE == 1:
                m.Assign(
                    be_read_data_total_word_offset(
                        be_address_o_reg[: -self.BE_ADDRESS_WIDTH]
                    )
                )
            elif self.ADDRESS_WIDTH - self.BE_ADDRESS_WIDTH == self.WORD_OFFSET_W:
                m.Assign(be_read_data_total_word_offset(be_read_data_word_offset))
            elif self.ADDRESS_WIDTH - self.BE_ADDRESS_WIDTH > self.WORD_OFFSET_W:
                m.Assign(
                    be_read_data_total_word_offset[: self.WORD_OFFSET_W](
                        be_read_data_word_offset
                    )
                )
                m.Assign(
                    be_read_data_total_word_offset[self.WORD_OFFSET_W :](
                        be_address_o_reg[self.WORD_OFFSET_W : -self.BE_ADDRESS_WIDTH]
                    )
                )
            else:
                m.Assign(
                    be_read_data_total_word_offset(
                        be_read_data_word_offset[
                            : self.ADDRESS_WIDTH - self.BE_ADDRESS_WIDTH
                        ]
                    )
                )

            m.Always(be_read_data_i, be_address_o_reg, be_read_data_total_word_offset)(
                # iterate over the be read data in steps of our own data width and check if
                # when it is the word that we want to read
                Case(be_read_data_total_word_offset)(
                    *[
                        When(i)(
                            resized_be_read_data(
                                be_read_data_i[
                                    self.DATA_WIDTH * i : self.DATA_WIDTH * (i + 1)
                                ],
                                blk=True,
                            )
                        )
                        for i in range(self.BE_BYTE_MULTIPLIER)
                    ]
                )
            )

        # Memories
        tag_memory = []
        valid_memory = []
        data_memory = []
        for way in range(self.NUM_WAYS):
            tag_memory.append(
                m.Reg(f"tag_memory_way_{way}", self.TAG_WIDTH, dims=(self.NUM_SETS))
            )
            valid_memory.append(
                m.Reg(f"valid_memory_way_{way}", 1, dims=(self.NUM_SETS))
            )
            data_memory.append([])
            for byte in range(self.BYTES_PER_WORD):
                data_memory[-1].append(
                    m.Reg(
                        f"data_memory_way_{way}_byte_{byte}",
                        self.BYTE_SIZE,
                        dims=(self.NUM_SETS * self.BLOCK_SIZE),
                    )
                )

        # Things that are only needed for write back
        if self.WRITE_BACK:
            dirty_memory = []
            for way in range(self.NUM_WAYS):
                dirty_memory.append(
                    m.Reg(
                        f"dirty_memory_way_{way}",
                        1,
                        dims=(self.NUM_SETS),
                    )
                )
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
            flush_set_index = m.Reg("flush_set_index", max(1, self.INDEX_WIDTH))
            flush_block_index = m.Reg("flush_block_index", max(1, self.NUM_WAYS_W))

        # The data memory cannot have more than two dimensions, so we need to do the addessing
        # manually. Here are all the wires to hold the addresses that we may want to access, which
        # are just concatenations of other signals. But we need these assignments because
        # Veriloggen does not seem to have a concatenation operator...
        dmem_msb_addr_fe = m.Wire(
            "dmem_msb_addr_fe", max(1, self.INDEX_WIDTH + self.WORD_OFFSET_W)
        )
        dmem_msb_addr_be = m.Wire(
            "dmem_msb_addr_be", max(1, self.INDEX_WIDTH + self.WORD_OFFSET_W)
        )
        if self.BLOCK_SIZE > 1:
            m.Assign(dmem_msb_addr_fe[: self.WORD_OFFSET_W](address_word_offset))
            m.Assign(dmem_msb_addr_be[: self.WORD_OFFSET_W](
                    # figure out the correct block offset
                    be_address_o_reg[: self.WORD_OFFSET_W]
                    + (
                        0
                        if self.ADDRESS_WIDTH == self.BE_ADDRESS_WIDTH
                        else be_read_data_word_offset
                    )
                )
            )
        if self.NUM_SETS > 1:
            m.Assign(dmem_msb_addr_fe[self.WORD_OFFSET_W :](address_index))
            m.Assign(dmem_msb_addr_be[self.WORD_OFFSET_W :](address_index))
        if self.BLOCK_SIZE == 1 and self.NUM_SETS == 1:
            m.Assign(dmem_msb_addr_fe(0))
            m.Assign(dmem_msb_addr_be(0))
        if self.WRITE_BACK:
            dmem_msb_addr_wb = m.Wire(
                "dmem_msb_addr_wb", max(1, self.INDEX_WIDTH + self.WORD_OFFSET_W)
            )
            if self.BLOCK_SIZE > 1:
                m.Assign(dmem_msb_addr_wb[: self.WORD_OFFSET_W](write_back_word_offset))
            if self.NUM_SETS > 1:
                m.Assign(dmem_msb_addr_wb[self.WORD_OFFSET_W :](write_back_address_index))
            if self.BLOCK_SIZE == 1 and self.NUM_SETS == 1:
                m.Assign(dmem_msb_addr_wb(0))

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
                    enable_reset=self.ENABLE_RESET,
                ).generate_module(),
                f"{self.PREFIX}replacement_policy",
                arg_ports=(
                    ("clk_i", clk_i),
                    ("reset_n_i", reset_n_i),
                    ("access_i", repl_pol_access),
                    ("replace_i", repl_pol_replace),
                    ("block_index_i", repl_pol_block_index),
                    ("set_index_i", address_index),
                    *[
                        (f"next_replacement_{i}_o", next_replacements[i])
                        for i in range(self.NUM_SETS)
                    ],
                ),
            )

        m.Always(Posedge(clk_i))(
            If(Not(reset_n_i))(
                [
                    ## reset
                    # frontend input buffers
                    fe_flush_i_reg(0),
                    fe_address_i_reg(0),
                    fe_write_data_i_reg(0),
                    fe_read_write_select_i_reg(0),
                    fe_write_strobe_i_reg(0),
                    # frontend output buffers
                    [fe_read_data_o_reg[i](0) for i in range(self.BYTES_PER_WORD)],
                    fe_read_data_valid_o_reg(0),
                    fe_write_done_o_reg(0),
                    fe_flush_done_o_reg(0),
                    # backend outputs
                    be_address_o_reg(0),
                    be_address_valid_o_reg(0),
                    [be_write_data_o_reg[i](0) for i in range(self.BYTES_PER_WORD)],
                    be_write_data_valid_o_reg(0),
                    be_read_write_select_o_reg(0),
                    be_write_strobe_o_reg(0),
                    be_flush_o_reg(0),
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
                                tag_memory[way_idx][set_idx](0),
                                valid_memory[way_idx][set_idx](0),
                                [
                                    [
                                        data_memory[way_idx][byte_idx][
                                            set_idx * word_idx
                                        ](0)
                                        for byte_idx in range(self.BYTES_PER_WORD)
                                    ]
                                    for word_idx in range(self.BLOCK_SIZE)
                                ],
                            ]
                            for set_idx in range(self.NUM_SETS)
                        ]
                        for way_idx in range(self.NUM_WAYS)
                    ],
                    # write back things
                    (
                        [
                            write_back_address_index(0),
                            write_back_block_index(0),
                            write_back_next_state(0),
                            write_back_tag(0),
                            write_back_word_offset(0),
                            flush_block_index(0),
                            [
                                [
                                    dirty_memory[way_idx][set_idx](0)
                                    for set_idx in range(self.NUM_SETS)
                                ]
                                for way_idx in range(self.NUM_WAYS)
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
                    be_read_data_word_offset(0) if self.READ_BLOCK_WC > 1 else [],
                ]
                if self.ENABLE_RESET
                else []
            ).Else(
                If(state_reg == States.READY.value)(
                    # Cache is ready for a new request
                    If(OrList(fe_flush_i, fe_flush_i_reg))(
                        state_reg(States.FLUSH_CACHE.value),
                    ).Elif(
                        OrList(
                            AndList(
                                fe_read_write_select_i == 0, fe_address_valid_i == 1
                            ),
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
                        fe_write_strobe_i_reg(fe_write_strobe_i),
                        # increment latency counter
                        latency_counter.inc(),
                        # reset flush status
                        fe_flush_done_o_reg(0),
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
                            [
                                If(fe_write_strobe_i_reg[byte_idx])(
                                    [
                                        If(hit_index == way)(
                                            data_memory[way][byte_idx][
                                                dmem_msb_addr_fe
                                            ](
                                                fe_write_data_i_reg[
                                                    self.BYTE_SIZE
                                                    * byte_idx : self.BYTE_SIZE
                                                    * (byte_idx + 1)
                                                ]
                                            )
                                        )
                                        for way in range(self.NUM_WAYS)
                                    ]
                                )
                                for byte_idx in range(self.BYTES_PER_WORD)
                            ],
                            (
                                [
                                    [
                                        If(hit_index == way)(
                                            dirty_memory[way][address_index](1),
                                        )
                                        for way in range(self.NUM_WAYS)
                                    ],
                                    state_reg(States.STALL.value),
                                ]
                                if self.WRITE_BACK
                                else [
                                    # in case of write through, we still need to write to the next level memory
                                    be_address_o_reg(fe_address_i_reg),
                                    be_write_data_valid_o_reg(1),
                                    [
                                        be_write_data_o_reg[i](
                                            fe_write_data_i_reg[
                                                self.BYTE_SIZE
                                                * i : self.BYTE_SIZE
                                                * (i + 1)
                                            ]
                                        )
                                        for i in range(self.BYTES_PER_WORD)
                                    ],
                                    be_read_write_select_o_reg(1),
                                    be_write_strobe_o_reg(fe_write_strobe_i_reg),
                                    state_reg(States.SEND_MEM_REQUEST.value),
                                    send_mem_request_next_state(States.STALL.value),
                                ]
                            ),
                        ).Else(
                            # read
                            [
                                [
                                    If(hit_index == way)(
                                        fe_read_data_o_reg[byte_idx](
                                            data_memory[way][byte_idx][dmem_msb_addr_fe]
                                        )
                                    )
                                    for way in range(self.NUM_WAYS)
                                ]
                                for byte_idx in range(self.BYTES_PER_WORD)
                            ],
                            state_reg(States.STALL.value),
                        ),
                    ).Else(
                        # we have a miss
                        If(And(not self.WRITE_ALLOCATE, fe_read_write_select_i_reg))(
                            # write request and write-no-allocate -> only write to memory
                            be_address_o_reg(fe_address_i_reg),
                            [
                                be_write_data_o_reg[i](
                                    fe_write_data_i_reg[
                                        self.BYTE_SIZE * i : self.BYTE_SIZE * (i + 1)
                                    ]
                                )
                                for i in range(self.BYTES_PER_WORD)
                            ],
                            be_write_data_valid_o_reg(1),
                            be_read_write_select_o_reg(1),
                            be_write_strobe_o_reg(fe_write_strobe_i_reg),
                            state_reg(States.SEND_MEM_REQUEST.value),
                            send_mem_request_next_state(States.STALL.value),
                        ).Else(
                            # We have to replace a block
                            # Update valid and dirty bits and the tag
                            [
                                If(next_block_replacement == way)(
                                    valid_memory[way][address_index](1),
                                    tag_memory[way][address_index](address_tag),
                                    # mark dirty if write, else remove dirty bit
                                    (
                                        dirty_memory[way][address_index](
                                            fe_read_write_select_i_reg
                                        )
                                        if self.WRITE_BACK
                                        else []
                                    ),
                                )
                                for way in range(self.NUM_WAYS)
                            ],
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
                                    OrList(
                                        *[
                                            And(
                                                way == next_block_replacement,
                                                dirty_memory[way][address_index],
                                            )
                                            for way in range(self.NUM_WAYS)
                                        ]
                                    ),
                                    Or(
                                        Not(fe_read_write_select_i_reg),
                                        self.WRITE_ALLOCATE,
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
                                    [
                                        If(way == next_block_replacement)(
                                            write_back_tag(
                                                tag_memory[way][address_index]
                                            )
                                        )
                                        for way in range(self.NUM_WAYS)
                                    ],
                                    If(
                                        OrList(
                                            Not(fe_read_write_select_i_reg),
                                            self.BLOCK_SIZE > 1,
                                            fe_write_strobe_i_reg
                                            != 2**self.BYTES_PER_WORD - 1,
                                        )
                                    )(
                                        write_back_next_state(States.READ_BLOCK.value)
                                    ).Else(
                                        write_back_next_state(
                                            States.READ_BLOCK_DONE.value
                                        )
                                    ),
                                ]
                                if self.WRITE_BACK
                                else []
                            ).Else(
                                # No write-back needed
                                If(
                                    OrList(
                                        Not(fe_read_write_select_i_reg),
                                        self.BLOCK_SIZE > 1,
                                        fe_write_strobe_i_reg
                                        != 2**self.BYTES_PER_WORD - 1,
                                    )
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
                                self.WORD_OFFSET_W : self.INDEX_WIDTH
                                + self.WORD_OFFSET_W
                            ](write_back_address_index)
                            if self.NUM_SETS > 1
                            else []
                        ),
                        be_address_o_reg[self.INDEX_WIDTH + self.WORD_OFFSET_W :](
                            write_back_tag
                        ),
                        be_write_strobe_o_reg(2**self.BYTES_PER_WORD - 1),
                        be_read_write_select_o_reg(1),
                        [
                            [
                                If(write_back_block_index == way)(
                                    be_write_data_o_reg[byte_idx](
                                        data_memory[way][byte_idx][dmem_msb_addr_wb]
                                    )
                                )
                                for way in range(self.NUM_WAYS)
                            ]
                            for byte_idx in range(self.BYTES_PER_WORD)
                        ],
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
                    # do nothing (not even increase the latency counter)
                    # while waiting for the next level memory to get ready
                    If(be_port_ready_i)(
                        latency_counter.inc(),
                        be_address_valid_o_reg(1),
                        state_reg(States.SEND_MEM_REQUEST_WAIT.value),
                    ),
                )
                .Elif(state_reg == States.SEND_MEM_REQUEST_WAIT.value)(
                    # invalidate the request. Then do nothing for one cycle
                    be_address_valid_o_reg(0),
                    # After waiting for one cycle, continue as soon as the next level
                    # memory gets ready again (that means that the request was processed)
                    If(
                        And(
                            Not(be_address_valid_o_reg),
                            Or(
                                And(be_read_write_select_o_reg, be_write_done_i),
                                And(
                                    Not(be_read_write_select_o_reg),
                                    be_read_data_valid_i,
                                ),
                            ),
                        )
                    )(
                        latency_counter.inc(),
                        If(be_read_write_select_o_reg)(
                            state_reg(send_mem_request_next_state)
                        ).Else(
                            (
                                # Write all the words we need from the BE read data into the cache and
                                # then go on to the next state
                                state_reg(send_mem_request_next_state)
                                if self.READ_BLOCK_WC == 1
                                else If(
                                    be_read_data_word_offset == self.READ_BLOCK_WC - 1
                                )(
                                    state_reg(send_mem_request_next_state),
                                    be_read_data_word_offset(0),
                                ).Else(
                                    be_read_data_word_offset.inc()
                                )
                            ),
                            # if we just read something, write it to the cache
                            # if we read stuff we always want to write back the whole word since the fe write request will be applied afterwards
                            # so we do not need to worry about any write strobe things
                            [
                                [
                                    If(next_block_replacement == way)(
                                        data_memory[way][byte_idx][dmem_msb_addr_be](
                                            resized_be_read_data[
                                                self.BYTE_SIZE
                                                * byte_idx : self.BYTE_SIZE
                                                * (byte_idx + 1)
                                            ]
                                        )
                                    )
                                    for way in range(self.NUM_WAYS)
                                ]
                                for byte_idx in range(self.BYTES_PER_WORD)
                            ],
                        ),
                    ),
                )
                .Elif(state_reg == States.READ_BLOCK.value)(
                    latency_counter.inc(),
                    # Stop updating the replacement policy
                    (
                        [repl_pol_access(0), repl_pol_replace(0)]
                        if self.NUM_WAYS > 1
                        else []
                    ),
                    # be_address_o_reg(fe_address_i_reg), # This line is unnecessary and not so cool for synthesis?
                    # prepare memory request
                    (
                        [
                            be_address_o_reg[: self.WORD_OFFSET_W](
                                read_block_word_offset
                            ),
                            (
                                read_block_word_offset.add(self.READ_BLOCK_WC)
                                if self.BLOCK_SIZE != self.READ_BLOCK_WC
                                else []
                            ),  # increment block offset
                        ]
                        if self.BLOCK_SIZE > 1
                        else []
                    ),
                    be_address_o_reg[self.WORD_OFFSET_W :](
                        fe_address_i_reg[self.WORD_OFFSET_W :]
                    ),
                    be_read_write_select_o_reg(0),
                    If(read_block_word_offset == self.BLOCK_SIZE - self.READ_BLOCK_WC)(
                        # We're done, go back
                        send_mem_request_next_state(States.READ_BLOCK_DONE.value)
                    ).Else(
                        # Come back, we're not done
                        send_mem_request_next_state(States.READ_BLOCK.value)
                    ),
                    # Send the memory request except for when its the address to which
                    # we want to write anyway AND write strobe is all ones AND we would not
                    # read any other byte from the word the BE would give is in this request (self.READ_BLOCK_WC == 1)
                    If(
                        Not(
                            AndList(
                                fe_read_write_select_i_reg,
                                address_word_offset == read_block_word_offset,
                                fe_write_strobe_i_reg + 1
                                == 0,  # write strobe is all ones so we dont need any byte of that word
                                self.READ_BLOCK_WC == 1,
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
                    (
                        [repl_pol_access(0), repl_pol_replace(0)]
                        if self.NUM_WAYS > 1
                        else []
                    ),
                    If(fe_read_write_select_i_reg)(
                        # fe write request, write to the cache
                        [
                            If(fe_write_strobe_i_reg[i])(
                                [
                                    If(next_block_replacement == way)(
                                        data_memory[way][i][dmem_msb_addr_fe](
                                            fe_write_data_i_reg[
                                                self.BYTE_SIZE
                                                * i : self.BYTE_SIZE
                                                * (i + 1)
                                            ]
                                        )
                                    )
                                    for way in range(self.NUM_WAYS)
                                ]
                            )
                            for i in range(self.BYTES_PER_WORD)
                        ],
                        # stall if write-back, else write to next level memory
                        (
                            [
                                state_reg(States.STALL.value),
                            ]
                            if self.WRITE_BACK
                            else [
                                be_address_o_reg(fe_address_i_reg),
                                [
                                    be_write_data_o_reg[i](
                                        fe_write_data_i_reg[
                                            self.BYTE_SIZE
                                            * i : self.BYTE_SIZE
                                            * (i + 1)
                                        ]
                                    )
                                    for i in range(self.BYTES_PER_WORD)
                                ],
                                be_read_write_select_o_reg(1),
                                be_write_data_valid_o_reg(1),
                                be_write_strobe_o_reg(fe_write_strobe_i_reg),
                                send_mem_request_next_state(States.STALL.value),
                                state_reg(States.SEND_MEM_REQUEST.value),
                            ]
                        ),
                    ).Else(
                        # fe read request, hand the data out
                        [
                            [
                                If(next_block_replacement == way)(
                                    fe_read_data_o_reg[byte_idx](
                                        data_memory[way][byte_idx][dmem_msb_addr_fe]
                                    )
                                )
                                for way in range(self.NUM_WAYS)
                            ]
                            for byte_idx in range(self.BYTES_PER_WORD)
                        ],
                        state_reg(States.STALL.value),
                    ),
                )
                .Elif(state_reg == States.STALL.value)(
                    # Stop updating the replacement policy
                    (
                        [repl_pol_access(0), repl_pol_replace(0)]
                        if self.NUM_WAYS > 1
                        else []
                    ),
                    If(
                        OrList(
                            AndList(
                                Or(
                                    self.HIT_LATENCY == 0,
                                    latency_counter == self.HIT_LATENCY - 1,
                                ),
                                fe_hit_o == 1,
                            ),
                            AndList(
                                Or(
                                    self.MISS_LATENCY == 0,
                                    latency_counter == self.MISS_LATENCY - 1,
                                ),
                                fe_hit_o == 0,
                            ),
                        )
                    )(
                        # We have stalled enough, finish the request
                        fe_read_data_valid_o_reg(Not(fe_read_write_select_i_reg)),
                        fe_write_done_o_reg(fe_read_write_select_i_reg),
                        hit_valid(0),
                        latency_counter(0),
                        If(fe_flush_i_reg)(state_reg(States.FLUSH_CACHE.value)).Else(
                            state_reg(States.READY.value)
                        ),
                    ).Else(
                        # Stall for the remaining time (or error if this took too much time...?)
                        latency_counter.inc(),
                    ),
                )
                .Elif(state_reg == States.FLUSH_CACHE.value)(
                    fe_flush_done_o_reg(0),  # reset flush done status
                    (
                        [
                            flush_set_index.inc(),
                            If(flush_set_index == self.NUM_SETS - 1)(
                                flush_block_index.inc(),
                                If(flush_block_index == self.NUM_WAYS - 1)(
                                    # Done flushing this cache, flush the backend
                                    state_reg(States.FLUSH_BACKEND.value),
                                    be_flush_o_reg(1),
                                ),
                            ),
                            Case(flush_block_index)(
                                *[
                                    When(way)(
                                        If(
                                            And(
                                                dirty_memory[way][flush_set_index],
                                                valid_memory[way][flush_set_index],
                                            )
                                        )(
                                            write_back_tag(
                                                tag_memory[way][flush_set_index]
                                            ),
                                            write_back_address_index(flush_set_index),
                                            dirty_memory[way][flush_set_index](0),
                                            write_back_next_state(
                                                States.FLUSH_CACHE.value
                                            ),
                                            state_reg(States.WRITE_BACK_BLOCK.value),
                                        )
                                    )
                                    for way in range(self.NUM_WAYS)
                                ]
                            ),
                        ]
                        if self.WRITE_BACK
                        else [
                            # flush the backend
                            state_reg(States.FLUSH_BACKEND.value),
                            be_flush_o_reg(1),
                        ]
                    ),
                )
                .Elif(state_reg == States.FLUSH_BACKEND.value)(
                    be_flush_o_reg(0),  # reset flush signal
                    If(And(be_flush_done_i, Not(be_flush_o_reg)))(
                        state_reg(States.READY.value),
                        fe_flush_i_reg(0),
                        latency_counter(
                            0
                        ),  # latency counter was incremented all the time by write back state, reset it
                        fe_flush_done_o_reg(1),
                    ),
                ),
                # Accept flush requests even while the cache is busy
                # but not while the cache is flushing
                If(
                    AndList(
                        state_reg != States.FLUSH_CACHE.value,
                        state_reg != States.FLUSH_BACKEND.value,
                    )
                )(fe_flush_i_reg(Or(fe_flush_i_reg, fe_flush_i))),
            )
        )
        return m
