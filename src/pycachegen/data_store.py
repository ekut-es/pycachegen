from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out
from amaranth.lib.memory import Memory
from amaranth.utils import exact_log2

from pycachegen.cache_config_validation import InternalCacheConfig


class DataStore(wiring.Component):
    def __init__(self, config: InternalCacheConfig, m: Module):
        """Module for storing the actual data of the cache. Provides methods for
        creating requests from the specified module `m`.

        This module uses a single dual port memory.

        Args:
            config (InternalCacheConfig): The cache config.
            m (Module): The module that instantiates this module.
        """
        self.depth = config.num_sets * config.block_size * config.num_ways
        self.address_width = exact_log2(config.num_sets) + exact_log2(config.block_size)
        self.total_address_width = self.address_width + exact_log2(config.num_ways)
        self.module_name = config.data_memory_module
        self.data_width = config.data_width
        self.byte_size = config.byte_size
        self.m = m
        super().__init__(
            {
                "read_request_valid": In(1),
                "read_address": In(self.address_width),
                "read_way": In(exact_log2(config.num_ways)),
                "read_data": Out(config.data_width),
                "write_request_valid": In(1),
                "write_address": In(self.address_width),
                "write_way": In(exact_log2(config.num_ways)),
                "write_data": In(config.data_width),
                "byte_strobe": In(config.bytes_per_word),
            }
        )

    def init_read(self, way, addr):
        """Initiate read from m.d.comb.

        Args:
            way: The way to access.
            addr: The address consists of the word offset and set index bits.
        """
        self.m.d.comb += self.read_request_valid.eq(1)
        self.m.d.comb += self.read_address.eq(addr)
        self.m.d.comb += self.read_way.eq(way)

    def init_write(self, way, addr, data, byte_strobe):
        """Initiate write to data memory from m.d.comb.

        Args:
            way: The way to access.
            addr: The address consists of the word offset and set index bits.
            data: The data to write to the memory.
            byte_strobe: The byte strobe signal.
        """
        self.m.d.comb += self.write_request_valid.eq(1)
        self.m.d.comb += self.write_address.eq(addr)
        self.m.d.comb += self.write_way.eq(way)
        self.m.d.comb += self.write_data.eq(data)
        self.m.d.comb += self.byte_strobe.eq(byte_strobe)

    def elaborate(self, platform):
        m = Module()

        # the given addresses are only "real addresses" and do not
        # include any information about the way to be accessed
        # Concatenate the address and the way to get the total address for the memory
        total_read_address = Signal(unsigned(self.total_address_width))
        m.d.comb += total_read_address.eq(Cat(self.read_address, self.read_way))
        total_write_address = Signal(unsigned(self.total_address_width))
        m.d.comb += total_write_address.eq(Cat(self.write_address, self.write_way))

        if self.module_name:
            # Extend byte strobe to bit strobe
            bit_strobe = Signal(self.data_width)
            for i, bit in enumerate(self.byte_strobe):
                m.d.comb += bit_strobe.word_select(i, self.byte_size).eq(
                    Mux(bit, -1, 0)
                )

            # Use an external Memory module
            m.submodules.memory = Instance(
                type=self.module_name,
                i_clk=ClockSignal(),
                i_rst=ResetSignal(),
                i_read_request_valid=self.read_request_valid,
                i_read_address=total_read_address,
                o_read_data=self.read_data,
                i_write_request_valid=self.read_request_valid,
                i_write_address=total_write_address,
                i_write_data=self.write_data,
                i_bit_strobe=bit_strobe,
            )
        else:
            # Create an Amaranth Memory
            m.submodules.memory = memory = Memory(
                shape=unsigned(self.data_width), depth=self.depth, init=[]
            )
            read_port = memory.read_port()
            m.d.comb += read_port.addr.eq(total_read_address)
            m.d.comb += self.read_data.eq(read_port.data)
            m.d.comb += read_port.en.eq(self.read_request_valid)

            write_port = memory.write_port(granularity=self.byte_size)
            m.d.comb += write_port.addr.eq(total_write_address)
            m.d.comb += write_port.data.eq(self.write_data)
            m.d.comb += write_port.en.eq(
                Mux(self.write_request_valid, self.byte_strobe, 0)
            )

        return m
