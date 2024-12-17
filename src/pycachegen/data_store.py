from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out
from amaranth.lib.memory import Memory
from amaranth.utils import exact_log2

from pycachegen.cache_config_validation import InternalCacheConfig


class DataStore(wiring.Component):
    def __init__(self, config: InternalCacheConfig):
        self.depth = config.num_sets * config.block_size * config.num_ways
        self.address_width = exact_log2(config.num_sets) + exact_log2(config.block_size)
        self.module_name = config.data_mem_module
        self.data_width = config.data_width
        self.byte_size = config.byte_size
        super().__init__(
            {
                "request_valid": In(1),
                "address": In(self.address_width),
                "way": In(exact_log2(config.num_ways)),
                "write_data": In(config.data_width),
                "byte_strobe": In(config.bytes_per_word),
                "read_data": Out(config.data_width),
            }
        )

    def init_read(self, way, addr):
        """Initiate read from m.d.comb.

        Args:
            way: The way to access.
            addr: The address consists of the word offset and set index bits.
        """
        self.m.d.comb += self.request_valid.eq(1)
        self.m.d.comb += self.address.eq(Cat(addr, way))

    def init_write(self, way, addr, data, byte_strobe):
        """Initiate write to data memory from m.d.comb.

        Args:
            way: The way to access.
            addr: The address consists of the word offset and set index bits.
            data: The data to write to the memory.
            byte_strobe: The byte strobe signal.
        """
        self.m.d.comb += self.request_valid.eq(1)
        self.m.d.comb += self.address.eq(Cat(addr, way))
        self.m.d.comb += self.byte_strobe.eq(byte_strobe)
        self.m.d.comb += self.write_data.eq(data)

    def elaborate(self, platform):
        m = Module()

        total_address = Signal(unsigned(self.address.width + self.way.width))
        m.d.comb += total_address.eq(Cat(self.address, self.way))

        if self.module_name:
            # Extend byte strobe to bit strobe
            bit_strobe = Signal(self.data_width)
            for i, bit in enumerate(self.byte_strobe):
                m.d.comb += bit_strobe.word_select(i, self.byte_size).eq(Mux(bit, -1, 0))

            # Use an external Memory module
            m.submodules.memory = Instance(
                type=self.module_name,
                i_clk=ClockSignal(),
                i_rst=ResetSignal(),
                i_address=total_address,
                i_bit_strobe=bit_strobe,
                i_write_data=self.write_data,
                i_request_valid=self.request_valid,
                o_read_data=self.read_data,
            )
        else:
            # Create an Amaranth Memory
            m.submodules.memory = memory = Memory(
                shape=unsigned(self.data_width), depth=self.depth, init=[]
            )
            read_port = memory.read_port()
            write_port = memory.write_port(granularity=1)
            m.d.comb += read_port.addr.eq(total_address)
            m.d.comb += write_port.addr.eq(total_address)
            m.d.comb += self.data_mem_read_data.eq(read_port.data)
            m.d.comb += write_port.data.eq(self.write_data)
            m.d.comb += read_port.en.eq(self.data_mem_req_valid & (~self.bit_strobe.any()))
            m.d.comb += write_port.en.eq(Mux(self.data_mem_req_valid, bit_strobe, 0))


        return m
