from math import ceil
from enum import Enum
from amaranth import *
from amaranth.lib import wiring, data
from amaranth.lib.memory import Memory
from amaranth.lib.wiring import In, Out
from amaranth.utils import exact_log2
from pycachegen.cache_config_validation import InternalCacheConfig
from pycachegen.memory_bus import MemoryBusSignature
from pycachegen.cache_address import CacheAddressLayout
from pycachegen.replacement_policy import ReplacementPolicy
from pycachegen.elaborate_utils import one_hot_encode


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
    FLUSH_CACHE_BLOCK = 11


class Cache(wiring.Component):
    def __init__(self, config: InternalCacheConfig) -> None:
        self.config = config
        self.bytes_per_word = config.DATA_WIDTH // config.BYTE_SIZE
        self.be_bytes_per_word = config.BE_DATA_WIDTH // config.BYTE_SIZE
        self.index_width = exact_log2(config.NUM_SETS)
        self.word_offset_width = exact_log2(config.BLOCK_SIZE)
        self.tag_width = (
            config.ADDRESS_WIDTH - self.index_width - self.word_offset_width
        )
        self.fe_signature = MemoryBusSignature(
            address_width=config.ADDRESS_WIDTH,
            data_width=config.DATA_WIDTH,
            bytes_per_word=self.bytes_per_word,
        )
        self.be_signature = MemoryBusSignature(
            address_width=config.BE_ADDRESS_WIDTH,
            data_width=config.BE_DATA_WIDTH,
            bytes_per_word=self.be_bytes_per_word,
        )
        self.address_layout = CacheAddressLayout(
            index_width=self.index_width,
            tag_width=self.tag_width,
            word_offset_width=self.word_offset_width,
        )
        # how many times bigger the be words are compared to ours
        self.be_byte_multiplier = self.be_bytes_per_word // self.bytes_per_word

        # self.read_block_requests_needed = ceil(
        #     self.bytes_per_word * config.BLOCK_SIZE / self.be_bytes_per_word
        # )

        # the words read from the BE cache can be bigger than our own words so
        # we might be able to extract multiple words from that single word. This
        # variable specifies how many times we can do that per BE word.
        self.read_block_wc = min(self.be_byte_multiplier, config.BLOCK_SIZE)
        super().__init__(
            {
                "fe": In(self.fe_signature),
                "hit_o": Out(1),
                "be": Out(self.be_signature),
            }
        )

    # fmt: off
    def elaborate(self, platform) -> Module:
        m = Module()
        ## frontend input buffers
        fe_buffer_address = Signal(self.address_layout
        )
        fe_buffer_write_data = Signal(self.config.DATA_WIDTH)
        fe_buffer_write_strobe = Signal(self.bytes_per_word)

        ## backend output buffers
        # Create be buffers that use our own data/address/write strobe widths
        # Then "shift" the data/write strobe into place in the real be interface
        # according to the bits we cut off from the address
        be_buffer_write_data = Signal(unsigned(self.config.DATA_WIDTH))
        be_buffer_write_strobe = Signal(unsigned(self.bytes_per_word))
        be_buffer_address = Signal(self.address_layout)
        m.d.comb += self.be.address.eq(be_buffer_address.as_value()[-self.config.BE_ADDRESS_WIDTH : ])
        m.d.comb += self.be.write_data.eq(0)
        m.d.comb += self.be.write_strobe.eq(0)
        m.d.comb += self.be.write_data.word_select(be_buffer_address.as_value()[:-self.config.BE_ADDRESS_WIDTH], self.config.DATA_WIDTH).eq(be_buffer_write_data)
        m.d.comb += self.be.write_strobe.word_select(be_buffer_address.as_value()[:-self.config.BE_ADDRESS_WIDTH], self.bytes_per_word).eq(be_buffer_write_strobe)

        ## internal registers
        # FSM state
        state = Signal(States)
        # FSM state that will be taken after the SEND_MEM_REQUEST state
        send_mem_request_next_state = Signal(States)
        # one bit per way to indicate a hit in that way
        hit_vector = Signal(unsigned(self.config.NUM_WAYS))
        # purely for statistics: let the outside know if we had a hit
        m.d.comb += self.hit_o.eq(hit_vector.any())
        # one hot encode the vector into this signal
        hit_index = one_hot_encode(m, hit_vector)
        # a view for convenient access to the tag/index/word offset bits
        fe_address_view = data.View(self.address_layout, self.fe.address)
        # counter for counting which word of the be read data to write to the
        # data_mem next.
        be_read_data_word_counter = Signal(range(self.read_block_wc))
        # the full index for pulling a word out of a be word
        be_read_data_total_word_offset = Signal(self.config.ADDRESS_WIDTH - self.config.BE_ADDRESS_WIDTH)
        if self.config.BLOCK_SIZE == 1:
            # block size == 1 -> the bits we cut off from the be buffer address are the index
            m.d.comb += be_read_data_total_word_offset.eq(be_buffer_address.as_value()[: -self.config.BE_ADDRESS_WIDTH])
        elif self.config.ADDRESS_WIDTH - self.config.BE_ADDRESS_WIDTH <= self.word_offset_width:
            # one block is exactly one be word or needs multiple be words -> the counter is the index
            m.d.comb += be_read_data_total_word_offset.eq(be_read_data_word_counter)
        elif self.config.ADDRESS_WIDTH - self.config.BE_ADDRESS_WIDTH > self.word_offset_width:
            # one be word is as big as two or more of our blocks -> take the bits we cut off + the counter as index
            m.d.comb += be_read_data_total_word_offset.eq(
                Cat(
                    be_read_data_word_counter,
                    be_buffer_address.as_value()[self.word_offset_width : -self.config.BE_ADDRESS_WIDTH]
                    )
                )
        # counter for the READ BLOCK state that indicates how many words have been read so far
        read_block_word_offset = Signal(self.word_offset_width)
        # Index of the data_mem that contains the data requested
        # Used in the STALL state to select the read data from the correct data_mem
        read_data_mem_select = Signal(range(self.config.NUM_WAYS))
        # index of the set to be flushed next
        flush_set_index = Signal(self.index_width)
        # index of the block that is currently being flushed
        flush_block_index = Signal(range(self.config.NUM_WAYS))
        # whether we already told the backend to flush itself
        be_flush_requested = Signal()
        # Output port ready status based on current state
        m.d.comb += self.fe.port_ready.eq(state == States.READY)

        ## replacement policy things
        # block to be replaced next for the set of the current fe_buffer_address
        next_block_replacement = Signal(range(self.config.NUM_WAYS))
        m.submodules.replacement_policy = replacement_policy = ReplacementPolicy(num_ways = self.config.NUM_WAYS, num_sets = self.config.NUM_SETS, policy = self.config.REPLACEMENT_POLICY)

        # Create valid, dirty, tag, data memories - one per way
        # usage: valid_mem[way][index], tag_mem[way][index], data_mem[way][Cat(word_offset, index)]
        # data memory contains values that represent whole blocks (potentially multiple words!)
        valid_mem = Array([Array([Signal() for _ in range(self.config.NUM_SETS)]) for _ in range(self.config.NUM_WAYS)])
        dirty_mem = Array([Array([Signal() for _ in range(self.config.NUM_SETS)]) for _ in range(self.config.NUM_WAYS)])
        tag_mem = Array()
        data_mem = Array()
        for i in range(self.config.NUM_WAYS):
            new_tag_mem = Memory(shape=unsigned(self.tag_width), depth=self.config.NUM_SETS, init=[])
            m.submodules[f"tag_mem_{i}"] = new_tag_mem
            tag_mem.append((new_tag_mem.read_port(), new_tag_mem.write_port()))

            new_data_mem = Memory(
                shape=unsigned(self.config.DATA_WIDTH), depth=self.config.NUM_SETS*self.config.BLOCK_SIZE, init=[]
            )
            m.submodules[f"data_mem_{i}"] = new_data_mem
            data_mem.append(
                (
                    new_data_mem.read_port(),
                    new_data_mem.write_port(granularity=self.config.BYTE_SIZE),
                )
            )
            # disable data_mem.read_port.en by default so that the read data
            # gets preserved even when the address changes
            # thats necessary because the read data might only be needed
            # after several cycles
            m.d.comb += data_mem[-1][0].en.eq(0)

        ## things for write back
        # address and way to identify the block to be written back
        write_back_address = Signal(self.address_layout)
        write_back_way = Signal(range(self.config.NUM_WAYS))
        # state to take after the WRITE_BACK state
        write_back_next_state = Signal(States)


        def send_fe_buffer_request_to_lower_mem(next_state: States):
            """Uses the request stored in the fe buffers to send a request
            to the lower memory. Goes to the SEND_MEM_REQUEST state to do so.
            """
            m.d.sync += be_buffer_address.eq(fe_buffer_address)
            m.d.sync += be_buffer_write_data.eq(fe_buffer_write_data)
            m.d.sync += be_buffer_write_strobe.eq(fe_buffer_write_strobe)
            m.d.sync += state.eq(States.SEND_MEM_REQUEST)
            m.d.sync += send_mem_request_next_state.eq(next_state)

        with m.Switch(state):
            with m.Case(States.READY):
                with m.If(self.fe.flush):
                    m.d.sync += state.eq(States.FLUSH_CACHE)
                    # Reset fe outputs
                    m.d.sync += self.fe.read_data_valid.eq(0)
                with m.Elif(self.fe.request_valid):
                    m.d.sync += state.eq(States.HIT_LOOKUP)
                    # Reset fe outputs
                    m.d.sync += self.fe.read_data_valid.eq(0)
                    # buffer inputs
                    m.d.sync += fe_buffer_address.eq(self.fe.address)
                    m.d.sync += fe_buffer_write_strobe.eq(self.fe.write_strobe)
                    m.d.sync += fe_buffer_write_data.eq(self.fe.write_data)
                    # query tag memories
                    # this needs to happen in m.d.comb so that the address gets set
                    # BEFORE the positive clk edge that triggers any sync statements
                    for i in range(self.config.NUM_WAYS):
                        m.d.comb += tag_mem[i][0].addr.eq(fe_address_view.index)
            with m.Case(States.HIT_LOOKUP):
                m.d.sync += state.eq(States.HIT_LOOKUP_DONE)
                # check whether we have a hit in any way
                for i in range(self.config.NUM_WAYS):
                    m.d.sync += hit_vector[i].eq(
                        (tag_mem[i][0].data == fe_buffer_address.tag)
                        & valid_mem[i][fe_buffer_address.index]
                    )
                # we might need the data from the data/tag mems
                # so read from all of them
                for i in range(self.config.NUM_WAYS):
                    m.d.comb += data_mem[i][0].en.eq(1)
                    m.d.comb += data_mem[i][0].addr.eq(fe_buffer_address)
                    m.d.comb += tag_mem[i][0].addr.eq(fe_buffer_address.index)
                # buffer the next way to be replaced for this set (shall we need to do that)
                m.d.comb += replacement_policy.set_i.eq(fe_buffer_address.index)
                m.d.sync += next_block_replacement.eq(replacement_policy.next_replacement_o)
            with m.Case(States.HIT_LOOKUP_DONE):
                with m.If(hit_vector.any()):
                    # We have a hit
                    # update the replacement policy state
                    m.d.comb += replacement_policy.access_i.eq(1)
                    m.d.comb += replacement_policy.set_i.eq(fe_buffer_address.index)
                    m.d.comb += replacement_policy.way_i.eq(hit_index)
                    with m.If(fe_buffer_write_strobe.any()):
                        # handle write
                        m.d.comb += data_mem[hit_index][1].en.eq(fe_buffer_write_strobe)
                        m.d.comb += data_mem[hit_index][1].addr.eq(fe_buffer_address)
                        m.d.comb += data_mem[hit_index][1].data.eq(fe_buffer_write_data)
                        if self.config.WRITE_BACK:
                            # mark dirty if write back
                            m.d.sync += dirty_mem[hit_index][fe_buffer_address.index].eq(1)
                            m.d.sync += state.eq(States.STALL)
                        else:
                            # write to lower mem if write through
                            send_fe_buffer_request_to_lower_mem(next_state=States.STALL)
                    with m.Else():
                        # handle read
                        m.d.sync += state.eq(States.STALL)
                        m.d.comb += data_mem[hit_index][0].addr.eq(fe_buffer_address)
                        m.d.comb += data_mem[hit_index][0].en.eq(1)
                        m.d.sync += read_data_mem_select.eq(hit_index)
                with m.Else():
                    # Handle miss
                    with m.If((not self.config.WRITE_ALLOCATE) & fe_buffer_write_strobe.any()):
                        # write miss and write no-allocate -> only write to lower memory
                        send_fe_buffer_request_to_lower_mem(next_state=States.STALL)
                    with m.Else():
                        # It's a miss and we have to replace a block

                        # determine the state that will be taken next (or after write back)
                        # If it's a read or if not all bytes of the block are being written to
                        # (because the write strobe is not all ones or becaues there is more than
                        # one word in the block) we need to perform a read block operation afterwards
                        read_block_operation_needed = (~fe_buffer_write_strobe).any() | (self.config.BLOCK_SIZE > 1)
                        next_state = Mux(read_block_operation_needed, States.READ_BLOCK, States.READ_BLOCK_DONE)
                        # Update valid/dirty/tag memories
                        m.d.sync += valid_mem[next_block_replacement][fe_buffer_address.index].eq(1)
                        m.d.comb += tag_mem[next_block_replacement][1].en.eq(1)
                        m.d.comb += tag_mem[next_block_replacement][1].addr.eq(fe_buffer_address.index)
                        m.d.comb += tag_mem[next_block_replacement][1].data.eq(fe_buffer_address.tag)
                        if self.config.WRITE_BACK:
                            # If it is a write request, mark the block dirty; else clear the dirty bit
                            m.d.sync += dirty_mem[next_block_replacement][fe_buffer_address.index].eq(fe_buffer_write_strobe.any())
                        # update the replacement policy
                        m.d.comb += replacement_policy.access_i.eq(1)
                        m.d.comb += replacement_policy.replace_i.eq(1)
                        m.d.comb += replacement_policy.set_i.eq(fe_buffer_address.index)
                        m.d.comb += replacement_policy.way_i.eq(next_block_replacement)
                        with m.If(self.config.WRITE_BACK & dirty_mem[next_block_replacement][fe_buffer_address.index]):
                            # We have to write back the block to be replaced first because its dirty
                            m.d.sync += state.eq(States.WRITE_BACK_BLOCK)
                            # Construct the correct address
                            m.d.sync += write_back_address.index.eq(fe_buffer_address.index)
                            m.d.sync += write_back_address.tag.eq(tag_mem[next_block_replacement][0].data)
                            m.d.sync += write_back_address.word_offset.eq(0)
                            m.d.sync += write_back_way.eq(next_block_replacement)
                            m.d.sync += write_back_next_state.eq(next_state)
                            # initiate a read from data_mem for the data to be written back
                            # so that WRITE_BACK_BLOCK can put the data in the be buffer register
                            m.d.comb += data_mem[next_block_replacement][0].en.eq(1)
                            # initiate read for the first word to be written back. clear the word offset so that the actual first word gets read.
                            m.d.comb += data_mem[next_block_replacement][0].addr.eq(Cat(C(0, unsigned(self.word_offset_width)), fe_buffer_address.index))
                        with m.Else():
                            # No write back needed
                            m.d.sync += state.eq(next_state)
            with m.Case(States.WRITE_BACK_BLOCK):
                # Write back the block specified by the respective registers
                m.d.sync += be_buffer_address.eq(write_back_address)
                m.d.sync += be_buffer_write_strobe.eq(-1)
                # data_mem read needs to be initiated by previous state
                m.d.sync += be_buffer_write_data.eq(data_mem[write_back_way][0].data)
                m.d.sync += state.eq(States.SEND_MEM_REQUEST)
                # increment word offset of write back address
                m.d.sync += write_back_address.word_offset.eq(write_back_address.word_offset + 1)
                with m.If(write_back_address.word_offset == (self.config.BLOCK_SIZE - 1)):
                    # This is the last word to write back
                    m.d.sync += send_mem_request_next_state.eq(write_back_next_state)
                with m.Else():
                    # We're not done yet, come back after mem request has finished
                    m.d.sync += send_mem_request_next_state.eq(States.WRITE_BACK_BLOCK)
                    # initiate read for the word to be written back next
                    m.d.comb += data_mem[write_back_way][0].addr.eq(write_back_address.as_value() + 1)
                    m.d.comb += data_mem[write_back_way][0].en.eq(1)
            with m.Case(States.SEND_MEM_REQUEST):
                # Wait for the lower memory to become ready
                with m.If(self.be.port_ready):
                    # Send request to lower memory
                    m.d.sync += state.eq(States.SEND_MEM_REQUEST_WAIT)
                    m.d.comb += self.be.request_valid.eq(1)
            with m.Case(States.SEND_MEM_REQUEST_WAIT):
                with m.If(be_buffer_write_strobe.any() | self.be.read_data_valid): # FIXME This doesn't make much sense anymore without the write_done signal
                    # The last request was "processed" (write request was accepted, read request got answered)
                    with m.If(be_buffer_write_strobe.any()):
                        # Write - go to the next state
                        m.d.sync += state.eq(send_mem_request_next_state)
                    with m.Else():
                        with m.If(self.read_block_wc == 1):
                            # We only need to read one word, go to the next state
                            m.d.sync += state.eq(send_mem_request_next_state)
                        with m.Elif(be_read_data_word_counter == self.read_block_wc - 1):
                            # If we're done reading all words into the block, go to the next state
                            m.d.sync += state.eq(send_mem_request_next_state)
                            m.d.sync += be_read_data_word_counter.eq(0)
                        with m.Else():
                            # Else increse the counter
                            m.d.sync += be_read_data_word_counter.eq(be_read_data_word_counter + 1)
                        # Now do the actual writing the be read data into the block in the data_mem
                        # for the address, take the word offset of the original request into account and add our word counter offset to that (+ the index)
                        data_mem_address = Cat((be_read_data_word_counter + be_buffer_address.word_offset)[:self.word_offset_width], be_buffer_address.index)
                        m.d.comb += data_mem[next_block_replacement][1].addr.eq(data_mem_address)
                        m.d.comb += data_mem[next_block_replacement][1].data.eq(self.be.read_data.word_select(be_read_data_total_word_offset, self.config.DATA_WIDTH))
                        m.d.comb += data_mem[next_block_replacement][1].en.eq(-1)
            with m.Case(States.READ_BLOCK):
                m.d.sync += be_buffer_address.eq(Cat(read_block_word_offset, fe_buffer_address.index, fe_buffer_address.tag))
                m.d.sync += be_buffer_write_strobe.eq(0)
                # increment word offset for the read block operation (shouldn't do anything bad if block_size == 1 or block_size == read_block_wc)
                m.d.sync += read_block_word_offset.eq(read_block_word_offset + self.read_block_wc)
                with m.If(read_block_word_offset == self.config.BLOCK_SIZE - self.read_block_wc):
                    # We're done, go back
                    m.d.sync += send_mem_request_next_state.eq(States.READ_BLOCK_DONE)
                with m.Else():
                    # Come back, we're not done
                    m.d.sync += send_mem_request_next_state.eq(States.READ_BLOCK)
                # Send the memory request except for when its the address to which
                # we want to write anyway AND write strobe is all ones AND we would not
                # read any other byte from the word the BE would give is in this request (self.read_block_wc == 1)
                with m.If(~(
                            fe_buffer_write_strobe.all()
                            & (fe_buffer_address.word_offset == read_block_word_offset)
                            & (self.read_block_wc == 1)
                        )
                    ):
                    m.d.sync += state.eq(States.SEND_MEM_REQUEST)
                with m.Elif(read_block_word_offset + 1 == 0):
                    # If the memory request is not needed AND this the last word in the block,
                    # then we can go to READ_BLOCK_DONE. Else stay in this state and continue
                    # with the next word (no state modification needed!)
                    m.d.sync += state.eq(States.READ_BLOCK_DONE)
            with m.Case(States.READ_BLOCK_DONE):
                with m.If(fe_buffer_write_strobe):
                    # Handle write request
                    # Write data to internal data_mem
                    m.d.comb += data_mem[next_block_replacement][1].addr.eq(fe_buffer_address)
                    m.d.comb += data_mem[next_block_replacement][1].data.eq(fe_buffer_write_data)
                    m.d.comb += data_mem[next_block_replacement][1].en.eq(fe_buffer_write_strobe)
                    with m.If(self.config.WRITE_BACK):
                        # Stall if write back
                        m.d.sync += state.eq(States.STALL)
                    with m.Else():
                        # Send request to lower memory if write through
                        send_fe_buffer_request_to_lower_mem(States.STALL)
                with m.Else():
                    # Handle read request
                    m.d.sync += state.eq(States.STALL)
                    m.d.comb += data_mem[next_block_replacement][0].addr.eq(fe_buffer_address)
                    m.d.comb += data_mem[next_block_replacement][0].en.eq(1)
                    m.d.sync += read_data_mem_select.eq(next_block_replacement)
            with m.Case(States.STALL):
                # Check if the configured latency was reached. Get ready and hand out
                # the read data if that is the case. FIXME Remove this comment once the change below gets implemented
                # FIXME remoe Stall state entirely since the latency parameter is no longer supported
                # hand out read data
                m.d.sync += self.fe.read_data_valid.eq(~(fe_buffer_write_strobe.any()))
                m.d.sync += self.fe.read_data.eq(data_mem[read_data_mem_select][0].data)
                # go to READY again
                m.d.sync += state.eq(States.READY)
            with m.Case(States.FLUSH_CACHE):
                with m.If(self.config.WRITE_BACK):
                    # Flush the cache
                    # query tag memory
                    m.d.comb += tag_mem[flush_block_index][0].addr.eq(flush_set_index)
                    # Go to a state that will check if this block needs to be flushed
                    m.d.sync += state.eq(States.FLUSH_CACHE_BLOCK)
                with m.Else():
                    # flush the backend
                    m.d.sync += state.eq(States.FLUSH_BACKEND)
                    m.d.comb += self.be.flush.eq(1)
            with m.Case(States.FLUSH_CACHE_BLOCK):
                # Increment set/block indices
                m.d.sync += flush_set_index.eq(flush_set_index + 1)
                with m.If(flush_set_index == self.config.NUM_SETS - 1):
                    m.d.sync += flush_block_index.eq(flush_block_index + 1)

                # Is this the last set in the last block?
                is_last_block = (flush_set_index == self.config.NUM_SETS - 1) & (flush_block_index == self.config.NUM_WAYS - 1)
                # Determine the next state/the next state after write back
                next_state = Mux(is_last_block, States.FLUSH_BACKEND, States.FLUSH_CACHE)

                with m.If(dirty_mem[flush_block_index][flush_set_index] & valid_mem[flush_block_index][flush_set_index]):
                    # This block needs to be written back
                    # prepare things for the write back state and transition into it
                    m.d.sync += write_back_address.tag.eq(tag_mem[flush_block_index][0].data)
                    m.d.sync += write_back_address.index.eq(flush_set_index)
                    m.d.sync += write_back_address.word_offset.eq(0)
                    # tell the write back state which way to use
                    m.d.sync += write_back_way.eq(flush_block_index)
                    # query the data memory so the write back state can access the data. It'll do that on its own for the following words.
                    m.d.comb += data_mem[flush_block_index][0].addr.eq(Cat(C(0, shape=unsigned(self.word_offset_width)), flush_set_index))
                    m.d.comb += data_mem[flush_block_index][0].en.eq(1)
                    # set the next states
                    m.d.sync += state.eq(States.WRITE_BACK_BLOCK)
                    m.d.sync += write_back_next_state.eq(next_state)
                    # clear dirty bit
                    m.d.sync += dirty_mem[flush_block_index][flush_set_index].eq(0)
                with m.Else():
                    # Block doesn't need to be written back
                    m.d.sync += state.eq(next_state)
            with m.Case(States.FLUSH_BACKEND):
                with m.If(self.be.port_ready):
                    with m.If(~be_flush_requested):
                        # Send flush signal to be once it gets ready
                        m.d.comb += self.be.flush.eq(1)
                        m.d.sync += be_flush_requested.eq(1)
                    with m.Else():
                        # If the port is ready and we've already sent the request, then
                        # the backend must be done flushing
                        m.d.sync += state.eq(States.READY)
                        # reset flush requested register
                        m.d.sync += be_flush_requested.eq(0)

        return m
