from math import log2
from enum import Enum
from amaranth import *
from amaranth.lib import wiring, data, coding
from amaranth.lib.memory import Memory, ReadPort, WritePort
from amaranth.lib.wiring import In, Out
from pycachegen.cache_config_validation import InternalCacheConfig
from pycachegen.amaranth.memory_bus import MemoryBusSignature, MemoryBusInterface
from pycachegen.amaranth.cache_address import CacheAddressLayout


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


class Cache(wiring.Component):
    def __init__(self, config: InternalCacheConfig) -> None:
        self.config = config
        self.bytes_per_word = config.DATA_WIDTH // config.BYTE_SIZE
        self.be_bytes_per_word = config.BE_DATA_WIDTH // config.BYTE_SIZE
        self.index_width = int(log2(config.NUM_SETS))
        self.word_offset_width = int(log2(config.BLOCK_SIZE))
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
        super().__init__(
            {
                "fe": In(self.fe_signature),
                "flush_i": In(1),
                "hit_o": Out(1),
                "flush_done_o": Out(1),
                "be": Out(self.be_signature),
                "flush_o": Out(1),
                "flush_done_i": In(1),
            }
        )

    # fmt: off
    def elaborate(self, platform) -> Module:
        m = Module()
        ## input buffers
        fe_buffer_address = Signal(
            CacheAddressLayout(
                index_width=self.index_width,
                tag_width=self.tag_width,
                word_offset_width=self.word_offset_width,
            )
        )
        fe_buffer_write_data = Signal(self.config.DATA_WIDTH)
        fe_buffer_write_strobe = Signal(self.bytes_per_word)
        fe_buffer_flush = Signal(1)
        ## internal registers
        # FSM state
        state = Signal(States)
        # FSM state that will be taken after the SEND_MEM_REQUEST state
        send_mem_request_next_state = Signal(States)
        # register for counting the time it took to execute a request
        latency_counter = Signal(
            range(max(self.config.HIT_LATENCY, self.config.MISS_LATENCY))
        )
        # one bit per way to indicate a hit in that way
        hit_vector = Signal(unsigned(self.config.NUM_WAYS))
        # purely for statistics: let the outside know if we had a hit
        m.d.comb += self.hit_o.eq(hit_vector.any())
        # one hot encode the vector into this signal
        hit_index = Signal(unsigned(range(self.config.NUM_WAYS)))
        m.submodules.hit_index_encoder = hit_index_encoder = coding.Encoder(hit_vector.shape().width)
        m.d.comb += hit_index_encoder.i.eq(hit_vector)
        m.d.comb += hit_index.eq(hit_index_encoder.o)
        # a view for convenient access to the tag/index/word offset bits
        fe_address_view = data.View(self.fe_signature, self.fe.address)
        # block to be replaced next
        next_block_replacement = Signal(unsigned(range(self.config.NUM_WAYS)))

        # Create be buffers that use our own data/address/write strobe widths
        # Then "shift" the data/write strobe into place in the real be interface
        # according to the bits we cut off from the address
        be_buffer_write_data = Signal(unsigned(self.config.DATA_WIDTH))
        be_buffer_write_strobe = Signal(unsigned(self.bytes_per_word))
        be_buffer_address = Signal(unsigned(self.config.ADDRESS_WIDTH))
        m.d.comb += self.be.address.eq(be_buffer_address[-self.config.BE_ADDRESS_WIDTH : ])
        m.d.comb += self.be.write_data.eq(0)
        m.d.comb += self.be.write_strobe.eq(0)
        m.d.comb += self.be.write_data.word_select(be_buffer_address[:-self.config.BE_ADDRESS_WIDTH], self.config.DATA_WIDTH).eq(be_buffer_write_data)
        m.d.comb += self.be.write_strobe.word_select(be_buffer_address[:-self.config.BE_ADDRESS_WIDTH], self.bytes_per_word).eq(be_buffer_write_strobe)

        # Create valid, dirty, tag, data memories - one per way
        # usage: valid_mem[way][index], tag_mem[way][index], data_mem[way][Cat(word_offset, index)]
        # data memory contains values that represent whole blocks (potentially multiple words!)
        valid_mem = Array()
        dirty_mem = Array()
        tag_mem = Array()
        data_mem = Array()
        for i in range(self.config.NUM_WAYS):
            new_valid_mem = Memory(shape=unsigned(1), depth=self.config.NUM_SETS)
            m.submodules["valid_mem_{i}"] = new_valid_mem
            valid_mem.append((new_valid_mem.read_port(), new_valid_mem.write_port()))

            new_dirty_mem = Memory(shape=unsigned(1), depth=self.config.NUM_SETS)
            m.submodules["dirty_mem_{i}"] = new_dirty_mem
            dirty_mem.append((new_dirty_mem.read_port(), new_dirty_mem.write_port()))

            new_tag_mem = Memory(shape=unsigned(self.tag_width), depth=self.config.NUM_SETS)
            m.submodules["tag_mem_{i}"] = new_tag_mem
            tag_mem.append((new_tag_mem.read_port(), new_tag_mem.write_port()))

            new_data_mem = Memory(
                shape=unsigned(self.config.DATA_WIDTH), depth=self.config.NUM_SETS*self.config.BLOCK_SIZE
            )
            m.submodules["data_mem_{i}"] = new_data_mem
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
        write_back_address = Signal(
            CacheAddressLayout(
                index_width=self.index_width,
                tag_width=self.tag_width,
                word_offset_width=self.word_offset_width,
            )
        )
        write_back_way = Signal(unsigned(range(self.config.NUM_WAYS)))
        # state to take after the WRITE_BACK state
        write_back_next_state = Signal(States)


        def send_buffered_request_to_lower_mem(next_state: States):
            """Uses the buffered inputs to send a request to the lower memory.
            Goes to the SEND_MEM_REQUEST state to do so.
            """
            m.d.sync += be_buffer_address.eq(fe_buffer_address)
            m.d.sync += be_buffer_write_data.eq(fe_buffer_write_data)
            m.d.sync += be_buffer_write_strobe.eq(fe_buffer_write_strobe)
            m.d.sync += state.eq(States.SEND_MEM_REQUEST)
            m.d.sync += send_mem_request_next_state.eq(next_state)

        with m.Switch(state):
            with m.Case(States.READY):
                with m.If(self.fe.flush | fe_buffer_flush):
                    m.d.sync += state.eq(States.FLUSH_CACHE)
                with m.Elif(self.fe.request_valid):
                    m.d.sync += state.eq(States.HIT_LOOKUP)
                    m.d.sync += latency_counter.eq(latency_counter + 1)
                    # Reset fe outputs
                    m.d.sync += self.fe.read_data_valid.eq(0)
                    m.d.sync += self.fe.flush_done.eq(0)
                    # buffer inputs
                    m.d.sync += fe_buffer_address.eq(self.fe.address)
                    m.d.sync += fe_buffer_write_strobe.eq(self.fe.write_strobe)
                    m.d.sync += fe_buffer_write_data.eq(self.fe.write_data)
                    # query valid and tag memories
                    # this needs to happen in m.d.comb so that the address gets set
                    # BEFORE the positive clk edge that triggers any sync statements
                    for i in range(self.NUM_WAYS):
                        m.d.comb += valid_mem[i][0].addr.eq(fe_address_view.index)
                        m.d.comb += tag_mem[i][0].addr.eq(fe_address_view.index)
            with m.Case(States.HIT_LOOKUP):
                m.d.sync += state.eq(States.HIT_LOOKUP_DONE)
                m.d.sync += latency_counter.eq(latency_counter + 1)
                # check whether we have a hit in any way
                for i in range(self.config.NUM_WAYS):
                    m.d.sync += hit_vector[i].eq(
                        (tag_mem[i][0].data == fe_buffer_address.tag)
                        & valid_mem[i][0].data
                    )
            with m.Case(States.HIT_LOOKUP_DONE):
                m.d.sync += latency_counter.eq(latency_counter + 1)
                with m.If(hit_vector.any()):
                    # We have a hit
                    # TODO update the replacement policy state
                    with m.If(fe_buffer_write_strobe.any()):
                        # handle write
                        m.d.comb += data_mem[hit_index][1].en.eq(fe_buffer_write_strobe)
                        m.d.comb += data_mem[hit_index][1].addr.eq(Cat(fe_address_view.word_offset, fe_address_view.index))
                        m.d.comb += data_mem[hit_index][1].data.eq(fe_buffer_write_data)
                        if self.config.WRITE_BACK:
                            # mark dirty if write back
                            m.d.comb += dirty_mem[hit_index][1].en.eq(1)
                            m.d.comb += dirty_mem[hit_index][1].addr.eq(fe_address_view.index)
                            m.d.comb += dirty_mem[hit_index][1].data.eq(1)
                            m.d.sync += state.eq(States.STALL)
                        else:
                            # write to lower mem if write through
                            send_buffered_request_to_lower_mem(next_state=States.STALL)
                    with m.Else():
                        # handle read
                        m.d.sync += state.eq(States.STALL)
                        # FIXME read not initiatet, .data forgotten
                        self.fe.read_data.eq(data_mem[hit_index][Cat(fe_address_view.word_offset, fe_address_view.index)])
                with m.Else():
                    # Handle miss
                    with m.If((not self.config.WRITE_ALLOCATE) & fe_buffer_write_strobe.any()):
                        # write miss and write no-allocate -> only write to lower memory
                        send_buffered_request_to_lower_mem(next_state=States.STALL)
                    with m.Else():
                        # It's a miss and we have to replace a block

                        # determine the state that will be taken next (or after write back)
                        # If it's a read or if not all bytes of the block are being written to
                        # (because the write strobe is not all ones or becaues there is more than
                        # one word in the block) we need to perform a read block operation afterwards
                        read_block_operation_needed = (~fe_buffer_write_strobe).any() | (self.config.BLOCK_SIZE > 1)
                        next_state = Mux(read_block_operation_needed, States.READ_BLOCK, States.READ_BLOCK_DONE)
                        # Update valid/dirty/tag memories
                        m.d.comb += valid_mem[hit_index][1].en.eq(1)
                        m.d.comb += valid_mem[hit_index][1].addr.eq(fe_buffer_address.index)
                        m.d.comb += valid_mem[hit_index][1].data.eq(1)
                        m.d.comb += tag_mem[hit_index][1].en.eq(1)
                        m.d.comb += tag_mem[hit_index][1].addr.eq(fe_buffer_address.index)
                        m.d.comb += tag_mem[hit_index][1].data.eq(fe_buffer_address.tag)
                        if self.config.WRITE_BACK:
                            m.d.comb += dirty_mem[hit_index][1].en.eq(1)
                            m.d.comb += dirty_mem[hit_index][1].addr.eq(fe_buffer_address.index)
                            m.d.comb += dirty_mem[hit_index][1].data.eq(1)
                        # TODO update the replacement policy
                        # TODO initiate read from dirty memories in the previous state
                        with m.If(self.config.WRITE_BACK & dirty_mem[next_block_replacement][0].data):
                            # We have to write back the block to be replaced first because its dirty
                            m.d.sync += state.eq(States.WRITE_BACK_BLOCK)
                            m.d.sync += write_back_address.eq(fe_buffer_address)
                            m.d.sync += write_back_address.word_offset.eq(0) # start at the first word
                            m.d.sync += write_back_way.eq(next_block_replacement)
                            m.d.sync += write_back_next_state.eq(next_state)
                        with m.Else():
                            # No write back needed
                            m.d.sync += state.eq(next_state)
            with m.Case(States.WRITE_BACK_BLOCK):
                # Write back the block specified by the respective registers
                # initiate a read from the data memory. tell the SEND_MEM_REQUEST
                # state that it should use the data from there
                m.d.comb += data_mem[write_back_way][0].en.eq(1)
                m.d.comb += data_mem[write_back_way][0].address.eq(write_back_address)
                m.d.sync += latency_counter.eq(latency_counter + 1)
                m.d.sync += be_buffer_address.eq(write_back_address)
                m.d.sync += be_buffer_write_strobe.eq(-1) # NOTE This might not work
                m.d.sync += state(States.SEND_MEM_REQUEST)
                with m.If(write_back_address.word_offset == (self.config.BLOCK_SIZE - 1)):
                    # This is the last word to write back
                    m.d.sync += send_mem_request_next_state.eq(write_back_next_state)
                with m.Else():
                    # We're not done yet, come back after mem request has finished
                    m.d.sync += send_mem_request_next_state.eq(States.WRITE_BACK_BLOCK)
            with m.Case(States.SEND_MEM_REQUEST):
                ...
