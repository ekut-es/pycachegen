from enum import Enum

from amaranth import Array, C, Cat, Module, Mux, Signal, unsigned
from amaranth.lib import data, wiring
from amaranth.lib.wiring import In, Out

from .cache_address import get_blockwise_incremented_address
from .cache_config import InternalCacheConfig
from .interfaces import (
    CacheStoreSignature,
    DirectorySignature,
    ReplacementPolicySignature,
)
from .utils import one_hot_encode


class States(Enum):
    READY = 0
    WRITE_BACK_BLOCK = 1
    READ_BLOCK = 2
    EXECUTE_FE_WRITE_REQUEST = 3
    SEND_MEM_REQUEST = 4
    FLUSH_CACHE = 5
    FLUSH_BACKEND = 6


class CacheController(wiring.Component):
    def __init__(self, config: InternalCacheConfig) -> None:
        """The heart of the cache: It processes requests and interacts with the other cache modules.

        Args:
            config (InternalCacheConfig): The cache configuration.
        """
        self.config = config

        super().__init__(
            {
                "fe": In(config.fe_signature),
                "hit_o": Out(1),
                "be": Out(config.be_signature),
                "store": Out(CacheStoreSignature(config)),
                "directory": Out(DirectorySignature(config)),
                "repl_pol": Out(ReplacementPolicySignature(config)),
            }
        )

    def elaborate(self, platform) -> Module:
        m = Module()

        config = self.config

        # replacement policy things
        # block to be replaced next for the set of the current fe_buffer_address
        next_block_replacement = Signal(range(config.num_ways))

        # frontend input buffers
        fe_buffer_address = Signal(config.address_layout)
        fe_buffer_write_data = Signal(config.data_width)
        fe_buffer_write_strobe = Signal(config.bytes_per_word)

        # backend output buffers
        # Create BE buffers that use our own data/address/write strobe widths
        # Then "shift" the data/write strobe into place in the real BE interface
        # according to the bits we cut off from the address
        be_buffer_write_data = Signal(unsigned(config.data_width))
        be_buffer_write_strobe = Signal(unsigned(config.bytes_per_word))
        be_buffer_address = Signal(config.address_layout)
        be_buffer_word_offset = be_buffer_address.as_value()[: config.address_width_difference]
        m.d.comb += [
            self.be.address.eq(be_buffer_address.as_value()[config.address_width_difference :]),
            self.be.write_data.eq(0),
            self.be.write_strobe.eq(0),
            self.be.write_data.word_select(be_buffer_word_offset, config.data_width).eq(be_buffer_write_data),
            self.be.write_strobe.word_select(be_buffer_word_offset, config.bytes_per_word).eq(be_buffer_write_strobe),
        ]

        # internal registers
        # FSM state
        state = Signal(States)
        # one bit per way to indicate a hit in that way
        hit_vector = Signal(unsigned(config.num_ways))
        # one hot encode the vector into this signal
        hit_index = one_hot_encode(m, hit_vector)
        # a view for convenient access to the tag/index/word offset bits
        fe_address_view = data.View(config.address_layout, self.fe.address)
        # Output port ready status based on current state
        m.d.comb += self.fe.port_ready.eq(state == States.READY)
        # Whether to hand the data in the buffer out or the data from the cache store
        fe_read_data_select_buffer = Signal()
        # Buffer that contains the data requested by the frontend
        fe_read_data_buffer = Signal(unsigned(config.data_width))
        # Use that index to assign the correct read data to the FE port
        m.d.comb += self.fe.read_data.eq(Mux(fe_read_data_select_buffer, fe_read_data_buffer, self.store.read_data))

        # States.READ_BLOCK
        # counter for how many read operations have been done so far
        read_block_read_counter = Signal(range(config.read_block_requests_needed + 1))
        # counter for how many words of the BE read data have been written back so far
        read_block_write_counter = Signal(config.be_word_multiplier_width)
        # the address for which a read request was issued
        read_block_previous_address = Signal(config.address_layout)
        # the address for the next write action (previous address incremented by write counter)
        read_block_write_address = Signal(config.address_layout)
        m.d.comb += read_block_write_address.eq(
            get_blockwise_incremented_address(
                read_block_previous_address, read_block_write_counter, m, config.be_word_multiplier_width
            )
        )
        # the word to be written back next
        read_block_write_address_word_offset = read_block_write_address.as_value()[: config.address_width_difference]
        read_block_write_data = Signal(config.data_width)
        m.d.comb += read_block_write_data.eq(
            self.be.read_data.word_select(read_block_write_address_word_offset, config.data_width)
        )
        # state that read block should take next
        read_block_next_state = Signal(States)

        # States.FLUSH_CACHE / States.FLUSH_BACKEND
        # index of the set to be flushed next
        flush_set_index = Signal(config.index_width)
        # index of the block that is currently being flushed
        flush_block_index = Signal(range(config.num_ways))
        # whether we already told the backend to flush itself
        be_flush_requested = Signal()

        # States.WRITE_BACK_BLOCK
        # address and way to identify the block to be written back
        write_back_address = Signal(config.address_layout)
        write_back_way = Signal(range(config.num_ways))
        # source of the data to write back.
        # 0: from cache store (read needs to be initiated before entering this state. way must also be specified)
        # 1: from write back buffer
        write_back_data_from_buffer = Signal()
        # state to take after the WRITE_BACK state
        write_back_next_state = Signal(States)

        # States.SEND_MEM_REQUEST
        # state to go to afterwards
        send_mem_request_next_state = Signal(States)

        # evict block operation puts data to be written back in this buffer
        evicted_block_buffer = Array(
            [Signal(unsigned(config.data_width), name=f"evicted_block_buffer_{i}") for i in range(config.block_size)]
        )
        # Enable signal to start the operation. Will get disabled once it's done.
        evict_block_enable = Signal()
        # The address of the block to write to the buffer
        evict_block_address = Signal(config.address_layout)
        # Counts how many cycles have passed since starting the operation
        evict_block_counter = Signal(range(config.block_size + 1))
        # The way in which to evict a block
        evict_block_way = Signal(range(config.num_ways))
        # Construct the address the same way that the read block operation does
        # so that we evict the block before it gets overwritten by the read block operation
        evict_block_incremented_address = Signal(config.address_layout)
        m.d.comb += evict_block_incremented_address.eq(
            get_blockwise_incremented_address(
                evict_block_address, evict_block_counter, m, config.be_word_multiplier_width
            )
        )
        # remember the previous word offset so we know in which slot of the buffer the read data belongs
        evict_block_previous_word_offset = Signal(config.word_offset_width)
        # the actual logic of the evict block operation
        with m.If(evict_block_enable):
            with m.If(evict_block_counter < config.block_size):
                # Send read request to cache store
                m.d.comb += [
                    self.store.read_request_valid.eq(1),
                    self.store.read_address.eq(evict_block_incremented_address),
                    self.store.read_way.eq(evict_block_way),
                ]
                # Store the address we just sent a request to
                m.d.sync += evict_block_previous_word_offset.eq(evict_block_incremented_address.word_offset)
                # Increment the total counter
                m.d.sync += evict_block_counter.eq(evict_block_counter + 1)

            with m.If(evict_block_counter > 0):
                # Write the previously requested word to the buffer
                m.d.sync += evicted_block_buffer[evict_block_previous_word_offset].eq(self.store.read_data)

            with m.If(evict_block_counter == config.block_size):
                # We're done, reset everything.
                m.d.sync += evict_block_enable.eq(0)
                m.d.sync += evict_block_counter.eq(0)

        def send_fe_buffer_request_to_lower_mem(next_state):
            """Send the request from the FE buffers to the lower memory."""
            m.d.comb += [
                self.be.request_valid.eq(1),
                be_buffer_address.eq(fe_buffer_address),
                be_buffer_write_data.eq(fe_buffer_write_data),
                be_buffer_write_strobe.eq(fe_buffer_write_strobe),
            ]
            with m.If(self.be.port_ready):
                m.d.sync += state.eq(next_state)
            with m.Else():
                m.d.sync += state.eq(States.SEND_MEM_REQUEST)
                m.d.sync += send_mem_request_next_state.eq(next_state)

        def send_fe_request_to_lower_mem(next_state):
            """Send the request from the FE to the lower memory."""
            m.d.comb += [
                self.be.request_valid.eq(1),
                be_buffer_address.eq(self.fe.address),
                be_buffer_write_data.eq(self.fe.write_data),
                be_buffer_write_strobe.eq(self.fe.write_strobe),
            ]
            with m.If(self.be.port_ready):
                m.d.sync += state.eq(next_state)
            with m.Else():
                m.d.sync += state.eq(States.SEND_MEM_REQUEST)
                m.d.sync += send_mem_request_next_state.eq(next_state)

        def prepare_block_write_back(next_state: States):
            """Prepare everything for writing back the block to be replaced by the frontend request.

            This includes starting the evict operation and configuring the registers for the write back operation. The
            transition to the write back block state has to be performed manually. The directory read also has to be
            performed manually. This function uses the repl_pol's current next_replacement_o, so the index for the
            repl_pol must be set manually.

            Args:
                next_state (States): State to transition to after write back.
            """
            m.d.sync += [
                # Write block from store to be replaced into a buffer should we need a write back
                evict_block_enable.eq(1),
                evict_block_address.as_value().eq(self.fe.address),
                evict_block_way.eq(self.repl_pol.next_replacement),
                # Prepare things for the Write Back State should we transition to it
                write_back_data_from_buffer.eq(1),
                write_back_next_state.eq(next_state),
                # construct the correct address (the address of the block to be replaced)
                write_back_address.as_value().eq(
                    Cat(
                        C(0, unsigned(config.word_offset_width)),
                        fe_address_view.index,
                        self.directory.tag(self.repl_pol.next_replacement),
                    )
                ),
            ]

        with m.Switch(state):
            with m.Case(States.READY):
                with m.If(self.fe.flush):
                    m.d.sync += state.eq(States.FLUSH_CACHE)
                    # Reset FE outputs
                    m.d.sync += [
                        self.fe.flush_done.eq(0),
                        self.fe.read_data_valid.eq(0),
                    ]
                with m.Elif(self.fe.request_valid):
                    # Reset FE outputs
                    m.d.sync += [
                        self.fe.flush_done.eq(0),
                        self.fe.read_data_valid.eq(0),
                    ]
                    # buffer inputs
                    m.d.sync += [
                        fe_buffer_address.eq(self.fe.address),
                        fe_buffer_write_strobe.eq(self.fe.write_strobe),
                        fe_buffer_write_data.eq(self.fe.write_data),
                    ]
                    # query directory and check whether we have a hit in any way
                    m.d.comb += self.directory.index.eq(fe_address_view.index)
                    m.d.comb += [
                        hit_vector[i].eq((self.directory.tag(i) == fe_address_view.tag) & self.directory.valid_bits[i])
                        for i in range(config.num_ways)
                    ]
                    # purely for statistics: let the outside know if we had a hit
                    m.d.sync += self.hit_o.eq(hit_vector.any())
                    # query replacement policy and buffer the next way to be replaced for this set
                    m.d.comb += self.repl_pol.set.eq(fe_address_view.index)
                    m.d.sync += next_block_replacement.eq(self.repl_pol.next_replacement)
                    with m.If(hit_vector.any()):
                        # We have a hit
                        # update the replacement policy state
                        m.d.comb += [
                            self.repl_pol.access.eq(1),
                            self.repl_pol.set.eq(fe_address_view.index),
                            self.repl_pol.way.eq(hit_index),
                        ]
                        with m.If(self.fe.write_strobe.any()):
                            # write data to cache
                            m.d.comb += [
                                self.store.write_request_valid.eq(1),
                                self.store.write_address.eq(self.fe.address),
                                self.store.write_way.eq(hit_index),
                                self.store.write_data.eq(self.fe.write_data),
                                self.store.byte_strobe.eq(self.fe.write_strobe),
                            ]
                            if config.write_back:
                                # mark dirty if write back
                                m.d.comb += [
                                    self.directory.data_dirty.eq(1),
                                    self.directory.update_dirty.eq(1),
                                    self.directory.write_way.eq(hit_index),
                                ]
                                m.d.sync += state.eq(States.READY)
                            else:
                                # write to lower mem if write through
                                send_fe_request_to_lower_mem(States.READY)
                        with m.Else():
                            # handle read
                            m.d.sync += [
                                state.eq(States.READY),
                                fe_read_data_select_buffer.eq(0),
                                self.fe.read_data_valid.eq(1),
                            ]
                            m.d.comb += [
                                self.store.read_request_valid.eq(1),
                                self.store.read_address.eq(self.fe.address),
                                self.store.read_way.eq(hit_index),
                            ]
                    with m.Else():
                        # We have a miss
                        with m.If((not config.write_allocate) & self.fe.write_strobe.any()):
                            # write miss and write no-allocate -> only write to lower memory
                            send_fe_request_to_lower_mem(States.READY)
                        with m.Else():
                            # In all other cases, we have to replace a block
                            # Update valid bit and tag
                            m.d.comb += [
                                # read index is already set correctly
                                # select way to be written to
                                self.directory.write_way.eq(self.repl_pol.next_replacement),
                                # update tag
                                self.directory.data_tag.eq(fe_address_view.tag),
                                self.directory.update_tag.eq(1),
                                # update valid bit
                                self.directory.data_valid.eq(1),
                                self.directory.update_valid.eq(1),
                            ]
                            # Also update dirty bit if write back
                            if config.write_back:
                                # Set dirty bit if write, else clear it
                                m.d.comb += [
                                    self.directory.data_dirty.eq(self.fe.write_strobe.any()),
                                    self.directory.update_dirty.eq(1),
                                ]
                            # find out whether we need a write back operation
                            write_back_needed = config.write_back & self.directory.dirty_bits.bit_select(
                                self.repl_pol.next_replacement, 1
                            )
                            # update the replacement policy
                            m.d.comb += [
                                self.repl_pol.access.eq(1),
                                self.repl_pol.replace.eq(1),
                                self.repl_pol.set.eq(fe_address_view.index),
                                self.repl_pol.way.eq(self.repl_pol.next_replacement),
                            ]
                            with m.If(self.fe.write_strobe.any()):
                                # Handle write
                                with m.If((~self.fe.write_strobe.all()) | (config.block_size > 1)):
                                    # partial write (doesn't overwrite the entire word or we just store multiple words
                                    # per block) -> we have to read in the block from the main memory first
                                    m.d.sync += state.eq(States.READ_BLOCK)
                                    with m.If(write_back_needed):
                                        m.d.sync += read_block_next_state.eq(States.WRITE_BACK_BLOCK)
                                        prepare_block_write_back(States.EXECUTE_FE_WRITE_REQUEST)
                                    with m.Else():
                                        m.d.sync += read_block_next_state.eq(States.EXECUTE_FE_WRITE_REQUEST)
                                with m.Else():
                                    # full write -> no read block operation needed
                                    if config.write_back:
                                        with m.If(
                                            self.directory.dirty_bits.bit_select(self.repl_pol.next_replacement, 1)
                                        ):
                                            m.d.sync += [
                                                # write back if dirty
                                                state.eq(States.WRITE_BACK_BLOCK),
                                                # Construct the correct address
                                                write_back_address.index.eq(fe_address_view.index),
                                                write_back_address.tag.eq(
                                                    self.directory.tag(self.repl_pol.next_replacement)
                                                ),
                                                write_back_address.word_offset.eq(0),
                                                write_back_way.eq(self.repl_pol.next_replacement),
                                                # Select data source and next state after write back
                                                write_back_data_from_buffer.eq(0),
                                                # the EXECUTE_FE_WRITE_REQUEST State will write the data to the cache
                                                write_back_next_state.eq(States.EXECUTE_FE_WRITE_REQUEST),
                                            ]
                                            # Query cache store so that the write back state can use its data
                                            # clear the word offset so that the actual first word gets read.
                                            m.d.comb += [
                                                self.store.read_request_valid.eq(1),
                                                self.store.read_address.eq(
                                                    Cat(
                                                        C(0, unsigned(config.word_offset_width)),
                                                        fe_address_view.index,
                                                    )
                                                ),
                                                self.store.read_way.eq(self.repl_pol.next_replacement),
                                            ]
                                        with m.Else():
                                            # Write the data to the cache and we're done if the block is not dirty
                                            m.d.sync += state.eq(States.READY)
                                            m.d.comb += [
                                                self.store.write_request_valid.eq(1),
                                                self.store.write_address.eq(self.fe.address),
                                                self.store.write_way.eq(self.repl_pol.next_replacement),
                                                self.store.write_data.eq(self.fe.write_data),
                                                self.store.byte_strobe.eq(self.fe.write_strobe),
                                            ]
                                    else:
                                        # write to cache and to lower mem if write through
                                        # (write through + no-allocate was caught earlier)
                                        send_fe_request_to_lower_mem(States.READY)
                                        m.d.comb += [
                                            self.store.write_request_valid.eq(1),
                                            self.store.write_address.eq(self.fe.address),
                                            self.store.write_way.eq(self.repl_pol.next_replacement),
                                            self.store.write_data.eq(self.fe.write_data),
                                            self.store.byte_strobe.eq(self.fe.write_strobe),
                                        ]
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
                # If we should take the data from the evict buffer then check that the evict block operation is done
                # (it should always be done for normal write backs but might not be for flush write backs)
                with m.If((~(write_back_data_from_buffer & evict_block_enable))):
                    # Write back the block specified by the respective registers
                    m.d.comb += [
                        self.be.request_valid.eq(1),
                        be_buffer_address.eq(write_back_address),
                    ]
                    with m.If(write_back_data_from_buffer):
                        # write back all the data in the evict buffer
                        # we can write multiple words at once if our block size is greater than 1 and
                        # if the BE data width allows it
                        m.d.comb += self.be.write_data.eq(
                            Cat(
                                [
                                    evicted_block_buffer[write_back_address.word_offset + i]
                                    for i in range(config.be_word_multiplier)
                                ]
                            )
                            << (config.data_width * write_back_address.as_value()[: -config.be_address_width])
                        )
                        m.d.comb += self.be.write_strobe.eq(
                            (2 ** (config.bytes_per_word * config.be_word_multiplier) - 1)
                            << (config.bytes_per_word * write_back_address.as_value()[: -config.be_address_width])
                        )
                    with m.Else():
                        # take the data from the cache store and write it and the write strobe to the BE buffers
                        m.d.comb += [
                            be_buffer_write_data.eq(self.store.read_data),
                            be_buffer_write_strobe.eq(-1),
                        ]
                    with m.If(self.be.port_ready):
                        with m.If(write_back_data_from_buffer):
                            # increment word offset of write back address
                            m.d.sync += write_back_address.word_offset.eq(
                                write_back_address.word_offset + config.be_word_multiplier
                            )
                            with m.If(
                                write_back_address.word_offset == (config.block_size - config.be_word_multiplier)
                            ):
                                # This is the last word to write back -> proceed with the next state
                                m.d.sync += state.eq(write_back_next_state)
                        with m.Else():
                            m.d.sync += state.eq(write_back_next_state)
            with m.Case(States.READ_BLOCK):
                # wait until the memory gets ready and (all words of previous request were written to the cache or this
                # is the first request) and we have not already issued all needed requests
                with m.If(
                    ((read_block_write_counter == (config.be_word_multiplier - 1)) | (read_block_read_counter == 0))
                    & (read_block_read_counter < config.read_block_requests_needed)
                ):
                    # Issue a memory read request
                    # Critical word first: Start at the word that was requested
                    # So we can hand that out first if it was a read request
                    m.d.comb += [
                        self.be.request_valid.eq(1),
                        be_buffer_write_strobe.eq(0),
                        be_buffer_address.eq(fe_buffer_address),
                    ]
                    # construct the correct word offset and increment the word offset for the next request
                    with m.If(
                        fe_buffer_write_strobe.all() & (read_block_read_counter == 0) & (config.be_word_multiplier == 1)
                    ):
                        # If the FE completely overwrites all the words that we'd get from the current request, we can
                        # skip it. (this is only the case if write strobe is all ones, we'd only get one word out of
                        # the request and the current request targets the same word as the FE address)
                        with m.If(self.be.port_ready):
                            m.d.sync += read_block_read_counter.eq(read_block_read_counter + 2)
                        m.d.comb += be_buffer_address.word_offset.eq(fe_buffer_address.as_value() + 1)
                    with m.Else():
                        # Else just increment the word offset by the amount of words we can retrieve from one BE word
                        with m.If(self.be.port_ready):
                            m.d.sync += read_block_read_counter.eq(read_block_read_counter + 1)
                        m.d.comb += be_buffer_address.word_offset.eq(
                            fe_buffer_address.as_value() + read_block_read_counter * config.be_word_multiplier
                        )

                    with m.If(self.be.port_ready):
                        # store the address so that we still have it when writing the words to the cache
                        m.d.sync += read_block_previous_address.eq(be_buffer_address.as_value())

                with m.If(self.be.read_data_valid & (read_block_read_counter != 0)):
                    # A read request was processed, write the data to the cache
                    m.d.comb += [
                        self.store.write_request_valid.eq(1),
                        self.store.write_address.eq(read_block_write_address),
                        self.store.write_way.eq(next_block_replacement),
                        self.store.write_data.eq(read_block_write_data),
                        self.store.byte_strobe.eq(-1),
                    ]
                    # increment write counter
                    m.d.sync += read_block_write_counter.eq(read_block_write_counter + 1)

                    # determine if we should hand out the read data to the FE
                    with m.If(
                        (read_block_read_counter == 1)  # it was the first read request to the BE
                        & (~fe_buffer_write_strobe.any())  # the FE sent a read request
                        & (read_block_write_counter == 0)  # This is the first cycle after the read data is valid
                    ):
                        m.d.sync += [
                            fe_read_data_select_buffer.eq(1),
                            fe_read_data_buffer.eq(read_block_write_data),
                            self.fe.read_data_valid.eq(1),
                        ]

                    with m.If(
                        (read_block_write_counter == (config.be_word_multiplier - 1))
                        & (read_block_read_counter == config.read_block_requests_needed)
                    ):
                        # go to the next state if no more read requests are needed and if we've written all words of
                        # the last request to the cache
                        m.d.sync += state.eq(read_block_next_state)
                        # also reset the read counter (the write counter has appropriate width and doesn't need a reset)
                        m.d.sync += read_block_read_counter.eq(0)
            with m.Case(States.EXECUTE_FE_WRITE_REQUEST):
                # Handle write request - this state is used after write back/read block operations
                # Write data to cache store
                m.d.comb += [
                    self.store.write_request_valid.eq(1),
                    self.store.write_address.eq(fe_buffer_address),
                    self.store.write_way.eq(next_block_replacement),
                    self.store.write_data.eq(fe_buffer_write_data),
                    self.store.byte_strobe.eq(fe_buffer_write_strobe),
                ]
                with m.If(config.write_back):
                    # We're done if using write back
                    m.d.sync += state.eq(States.READY)
                with m.Else():
                    # Send request to lower memory if write through
                    send_fe_buffer_request_to_lower_mem(States.READY)
            with m.Case(States.SEND_MEM_REQUEST):
                send_fe_buffer_request_to_lower_mem(send_mem_request_next_state)
            with m.Case(States.FLUSH_CACHE):
                with m.If(not config.write_back):
                    # If write back is not used, simply flush the back end
                    m.d.sync += state.eq(States.FLUSH_BACKEND)
                with m.Else():
                    # Increment set/block indices
                    m.d.sync += flush_set_index.eq(flush_set_index + 1)
                    with m.If(flush_set_index == config.num_sets - 1):
                        m.d.sync += flush_block_index.eq(flush_block_index + 1)

                    # Is this the last set in the last block?
                    is_last_block = (flush_set_index == config.num_sets - 1) & (
                        flush_block_index == config.num_ways - 1
                    )
                    # Determine the next state/the next state after write back
                    next_state = Mux(is_last_block, States.FLUSH_BACKEND, States.FLUSH_CACHE)

                    # query directory for valid/dirty bits
                    m.d.comb += self.directory.index.eq(flush_set_index)

                    with m.If(
                        self.directory.dirty_bits.bit_select(flush_block_index, 1)
                        & self.directory.valid_bits.bit_select(flush_block_index, 1)
                    ):
                        m.d.sync += [
                            # Start a evict block operation so that the write back state can take multiple words out of
                            # the evict data buffer
                            evict_block_enable.eq(1),
                            evict_block_address.index.eq(flush_set_index),  # tag is not needed for evict block
                            evict_block_address.word_offset.eq(0),
                            evict_block_way.eq(flush_block_index),
                            # Prepare things for the Write Back State
                            write_back_data_from_buffer.eq(1),
                            write_back_next_state.eq(next_state),
                            write_back_address.tag.eq(self.directory.tag(flush_block_index)),
                            write_back_address.index.eq(flush_set_index),
                            write_back_address.word_offset.eq(0),
                            # transition to write back state (it will wait until the evict block operation is done)
                            state.eq(States.WRITE_BACK_BLOCK),
                            write_back_next_state.eq(next_state),
                        ]
                        m.d.comb += [
                            # Select the way that is being flushed
                            self.directory.write_way.eq(flush_block_index),
                            # Clear dirty bit
                            self.directory.data_dirty.eq(0),
                            self.directory.update_dirty.eq(1),
                        ]
                    with m.Else():
                        # Block doesn't need to be written back
                        m.d.sync += state.eq(next_state)
            with m.Case(States.FLUSH_BACKEND):
                with m.If(~be_flush_requested):
                    with m.If(self.be.flush_done):
                        # We haven't yet requested a flush, but the BE is already done flushing. This means that we
                        # either didn't write anything to the BE (in which case nothing is dirty) or the BE is not a
                        # cache (in which case nothing ever needs to be flushed in the BE), so we're done
                        m.d.sync += [
                            state.eq(States.READY),
                            self.fe.flush_done.eq(1),
                        ]
                    with m.Else():
                        # request a flush from the BE
                        m.d.comb += self.be.flush.eq(1)
                        with m.If(self.be.port_ready):
                            # the BE accepted the flush request
                            m.d.sync += be_flush_requested.eq(1)
                with m.Elif(self.be.flush_done):
                    # the BE is done flushing
                    m.d.sync += [
                        state.eq(States.READY),
                        be_flush_requested.eq(0),
                        self.fe.flush_done.eq(1),
                    ]

        return m
