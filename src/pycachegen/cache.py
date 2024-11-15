from math import ceil
from enum import Enum
from amaranth import *
from amaranth.lib import wiring, data
from amaranth.lib.memory import Memory
from amaranth.lib.wiring import In, Out
from amaranth.utils import exact_log2
from pycachegen.cache_config_validation import InternalCacheConfig
from pycachegen.memory_bus import MemoryBusSignature
from pycachegen.cache_address import (
    CacheAddressLayout,
    get_blockwise_incremented_address,
)
from pycachegen.replacement_policy import ReplacementPolicy
from pycachegen.elaborate_utils import one_hot_encode
from pycachegen.cache_memories import CacheMemories


class States(Enum):
    READY = 0
    WRITE_BACK_BLOCK = 1
    READ_BLOCK = 2
    EXECUTE_FE_WRITE_REQUEST = 3
    SEND_MEM_REQUEST = 4
    FLUSH_CACHE = 5
    FLUSH_BACKEND = 6
    FLUSH_CACHE_BLOCK = 7


class Cache(wiring.Component):
    def __init__(self, config: InternalCacheConfig) -> None:
        self.config = config

        super().__init__(
            {
                "fe": In(self.config.fe_signature),
                "hit_o": Out(1),
                "be": Out(self.config.be_signature),
            }
        )

    # fmt: off
    def elaborate(self, platform) -> Module:
        m = Module()

        # Create valid and dirty bits as well as tag and data memories
        valid_bits = Array([Array([Signal(name=f"valid_bits_{way_idx}_{set_idx}") for set_idx in range(self.config.num_sets)]) for way_idx in range(self.config.num_ways)])
        dirty_bits = Array([Array([Signal(name=f"dirty_bits_{way_idx}_{set_idx}") for set_idx in range(self.config.num_sets)]) for way_idx in range(self.config.num_ways)])
        memories = CacheMemories(self.config, m)

        ## replacement policy things
        # block to be replaced next for the set of the current fe_buffer_address
        next_block_replacement = Signal(range(self.config.num_ways))
        m.submodules.repl_pol = repl_pol = ReplacementPolicy(num_ways = self.config.num_ways, num_sets = self.config.num_sets, policy = self.config.replacement_policy)

        ## frontend input buffers
        fe_buffer_address = Signal(self.config.address_layout)
        fe_buffer_write_data = Signal(self.config.data_width)
        fe_buffer_write_strobe = Signal(self.config.bytes_per_word)

        ## backend output buffers
        # Create be buffers that use our own data/address/write strobe widths
        # Then "shift" the data/write strobe into place in the real be interface
        # according to the bits we cut off from the address
        be_buffer_write_data = Signal(unsigned(self.config.data_width))
        be_buffer_write_strobe = Signal(unsigned(self.config.bytes_per_word))
        be_buffer_address = Signal(self.config.address_layout)
        m.d.comb += self.be.address.eq(be_buffer_address.as_value()[-self.config.be_address_width : ])
        m.d.comb += self.be.write_data.eq(0)
        m.d.comb += self.be.write_strobe.eq(0)
        m.d.comb += self.be.write_data.word_select(be_buffer_address.as_value()[:-self.config.be_address_width], self.config.data_width).eq(be_buffer_write_data)
        m.d.comb += self.be.write_strobe.word_select(be_buffer_address.as_value()[:-self.config.be_address_width], self.config.bytes_per_word).eq(be_buffer_write_strobe)

        ## internal registers
        # FSM state
        state = Signal(States)
        # one bit per way to indicate a hit in that way
        hit_vector = Signal(unsigned(self.config.num_ways))
        # one hot encode the vector into this signal
        hit_index = one_hot_encode(m, hit_vector)
        # a view for convenient access to the tag/index/word offset bits
        fe_address_view = data.View(self.config.address_layout, self.fe.address)
        # Output port ready status based on current state
        m.d.comb += self.fe.port_ready.eq(state == States.READY)
        # Whether to hand the data in the buffer out or the data from a data mem
        fe_read_data_select_buffer = Signal()
        # Index of the data_mem that contains the data requested by the frontend
        read_data_mem_select = Signal(range(self.config.num_ways))
        # Buffer that contains the data requested by the frontend
        fe_read_data_buffer = Signal(unsigned(self.config.data_width))
        # Use that index to assign the correct read data to the fe port
        with m.If(~fe_read_data_select_buffer):
            m.d.comb += self.fe.read_data.eq(memories.data_mem_rp[read_data_mem_select].data)
        with m.Else():
            m.d.comb += self.fe.read_data.eq(fe_read_data_buffer)

        ## States.READ_BLOCK
        # counter for how many read operations have been done so far
        read_block_read_counter = Signal(range(self.config.read_block_requests_needed + 1))
        # counter for how many words of the be read data have been written back so far
        read_block_write_counter = Signal(self.config.read_block_wc_width)
        # the address for which a read request was issued
        read_block_previous_address = Signal(self.config.address_layout)
        # the address for the next write action (previous address incremented by write counter)
        read_block_write_address = Signal(self.config.address_layout)
        m.d.comb += read_block_write_address.eq(get_blockwise_incremented_address(read_block_previous_address, read_block_write_counter, m, self.config.read_block_wc_width))
        # the word to be written back next
        read_block_write_data = Signal(self.config.data_width)
        m.d.comb += read_block_write_data.eq(self.be.read_data.word_select(read_block_write_address.as_value()[:self.config.address_width_difference], self.config.data_width))
        # state that read block should take next
        read_block_next_state = Signal(States)

        ## States.FLUSH_CACHE / States.FLUSH_CACHE_BLOCK / States.FLUSH_BACKEND
        # index of the set to be flushed next
        flush_set_index = Signal(self.config.index_width)
        # index of the block that is currently being flushed
        flush_block_index = Signal(range(self.config.num_ways))
        # whether we already told the backend to flush itself
        be_flush_requested = Signal()

        ## States.WRITE_BACK_BLOCK
        # address and way to identify the block to be written back
        write_back_address = Signal(self.config.address_layout)
        # source of the data to write back.
        # 0: from data mem (read needs to be initiated before entering this state. way needs to be specified in next signal),
        # 1: from write back buffer
        write_back_data_from_buffer = Signal()
        # data memory way that contains the data to be written back
        write_back_way = Signal(range(self.config.num_ways))
        # state to take after the WRITE_BACK state
        write_back_next_state = Signal(States)

        ## States.SEND_MEM_REQUEST
        # state to go to afterwards
        send_mem_request_next_state = Signal(States)

        ## Evict operation reads one block of the internal data_mem and writes it to a buffer.
        # evict block operation puts data to be written back in this buffer
        evicted_block_buffer = Array([Signal(unsigned(self.config.data_width), name=f"evicted_block_buffer_{i}") for i in range(self.config.block_size)])
        # Enable signal to start the operation. Will get disabled once it's done.
        evict_block_enable = Signal()
        # The address of the block to write to the buffer
        evict_block_address = Signal(self.config.address_layout)
        # Counts how many cycles have passed since starting the operation
        evict_block_counter = Signal(range(self.config.block_size + 1))
        # Construct the address the same way that the read block operation does
        # so that we evict the block before it gets overwritten by the read block operation
        evict_block_incremented_address = get_blockwise_incremented_address(evict_block_address, evict_block_counter, m, self.config.read_block_wc_width)

        # remember the previous word offset so we know in which slot of the buffer the read data belongs
        evict_block_previous_word_offset = Signal(self.config.word_offset_width)

        with m.If(evict_block_enable):
            with m.If(evict_block_counter < self.config.block_size):
                # Send read request to data_mem
                memories.init_data_mem_read(next_block_replacement, evict_block_incremented_address)
                # Store the address we just sent a request to
                m.d.sync += evict_block_previous_word_offset.eq(evict_block_incremented_address.word_offset)
                # Increment the total counter
                m.d.sync += evict_block_counter.eq(evict_block_counter + 1)

            with m.If(evict_block_counter > 0):
                # Write the previously requested word to the buffer
                m.d.sync += evicted_block_buffer[evict_block_previous_word_offset].eq(memories.data_mem_rp[next_block_replacement].data)

            with m.If(evict_block_counter == self.config.block_size):
                # We're done, reset everything.
                m.d.sync += evict_block_enable.eq(0)
                m.d.sync += evict_block_counter.eq(0)

        def send_fe_buffer_request_to_lower_mem(next_state):
            """Uses the request stored in the fe buffers to send a request
            to the lower memory.
            """
            with m.If(self.be.port_ready):
                m.d.comb += be_buffer_address.eq(fe_buffer_address)
                m.d.comb += be_buffer_write_data.eq(fe_buffer_write_data)
                m.d.comb += be_buffer_write_strobe.eq(fe_buffer_write_strobe)
                m.d.comb += self.be.request_valid.eq(1)
                m.d.sync += state.eq(next_state)
            with m.Else():
                m.d.sync += state.eq(States.SEND_MEM_REQUEST)
                m.d.sync += send_mem_request_next_state.eq(next_state)

        def send_fe_request_to_lower_mem(next_state):
            """Send the request from the fe to the lower memory."""
            with m.If(self.be.port_ready):
                m.d.comb += be_buffer_address.eq(self.fe.address)
                m.d.comb += be_buffer_write_data.eq(self.fe.write_data)
                m.d.comb += be_buffer_write_strobe.eq(self.fe.write_strobe)
                m.d.comb += self.be.request_valid.eq(1)
                m.d.sync += state.eq(next_state)
            with m.Else():
                m.d.sync += state.eq(States.SEND_MEM_REQUEST)
                m.d.sync += send_mem_request_next_state.eq(next_state)

        def prepare_block_write_back(next_state: States):
            """Prepare everything for writing back the block to be replaced
            by the frontend request. This includes starting the evict operation
            and configuring the registers for the write back operation. The
            transition to the write back block state has to be performed manually.



            Args:
                next_state (States): State to transition to after write back.
            """
            # Write data_mem block to be replaced into a buffer should we need a write back
            m.d.sync += evict_block_enable.eq(1)
            m.d.sync += evict_block_address.as_value().eq(self.fe.address)
            # Prepare things for the Write Back State should we transition to it
            m.d.sync += write_back_data_from_buffer.eq(1)
            m.d.sync += write_back_next_state.eq(next_state)
            # construct the correct address (the address of the block to be replaced)
            m.d.sync += write_back_address.as_value().eq(
                Cat(
                    C(0, unsigned(self.config.word_offset_width)),
                    fe_address_view.index,
                    memories.tag_mem_rp[way_to_replace].data
                )
            )

        with m.Switch(state):
            with m.Case(States.READY):
                with m.If(self.fe.flush):
                    m.d.sync += state.eq(States.FLUSH_CACHE)
                    # Reset fe outputs
                    m.d.sync += self.fe.read_data_valid.eq(0)
                with m.Elif(self.fe.request_valid):
                    # Reset fe outputs
                    m.d.sync += self.fe.read_data_valid.eq(0)
                    # buffer inputs
                    m.d.sync += fe_buffer_address.eq(self.fe.address)
                    m.d.sync += fe_buffer_write_strobe.eq(self.fe.write_strobe)
                    m.d.sync += fe_buffer_write_data.eq(self.fe.write_data)
                    # query tag memories and check whether we have a hit in any way
                    for i in range(self.config.num_ways):
                        memories.init_tag_mem_read(i, fe_address_view.index)
                        m.d.comb += hit_vector[i].eq(
                            (memories.tag_mem_rp[i].data == fe_address_view.tag)
                            & valid_bits[i][fe_address_view.index]
                        )
                    # purely for statistics: let the outside know if we had a hit
                    m.d.sync += self.hit_o.eq(hit_vector.any())
                    # query replacement policy and buffer the next way to be replaced for this set
                    way_to_replace = repl_pol.get_way_to_replace(fe_address_view.index, m)
                    m.d.sync += next_block_replacement.eq(way_to_replace)
                    with m.If(hit_vector.any()):
                        # We have a hit
                        # update the replacement policy state
                        repl_pol.access(fe_address_view.index, hit_index, m)
                        with m.If(self.fe.write_strobe.any()):
                            # write data to cache
                            memories.init_data_mem_write(hit_index, self.fe.address, self.fe.write_data, self.fe.write_strobe)
                            if self.config.write_back:
                                # mark dirty if write back
                                m.d.sync += dirty_bits[hit_index][fe_address_view.index].eq(1)
                                m.d.sync += state.eq(States.READY)
                            else:
                                # write to lower mem if write through
                                send_fe_request_to_lower_mem(States.READY)
                        with m.Else():
                            # handle read
                            m.d.sync += state.eq(States.READY)
                            m.d.sync += read_data_mem_select.eq(hit_index)
                            m.d.sync += fe_read_data_select_buffer.eq(0)
                            m.d.sync += self.fe.read_data_valid.eq(1)
                            memories.init_data_mem_read(hit_index, self.fe.address)
                    with m.Else():
                        # We have a miss
                        with m.If((not self.config.write_allocate) & self.fe.write_strobe.any()):
                            # write miss and write no-allocate -> only write to lower memory
                            send_fe_request_to_lower_mem(States.READY)
                        with m.Else():
                            # In all other cases, we have to replace a block
                            # Update valid/dirty/tag memories
                            m.d.sync += valid_bits[way_to_replace][fe_address_view.index].eq(1)
                            memories.init_tag_mem_write(way_to_replace, fe_address_view.index, fe_address_view.tag)
                            if self.config.write_back:
                                # If it is a write request, mark the block dirty; else clear the dirty bit
                                m.d.sync += dirty_bits[way_to_replace][fe_address_view.index].eq(self.fe.write_strobe.any())
                            # find out whether we need a write back operation
                            write_back_needed = self.config.write_back & dirty_bits[way_to_replace][fe_address_view.index]
                            # update the replacement policy
                            repl_pol.replace(fe_address_view.index, m)
                            with m.If(self.fe.write_strobe.any()):
                                # Handle write
                                with m.If((~self.fe.write_strobe.all()) | (self.config.block_size > 1)):
                                    # partial write (doesn't overwrite the entire word or we just store multiple words per block)
                                    # -> we have to read in the block from the main memory first
                                    m.d.sync += state.eq(States.READ_BLOCK)
                                    with m.If(write_back_needed):
                                        m.d.sync += read_block_next_state.eq(States.WRITE_BACK_BLOCK)
                                        prepare_block_write_back(States.EXECUTE_FE_WRITE_REQUEST)
                                    with m.Else():
                                        m.d.sync += read_block_next_state.eq(States.EXECUTE_FE_WRITE_REQUEST)
                                with m.Else():
                                    # full write -> no read block operation needed
                                    if self.config.write_back:
                                        with m.If(dirty_bits[way_to_replace][fe_address_view.index]):
                                            # write back if dirty
                                            m.d.sync += state.eq(States.WRITE_BACK_BLOCK)
                                            # Construct the correct address
                                            m.d.sync += write_back_address.index.eq(fe_address_view.index)
                                            m.d.sync += write_back_address.tag.eq(memories.tag_mem_rp[way_to_replace].data)
                                            m.d.sync += write_back_address.word_offset.eq(0)
                                            m.d.sync += write_back_way.eq(way_to_replace)
                                            # Select data source and next state after write back
                                            m.d.sync += write_back_data_from_buffer.eq(0)
                                            # the EXECUTE_FE_WRITE_REQUEST State will write the data to the cache
                                            m.d.sync += write_back_next_state.eq(States.EXECUTE_FE_WRITE_REQUEST)
                                            # Query data mem so that the write back state can use its data
                                            # clear the word offset so that the actual first word gets read.
                                            memories.init_data_mem_read(way_to_replace, Cat(C(0, unsigned(self.config.word_offset_width)), fe_address_view.index))
                                        with m.Else():
                                            # Write the data to the cache and we're done if the block is not dirty
                                            m.d.sync += state.eq(States.READY)
                                            memories.init_data_mem_write(way_to_replace, self.fe.address, self.fe.write_data, self.fe.write_strobe)
                                    else:
                                        # write to cache and to lower mem if write through (write through + no-allocate was caught earlier)
                                        send_fe_request_to_lower_mem(States.READY)
                                        memories.init_data_mem_write(way_to_replace, self.fe.address, self.fe.write_data, self.fe.write_strobe)
                            with m.Else():
                                # Handle read
                                m.d.sync += state.eq(States.READ_BLOCK)
                                with m.If(write_back_needed):
                                    m.d.sync += read_block_next_state.eq(States.WRITE_BACK_BLOCK)
                                    prepare_block_write_back(States.READY)
                                with m.Else():
                                    m.d.sync += read_block_next_state.eq(States.READY)
            with m.Case(States.WRITE_BACK_BLOCK):
                # wait for the BE to get ready
                with m.If(self.be.port_ready):
                    # Write back the block specified by the respective registers
                    m.d.comb += be_buffer_address.eq(write_back_address)
                    m.d.comb += be_buffer_write_strobe.eq(-1)
                    m.d.comb += self.be.request_valid.eq(1)
                    with m.If(write_back_data_from_buffer):
                        # take the data from the buffer
                        # we can write multiple words at once if our block size is greater than 1 and
                        # if the BE data width allows it
                        m.d.comb += self.be.write_data.eq(
                            Cat([evicted_block_buffer[write_back_address.word_offset + i] for i in range(self.config.read_block_wc)])
                            << (self.config.data_width * write_back_address.as_value()[:-self.config.be_address_width])
                        )
                        m.d.comb += self.be.write_strobe.eq(
                            (2**(self.config.bytes_per_word * self.config.read_block_wc) - 1)
                            << (self.config.bytes_per_word * write_back_address.as_value()[:-self.config.be_address_width])
                        )
                        # increment word offset of write back address
                        m.d.sync += write_back_address.word_offset.eq(write_back_address.word_offset + self.config.read_block_wc)
                        with m.If(write_back_address.word_offset == (self.config.block_size - self.config.read_block_wc)):
                            # This is the last word to write back -> proceed with the next state
                            m.d.sync += state.eq(write_back_next_state)
                    with m.Else():
                        # take the data from the data memory
                        m.d.comb += be_buffer_write_data.eq(memories.data_mem_rp[write_back_way].data)
                        # data_mem read needs to be initiated by previous state
                        # -> we also need to initiate a new read
                        memories.init_data_mem_read(write_back_way, write_back_address.as_value() + 1)
                        # increment word offset of write back address
                        m.d.sync += write_back_address.word_offset.eq(write_back_address.word_offset + 1)
                        with m.If(write_back_address.word_offset == (self.config.block_size - 1)):
                            # This is the last word to write back -> proceed with the next state
                            m.d.sync += state.eq(write_back_next_state)
            with m.Case(States.READ_BLOCK):
                # wait until the memory gets ready and (all words of previous request were written to the cache or this is the first request)
                # and we have not already issued all needed requests
                with m.If(
                    self.be.port_ready
                    & ((read_block_write_counter == (self.config.read_block_wc - 1)) | (read_block_read_counter == 0))
                    & (read_block_read_counter < self.config.read_block_requests_needed)
                ):
                    # Issue a memory read request
                    # Critical word first: Start at the word that was requested
                    # So we can hand that out first if it was a read request
                    m.d.comb += be_buffer_address.eq(fe_buffer_address)
                    m.d.comb += be_buffer_write_strobe.eq(0)
                    # construct the correct word offset and increment the word offset for the next request
                    with m.If(
                            fe_buffer_write_strobe.all()
                            & (read_block_read_counter == 0)
                            & (self.config.read_block_wc == 1)
                    ):
                        # If the fe completely overwrites all the words that we'd get from the current request, we can skip it.
                        # (this is only the case if write strobe is all ones, we'd only get one word out of the request and
                        # the current request targets the same word as the fe address)
                        m.d.sync += read_block_read_counter.eq(read_block_read_counter + 2)
                        m.d.comb += be_buffer_address.word_offset.eq(fe_buffer_address.as_value() + 1)
                    with m.Else():
                        # Else just increment the word offset by the amount of words we can retrieve from one be word
                        m.d.sync += read_block_read_counter.eq(read_block_read_counter + 1)
                        m.d.comb += be_buffer_address.word_offset.eq(fe_buffer_address.as_value() + read_block_read_counter * self.config.read_block_wc)
                    m.d.comb += self.be.request_valid.eq(1)
                    # store the address so that we still have it when writing the words to the cache
                    m.d.sync += read_block_previous_address.eq(be_buffer_address.as_value())

                with m.If(self.be.port_ready & (read_block_read_counter != 0)):
                    # A read request was processed, write the data to the cache
                    memories.init_data_mem_write(
                        way=next_block_replacement,
                        addr=read_block_write_address,
                        data=read_block_write_data,
                        strobe=-1
                    )
                    # increment write counter
                    m.d.sync += read_block_write_counter.eq(read_block_write_counter + 1)

                    # determine if we should hand out the read data to the FE
                    with m.If(
                        (read_block_read_counter == 1) # it was the first read request to the BE
                        & (~fe_buffer_write_strobe.any()) # the FE sent a read request
                        & (read_block_write_counter == 0) # This is the first cycle after the read data is valid
                    ):
                        m.d.sync += fe_read_data_select_buffer.eq(1)
                        m.d.sync += fe_read_data_buffer.eq(read_block_write_data)
                        m.d.sync += self.fe.read_data_valid.eq(1)

                    with m.If(
                        (read_block_write_counter == (self.config.read_block_wc - 1))
                        & (read_block_read_counter == self.config.read_block_requests_needed)
                    ):
                        # go to the next state if no more read requests are needed and if we've written all words of the last request to the cache
                        m.d.sync += state.eq(read_block_next_state)
                        # also reset the read counter (the write counter has appropriate width and doesn't need a reset)
                        m.d.sync += read_block_read_counter.eq(0)
            with m.Case(States.EXECUTE_FE_WRITE_REQUEST):
                # Handle write request - this state is used after write back/read block operations
                # Write data to internal data_mem
                memories.init_data_mem_write(next_block_replacement, fe_buffer_address, fe_buffer_write_data, fe_buffer_write_strobe)
                with m.If(self.config.write_back):
                    # We're done if using write back
                    m.d.sync += state.eq(States.READY)
                with m.Else():
                    # Send request to lower memory if write through
                    send_fe_buffer_request_to_lower_mem(States.READY)
            with m.Case(States.SEND_MEM_REQUEST):
                send_fe_buffer_request_to_lower_mem(send_mem_request_next_state)
            with m.Case(States.FLUSH_CACHE):
                with m.If(self.config.write_back):
                    # Flush the cache
                    # query tag memory
                    memories.init_tag_mem_read(flush_block_index, flush_set_index)
                    # Go to a state that will check if this block needs to be flushed
                    m.d.sync += state.eq(States.FLUSH_CACHE_BLOCK)
                with m.Else():
                    # flush the backend
                    m.d.sync += state.eq(States.FLUSH_BACKEND)
                    m.d.comb += self.be.flush.eq(1)
            with m.Case(States.FLUSH_CACHE_BLOCK):
                # Increment set/block indices
                m.d.sync += flush_set_index.eq(flush_set_index + 1)
                with m.If(flush_set_index == self.config.num_sets - 1):
                    m.d.sync += flush_block_index.eq(flush_block_index + 1)

                # Is this the last set in the last block?
                is_last_block = (flush_set_index == self.config.num_sets - 1) & (flush_block_index == self.config.num_ways - 1)
                # Determine the next state/the next state after write back
                next_state = Mux(is_last_block, States.FLUSH_BACKEND, States.FLUSH_CACHE)

                with m.If(dirty_bits[flush_block_index][flush_set_index] & valid_bits[flush_block_index][flush_set_index]):
                    # This block needs to be written back
                    # prepare things for the write back state and transition into it
                    m.d.sync += write_back_address.tag.eq(memories.tag_mem_rp[flush_block_index].data)
                    m.d.sync += write_back_address.index.eq(flush_set_index)
                    m.d.sync += write_back_address.word_offset.eq(0)
                    # tell the write back state which way to use
                    m.d.sync += write_back_way.eq(flush_block_index)
                    m.d.sync += write_back_data_from_buffer.eq(0)
                    # query the data memory so the write back state can access the data. It'll do that on its own for the following words.
                    memories.init_data_mem_read(flush_block_index, Cat(C(0, shape=unsigned(self.config.word_offset_width)), flush_set_index))
                    # set the next states
                    m.d.sync += state.eq(States.WRITE_BACK_BLOCK)
                    m.d.sync += write_back_next_state.eq(next_state)
                    # clear dirty bit
                    m.d.sync += dirty_bits[flush_block_index][flush_set_index].eq(0)
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
