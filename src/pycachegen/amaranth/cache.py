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
        state = Signal(States)
        send_mem_request_next_state = Signal(States)
        latency_counter = Signal(
            range(max(self.config.HIT_LATENCY, self.config.MISS_LATENCY))
        )
        hit_vector = Signal(unsigned(self.config.NUM_WAYS))
        m.d.comb += self.hit_o.eq(hit_vector.any())
        hit_index = Signal(unsigned(self.index_width))
        m.submodules.hit_index_encoder = hit_index_encoder = coding.Encoder(hit_vector.shape().width)
        m.d.comb += hit_index_encoder.i.eq(hit_vector)
        m.d.comb += hit_index.eq(hit_index_encoder.o)
        fe_address_view = data.View(self.fe_signature, self.fe.address)

        # Create be buffers that use our own data/address/write strobe widths
        # Then shift the data/write strobe into place in the real be interface
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
        for i in range(self.config.NUM_WAYS):
            new_mem = Memory(shape=unsigned(1), depth=self.config.NUM_SETS)
            m.submodules["valid_mem_{i}"] = new_mem
            valid_mem.append((new_mem.read_port(), new_mem.write_port()))
        dirty_mem = Array()
        for i in range(self.config.NUM_WAYS):
            new_mem = Memory(shape=unsigned(1), depth=self.config.NUM_SETS)
            m.submodules["dirty_mem_{i}"] = new_mem
            dirty_mem.append((new_mem.read_port(), new_mem.write_port()))
        tag_mem = Array()
        for i in range(self.config.NUM_WAYS):
            new_mem = Memory(shape=unsigned(self.tag_width), depth=self.config.NUM_SETS)
            m.submodules["tag_mem_{i}"] = new_mem
            tag_mem.append((new_mem.read_port(), new_mem.write_port()))
        data_mem = Array()
        for i in range(self.config.NUM_WAYS):
            new_mem = Memory(
                shape=unsigned(self.config.DATA_WIDTH), depth=self.config.NUM_SETS*self.config.BLOCK_SIZE
            )
            m.submodules["data_mem_{i}"] = new_mem
            data_mem.append(
                (
                    new_mem.read_port(),
                    new_mem.write_port(granularity=self.config.BYTE_SIZE),
                )
            )


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
                    for i in range(self.NUM_WAYS):
                        m.d.sync += valid_mem[i][0].addr.eq(fe_address_view.index)
                        m.d.sync += valid_mem[i][0].en.eq(1)
                        m.d.sync += tag_mem[i][0].addr.eq(fe_address_view.index)
                        m.d.sync += tag_mem[i][0].en.eq(1)
            with m.Case(States.HIT_LOOKUP):
                m.d.sync += state.eq(States.HIT_LOOKUP_DONE)
                m.d.sync += latency_counter.eq(latency_counter + 1)
                # stop querying valid and tag memories
                for i in range(self.NUM_WAYS):
                    m.d.sync += valid_mem[i][0].en.eq(0)
                    m.d.sync += tag_mem[i][0].en.eq(0)
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
                        m.d.sync += data_mem[hit_index][1].en.eq(fe_buffer_write_strobe)
                        m.d.sync += data_mem[hit_index][1].address.eq(Cat(fe_address_view.word_offset, fe_address_view.index))
                        m.d.sync += data_mem[hit_index][1].data.eq(fe_buffer_write_data)
                        if self.config.WRITE_BACK:
                            # mark dirty if write back
                            m.d.sync += dirty_mem[hit_index][1].en.eq(1)
                            m.d.sync += dirty_mem[hit_index][1].address.eq(fe_address_view.index)
                            m.d.sync += dirty_mem[hit_index][1].data.eq(1)
                            m.d.sync += state.eq(States.STALL)
                        else:
                            # write to lower mem if write through
                            m.d.sync += be_buffer_address.eq(fe_buffer_address)
                            m.d.sync += be_buffer_write_data.eq(fe_buffer_write_data)
                            m.d.sync += be_buffer_write_strobe.eq(fe_buffer_write_strobe)
                            m.d.sync += state.eq(States.SEND_MEM_REQUEST)
                            m.d.sync += send_mem_request_next_state.eq(States.STALL)
                    with m.Else():
                        # TODO Handle read
                        ...
                with m.Else():
                    # TODO Handle miss
                    ...
