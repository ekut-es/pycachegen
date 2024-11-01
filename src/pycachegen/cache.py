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
    WRITE_BACK_BLOCK = 1
    READ_BLOCK = 2
    EXECUTE_FE_WRITE_REQUEST = 3
    SEND_MEM_REQUEST = 4
    WRITE_BE_READ_DATA_TO_CACHE = 5
    FLUSH_CACHE = 6
    FLUSH_BACKEND = 7
    FLUSH_CACHE_BLOCK = 8


class Cache(wiring.Component):
    def __init__(self, config: InternalCacheConfig) -> None:
        self.config = config

        self.fe_signature = MemoryBusSignature(
            address_width=config.address_width,
            data_width=config.data_width,
            bytes_per_word=self.config.bytes_per_word,
        )
        self.be_signature = MemoryBusSignature(
            address_width=config.be_address_width,
            data_width=config.be_data_width,
            bytes_per_word=self.config.be_bytes_per_word,
        )
        self.address_layout = CacheAddressLayout(
            index_width=self.config.index_width,
            tag_width=self.config.tag_width,
            word_offset_width=self.config.word_offset_width,
        )

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

        ## Create valid, dirty, tag, data memories - one per way
        # usage: valid_mem[way][index], tag_mem[way][index], data_mem[way][Cat(word_offset, index)]
        # data memory contains values that represent whole blocks (potentially multiple words!)
        valid_mem = Array([Array([Signal(name=f"valid_mem_{way_idx}_{set_idx}") for set_idx in range(self.config.num_sets)]) for way_idx in range(self.config.num_ways)])
        dirty_mem = Array([Array([Signal(name=f"dirty_mem_{way_idx}_{set_idx}") for set_idx in range(self.config.num_sets)]) for way_idx in range(self.config.num_ways)])
        tag_mem = Array()
        data_mem = Array()
        for i in range(self.config.num_ways):
            new_tag_mem = Memory(shape=unsigned(self.config.tag_width), depth=self.config.num_sets, init=[])
            m.submodules[f"tag_mem_{i}"] = new_tag_mem
            tag_mem.append((new_tag_mem.read_port(domain="comb"), new_tag_mem.write_port()))

            new_data_mem = Memory(
                shape=unsigned(self.config.data_width), depth=self.config.num_sets*self.config.block_size, init=[]
            )
            m.submodules[f"data_mem_{i}"] = new_data_mem
            data_mem.append(
                (
                    new_data_mem.read_port(),
                    new_data_mem.write_port(granularity=self.config.byte_size),
                )
            )
            # disable data_mem.read_port.en by default so that the read data gets preserved even when the address changes
            # thats necessary because the read data might only be needed after several cycles
            m.d.comb += data_mem[-1][0].en.eq(0)

        def init_data_mem_read(way, addr):
            m.d.comb += data_mem[way][0].en.eq(1)
            m.d.comb += data_mem[way][0].addr.eq(addr)

        def init_data_mem_write(way, addr, data, strobe):
            m.d.comb += data_mem[way][1].en.eq(strobe)
            m.d.comb += data_mem[way][1].addr.eq(addr)
            m.d.comb += data_mem[way][1].data.eq(data)

        def init_tag_mem_read(way, addr):
            m.d.comb += tag_mem[way][0].addr.eq(addr)

        def init_tag_mem_write(way, addr, data):
            m.d.comb += tag_mem[way][1].en.eq(1)
            m.d.comb += tag_mem[way][1].addr.eq(addr)
            m.d.comb += tag_mem[way][1].data.eq(data)

        ## replacement policy things
        # block to be replaced next for the set of the current fe_buffer_address
        next_block_replacement = Signal(range(self.config.num_ways))
        m.submodules.replacement_policy = replacement_policy = ReplacementPolicy(num_ways = self.config.num_ways, num_sets = self.config.num_sets, policy = self.config.replacement_policy)

        ## frontend input buffers
        fe_buffer_address = Signal(self.address_layout
        )
        fe_buffer_write_data = Signal(self.config.data_width)
        fe_buffer_write_strobe = Signal(self.config.bytes_per_word)

        ## backend output buffers
        # Create be buffers that use our own data/address/write strobe widths
        # Then "shift" the data/write strobe into place in the real be interface
        # according to the bits we cut off from the address
        be_buffer_write_data = Signal(unsigned(self.config.data_width))
        be_buffer_write_strobe = Signal(unsigned(self.config.bytes_per_word))
        be_buffer_address = Signal(self.address_layout)
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
        fe_address_view = data.View(self.address_layout, self.fe.address)
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
            m.d.comb += self.fe.read_data.eq(data_mem[read_data_mem_select][0].data)
        with m.Else():
            m.d.comb += self.fe.read_data.eq(fe_read_data_buffer)

        ## States.SEND_MEM_REQUEST / States.WRITE_BE_READ_DATA_TO_CACHE
        # FSM state that will be taken after the SEND_MEM_REQUEST state (or after WRITE_BE_READ_DATA_TO_CACHE)
        send_mem_request_next_state = Signal(States)

        ## States.WRITE_BE_READ_DATA_TO_CACHE
        # counter for counting which word of the be read data to write to the data_mem next.
        be_read_data_word_counter = Signal(range(self.config.read_block_wc))
        # We need to increment the address based on the counter. But we need to consider that the overflow
        # has to happen within the lower bits that specify the index of the our-size-word within the be size word
        # (this index is then stored in the be_address_incremented_cut_off_bits signal)
        # The READ_BLOCK State will then increment the other word_offset bits for jumping into the next be word.
        incremented_be_buffer_address = Signal(unsigned(self.config.address_width))
        m.d.comb += incremented_be_buffer_address.eq(Cat(
            (be_buffer_address.word_offset + be_read_data_word_counter)[:self.config.read_block_wc_width],
            be_buffer_address.as_value()[self.config.read_block_wc_width:]
        ))
        addr_width_difference = self.config.address_width - self.config.be_address_width
        # This signal specifies the index of the word to extract from the be read data.
        be_address_incremented_cut_off_bits = Signal(unsigned(addr_width_difference))
        m.d.comb += be_address_incremented_cut_off_bits.eq(incremented_be_buffer_address)

        ## States.READ_BLOCK
        # counter for the READ BLOCK state that indicates how many words have been read so far
        read_block_word_offset = Signal(self.config.word_offset_width)
        # state that read block should take next
        read_block_next_state = Signal(States)

        ## States.FLUSH_CACHE / States.FLUSH_CACHE_BLOCK / States.FLUSH_BACKEND
        # index of the set to be flushed next
        flush_set_index = Signal(self.config.index_width)
        # index of the block that is currently being flushed
        flush_block_index = Signal(range(self.config.num_ways))
        # whether we already told the backend to flush itself
        be_flush_requested = Signal()

        ## States.WRITE_BACK_BLOCk
        # address and way to identify the block to be written back
        write_back_address = Signal(self.address_layout)
        # source of the data to write back.
        # 0: from data mem (read needs to be initiated before entering this state. way needs to be specified in next signal),
        # 1: from write back buffer
        write_back_data_from_buffer = Signal()
        # data memory way that contains the data to be written back
        write_back_way = Signal(range(self.config.num_ways))
        # state to take after the WRITE_BACK state
        write_back_next_state = Signal(States)

        ## Evict operation reads one block of the internal data_mem and writes it to a buffer.
        # evict block operation puts data to be written back in this buffer
        evicted_block_buffer = Array([Signal(unsigned(self.config.data_width), name=f"write_back_data_{i}") for i in range(self.config.block_size)])
        # Enable signal to start the operation. Will get disabled once it's done.
        evict_block_enable = Signal()
        # The address of the block to write to the buffer
        evict_block_address = Signal(self.address_layout)
        # Counts how many cycles have passed since starting the operation
        evict_block_counter = Signal(range(self.config.block_size + 1))
        # Construct the address the same way that the read block operation does so that we
        # evict the blocks in the same order they get overwritten
        evict_block_incremented_address = Signal(self.address_layout)
        m.d.comb += evict_block_incremented_address.as_value().eq(evict_block_address)
        m.d.comb += evict_block_incremented_address.word_offset.eq(
            Cat(
                (evict_block_address.word_offset + evict_block_counter)[:self.config.read_block_wc_width],
                (evict_block_address.word_offset[self.config.read_block_wc_width:] + evict_block_counter[self.config.read_block_wc_width:])
            )
        )
        # remember the previous word offset so we know in which slot of the buffer the read data belongs
        evict_block_previous_word_offset = Signal(self.config.word_offset_width)

        with m.If(evict_block_enable):
            with m.If(evict_block_counter < self.config.block_size):
                # Send read request to data_mem
                init_data_mem_read(next_block_replacement, evict_block_incremented_address)
                # Store the address we just sent a request to
                m.d.sync += evict_block_previous_word_offset.eq(evict_block_incremented_address.word_offset)
                # Increment the total counter
                m.d.sync += evict_block_counter.eq(evict_block_counter + 1)

            with m.If(evict_block_counter > 0):
                # Write the previously requested word to the buffer
                m.d.sync += evicted_block_buffer[evict_block_previous_word_offset].eq(data_mem[next_block_replacement][0].data)

            with m.If(evict_block_counter == self.config.block_size):
                # We're done, reset everything.
                m.d.sync += evict_block_enable.eq(0)
                m.d.sync += evict_block_counter.eq(0)

        def send_fe_buffer_request_to_lower_mem(next_state: States):
            """Uses the request stored in the fe buffers to send a request
            to the lower memory. Goes to the SEND_MEM_REQUEST state to do so.
            """
            m.d.sync += be_buffer_address.eq(fe_buffer_address)
            m.d.sync += be_buffer_write_data.eq(fe_buffer_write_data)
            m.d.sync += be_buffer_write_strobe.eq(fe_buffer_write_strobe)
            m.d.sync += state.eq(States.SEND_MEM_REQUEST)
            m.d.sync += send_mem_request_next_state.eq(next_state)

        def send_fe_request_to_lower_mem(next_state: States):
            """Send the request from the fe to the lower memory. Goes to the
            SEND_MEM_REQUEST state to do so.
            """
            m.d.sync += be_buffer_address.eq(self.fe.address)
            m.d.sync += be_buffer_write_data.eq(self.fe.write_data)
            m.d.sync += be_buffer_write_strobe.eq(self.fe.write_strobe)
            m.d.sync += state.eq(States.SEND_MEM_REQUEST)
            m.d.sync += send_mem_request_next_state.eq(next_state)

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
                        init_tag_mem_read(i, fe_address_view.index)
                        m.d.comb += hit_vector[i].eq(
                            (tag_mem[i][0].data == fe_address_view.tag)
                            & valid_mem[i][fe_address_view.index]
                        )
                    # purely for statistics: let the outside know if we had a hit
                    m.d.sync += self.hit_o.eq(hit_vector.any())
                    # query replacement policy and buffer the next way to be replaced for this set
                    m.d.comb += replacement_policy.set_i.eq(fe_address_view.index)
                    m.d.sync += next_block_replacement.eq(replacement_policy.next_replacement_o)
                    with m.If(hit_vector.any()):
                        # We have a hit
                        # update the replacement policy state
                        m.d.comb += replacement_policy.access_i.eq(1)
                        m.d.comb += replacement_policy.way_i.eq(hit_index)
                        with m.If(self.fe.write_strobe.any()):
                            # write data to cache
                            init_data_mem_write(hit_index, self.fe.address, self.fe.write_data, self.fe.write_strobe)
                            if self.config.write_back:
                                # mark dirty if write back
                                m.d.sync += dirty_mem[hit_index][fe_address_view.index].eq(1)
                                m.d.sync += state.eq(States.READY)
                            else:
                                # write to lower mem if write through
                                send_fe_request_to_lower_mem(next_state=States.READY)
                        with m.Else():
                            # handle read
                            m.d.sync += state.eq(States.READY)
                            m.d.sync += read_data_mem_select.eq(hit_index)
                            m.d.sync += fe_read_data_select_buffer.eq(0)
                            m.d.sync += self.fe.read_data_valid.eq(1)
                            init_data_mem_read(hit_index, self.fe.address)
                    with m.Else():
                        # We have a miss
                        with m.If((not self.config.write_allocate) & self.fe.write_strobe.any()):
                            # write miss and write no-allocate -> only write to lower memory
                            send_fe_request_to_lower_mem(next_state=States.READY)
                        with m.Else():
                            # In all other cases, we have to replace a block
                            # Update valid/dirty/tag memories
                            m.d.sync += valid_mem[replacement_policy.next_replacement_o][fe_address_view.index].eq(1)
                            init_tag_mem_write(replacement_policy.next_replacement_o, fe_address_view.index, fe_address_view.tag)
                            if self.config.write_back:
                                # If it is a write request, mark the block dirty; else clear the dirty bit
                                m.d.sync += dirty_mem[replacement_policy.next_replacement_o][fe_address_view.index].eq(self.fe.write_strobe.any())
                            # update the replacement policy
                            m.d.comb += replacement_policy.access_i.eq(1)
                            m.d.comb += replacement_policy.replace_i.eq(1)
                            m.d.comb += replacement_policy.way_i.eq(replacement_policy.next_replacement_o)
                            with m.If(self.fe.write_strobe.any()):
                                # Handle write
                                with m.If((~self.fe.write_strobe.all()) | (self.config.block_size > 1)):
                                    # partial write (doesn't overwrite the entire word or we just store multiple words per block)
                                    # -> we have to read in the block from the main memory first
                                    m.d.sync += state.eq(States.READ_BLOCK)
                                    m.d.sync += read_block_next_state.eq(
                                        Mux(
                                            self.config.write_back & dirty_mem[replacement_policy.next_replacement_o][fe_address_view.index],
                                            States.WRITE_BACK_BLOCK,
                                            States.EXECUTE_FE_WRITE_REQUEST
                                        )
                                    )
                                    # Write data_mem block to be replaced into a buffer should we need a write back
                                    m.d.sync += evict_block_enable.eq(1)
                                    m.d.sync += evict_block_address.as_value().eq(self.fe.address)
                                    # Prepare things for the Write Back State should we transition to it
                                    m.d.sync += write_back_data_from_buffer.eq(1)
                                    m.d.sync += write_back_next_state.eq(States.EXECUTE_FE_WRITE_REQUEST)
                                    # construct the correct address (the address of the block to be replaced)
                                    m.d.sync += write_back_address.as_value().eq(
                                        Cat(
                                            C(0, unsigned(self.config.word_offset_width)),
                                            fe_address_view.index,
                                            tag_mem[replacement_policy.next_replacement_o][0].data
                                        )
                                    )
                                with m.Else():
                                    # full write -> no read block operation needed
                                    # write data to cache DUPLICATE CODE
                                    # TODO Think about whether writing data to the cache and optionally sending the write request
                                    # to the lower mem should only happen inside the execute fe write req state, in a function, or
                                    # if it should stay messy like this
                                    init_data_mem_write(replacement_policy.next_replacement_o, self.fe.address, self.fe.write_data, self.fe.write_strobe)
                                    if self.config.write_back:
                                        with m.If(dirty_mem[replacement_policy.next_replacement_o][fe_address_view.index]):
                                            # write back if dirty
                                            m.d.sync += state.eq(States.WRITE_BACK_BLOCK)
                                            # Construct the correct address
                                            m.d.sync += write_back_address.index.eq(fe_address_view.index)
                                            m.d.sync += write_back_address.tag.eq(tag_mem[replacement_policy.next_replacement_o][0].data)
                                            m.d.sync += write_back_address.word_offset.eq(0)
                                            m.d.sync += write_back_way.eq(replacement_policy.next_replacement_o)
                                            # Select data source and next state after write back
                                            m.d.sync += write_back_data_from_buffer.eq(0)
                                            m.d.sync += write_back_next_state.eq(States.EXECUTE_FE_WRITE_REQUEST)
                                            # Query data mem so that the write back state can use its data
                                            # clear the word offset so that the actual first word gets read.
                                            init_data_mem_read(replacement_policy.next_replacement_o, Cat(C(0, unsigned(self.config.word_offset_width)), fe_address_view.index))
                                        with m.Else():
                                            # We're done if the block is not dirty
                                            m.d.sync += state.eq(States.READY)
                                    else:
                                        # write to lower mem if write through
                                        send_fe_request_to_lower_mem(next_state=States.READY)
                            with m.Else():
                                # Handle read
                                m.d.sync += state.eq(States.READ_BLOCK)
                                m.d.sync += read_block_next_state.eq(
                                    Mux(
                                        self.config.write_back & dirty_mem[replacement_policy.next_replacement_o][fe_address_view.index],
                                        States.WRITE_BACK_BLOCK,
                                        States.READY
                                    )
                                )
                                # Write data_mem block to be replaced into a buffer should we need a write back
                                m.d.sync += evict_block_enable.eq(1)
                                m.d.sync += evict_block_address.as_value().eq(self.fe.address)
                                # Prepare things for the Write Back State should we transition to it
                                m.d.sync += write_back_data_from_buffer.eq(1)
                                m.d.sync += write_back_next_state.eq(States.READY)
                                # construct the correct address (the address of the block to be replaced)
                                m.d.sync += write_back_address.as_value().eq(
                                    Cat(
                                        C(0, unsigned(self.config.word_offset_width)),
                                        fe_address_view.index,
                                        tag_mem[replacement_policy.next_replacement_o][0].data
                                    )
                                )
            with m.Case(States.WRITE_BACK_BLOCK):
                # Write back the block specified by the respective registers
                m.d.sync += be_buffer_address.eq(write_back_address)
                m.d.sync += be_buffer_write_strobe.eq(-1)
                with m.If(write_back_data_from_buffer):
                    # take the data from the buffer
                    m.d.sync += be_buffer_write_data.eq(evicted_block_buffer[write_back_address.word_offset])
                with m.Else():
                    # take the data from the data memory
                    m.d.sync += be_buffer_write_data.eq(data_mem[write_back_way][0].data)
                    # data_mem read needs to be initiated by previous state
                    # -> we also need to initiate a new read
                    init_data_mem_read(write_back_way, write_back_address.as_value() + 1)
                m.d.sync += state.eq(States.SEND_MEM_REQUEST)
                # increment word offset of write back address
                m.d.sync += write_back_address.word_offset.eq(write_back_address.word_offset + 1)
                with m.If(write_back_address.word_offset == (self.config.block_size - 1)):
                    # This is the last word to write back -> proceed with the next state
                    m.d.sync += send_mem_request_next_state.eq(write_back_next_state)
                with m.Else():
                    # We're not done yet, come back after mem request has finished
                    m.d.sync += send_mem_request_next_state.eq(States.WRITE_BACK_BLOCK)
            with m.Case(States.SEND_MEM_REQUEST):
                # Wait for the lower memory to become ready
                with m.If(self.be.port_ready):
                    # Send request to lower memory
                    m.d.comb += self.be.request_valid.eq(1)
                    with m.If(be_buffer_write_strobe.any()):
                        # If it is a write, go to the next state
                        m.d.sync += state.eq(send_mem_request_next_state)
                    with m.Else():
                        # In case of a read, we have to write the be read data to the cache first
                        m.d.sync += state.eq(States.WRITE_BE_READ_DATA_TO_CACHE)
            with m.Case(States.WRITE_BE_READ_DATA_TO_CACHE):
                # First wait for the memory to respond
                with m.If(self.be.read_data_valid):
                    # The read request was processed, now write the data to the cache
                    init_data_mem_write(
                        next_block_replacement,
                        incremented_be_buffer_address,
                        self.be.read_data.word_select(be_address_incremented_cut_off_bits, self.config.data_width),
                        -1
                    )
                    # Determine if we should hand out the read data to the fe
                    with m.If(
                        (be_read_data_word_counter == 0)
                        & (~fe_buffer_write_strobe.any())
                        & (be_buffer_address.word_offset == fe_buffer_address.word_offset)
                    ):
                        # If we're seeing this word for the first time (be_read_data_word_counter == 0) and the fe request was a read request
                        # and the request was for the be word containing the word requested by the fe (be_buffer_address.word_offset == fe_buffer_address.word_offset)
                        # then hand out the data now
                        m.d.sync += fe_read_data_select_buffer.eq(1)
                        m.d.sync += fe_read_data_buffer.eq(self.be.read_data.word_select(be_address_incremented_cut_off_bits, self.config.data_width))
                        m.d.sync += self.fe.read_data_valid.eq(1)
                    # Now determine the next state
                    with m.If(be_read_data_word_counter == self.config.read_block_wc - 1):
                        # If we're done reading all words into the block, go to the next state
                        m.d.sync += state.eq(send_mem_request_next_state)
                        m.d.sync += be_read_data_word_counter.eq(0)
                    with m.Else():
                        # Else increase the counter
                        m.d.sync += be_read_data_word_counter.eq(be_read_data_word_counter + 1)
            with m.Case(States.READ_BLOCK):
                # Prepare a memory read request
                # Critical word first: Start at the word that was requested
                # So we can hand that out first if it was a read request
                m.d.sync += be_buffer_address.eq(fe_buffer_address)
                m.d.sync += be_buffer_address.word_offset.eq(fe_buffer_address.as_value() + read_block_word_offset)
                m.d.sync += be_buffer_write_strobe.eq(0)
                # increment word offset for the read block operation (shouldn't do anything bad if block_size == 1 or block_size == read_block_wc)
                m.d.sync += read_block_word_offset.eq(read_block_word_offset + self.config.read_block_wc)
                # determine the state that should be taken next or after the next send mem request operation
                is_last_read_block_operation = read_block_word_offset == self.config.block_size - self.config.read_block_wc
                # If it's not the last request needed, come back afterwards. Else go to the next state.
                state_after_read_block = Mux(is_last_read_block_operation, read_block_next_state, States.READ_BLOCK)
                # Send the memory request except for when its the address to which
                # we want to write anyway AND write strobe is all ones AND we would not
                # read any other byte from the word the BE would give is in this request (self.config.read_block_wc == 1)
                with m.If(~(
                            fe_buffer_write_strobe.all()
                            & (read_block_word_offset == 0)
                            & (self.config.read_block_wc == 1)
                        )
                    ):
                    m.d.sync += state.eq(States.SEND_MEM_REQUEST)
                    m.d.sync += send_mem_request_next_state.eq(state_after_read_block)
                with m.Elif(is_last_read_block_operation):
                    # If the memory request is not needed AND this the last word in the block,
                    # then we can go to the next state. Else stay in this state and continue
                    # with the next word (no state modification needed!)
                    m.d.sync += state.eq(state_after_read_block)
            with m.Case(States.EXECUTE_FE_WRITE_REQUEST):
                # Handle write request - this state is used after write back/read block operations
                # Write data to internal data_mem
                init_data_mem_write(next_block_replacement, fe_buffer_address, fe_buffer_write_data, fe_buffer_write_strobe)
                with m.If(self.config.write_back):
                    # We're done if using write back
                    m.d.sync += state.eq(States.READY)
                with m.Else():
                    # Send request to lower memory if write through
                    send_fe_buffer_request_to_lower_mem(States.READY)
            with m.Case(States.FLUSH_CACHE):
                with m.If(self.config.write_back):
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
                with m.If(flush_set_index == self.config.num_sets - 1):
                    m.d.sync += flush_block_index.eq(flush_block_index + 1)

                # Is this the last set in the last block?
                is_last_block = (flush_set_index == self.config.num_sets - 1) & (flush_block_index == self.config.num_ways - 1)
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
                    m.d.sync += write_back_data_from_buffer.eq(0)
                    # query the data memory so the write back state can access the data. It'll do that on its own for the following words.
                    init_data_mem_read(flush_block_index, Cat(C(0, shape=unsigned(self.config.word_offset_width)), flush_set_index))
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
