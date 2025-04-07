from amaranth import (
    Cat,
    ClockSignal,
    Instance,
    Module,
    Mux,
    ResetSignal,
    Signal,
    unsigned,
)
from amaranth.lib import wiring
from amaranth.lib.memory import Memory
from amaranth.lib.wiring import In
from amaranth.utils import exact_log2

from .cache_config import InternalCacheConfig
from .interfaces import CacheStoreSignature


class CacheStore(wiring.Component):
    def __init__(self, config: InternalCacheConfig):
        """Module for storing the actual data of the cache.

        This module uses a single dual port memory.

        Args:
            config (InternalCacheConfig): The cache config.
        """
        self.depth = config.num_sets * config.block_size * config.num_ways
        self.address_width = exact_log2(config.num_sets) + exact_log2(config.block_size)
        self.total_address_width = self.address_width + exact_log2(config.num_ways)
        self.module_name = config.data_memory_module
        self.data_width = config.data_width
        self.byte_size = config.byte_size
        super().__init__({"port": In(CacheStoreSignature(config))})

    def elaborate(self, platform):
        m = Module()

        # the given addresses are only "real addresses" and do not
        # include any information about the way to be accessed
        # Concatenate the address and the way to get the total address for the memory
        total_read_address = Signal(unsigned(self.total_address_width))
        m.d.comb += total_read_address.eq(Cat(self.port.read_address, self.port.read_way))
        total_write_address = Signal(unsigned(self.total_address_width))
        m.d.comb += total_write_address.eq(Cat(self.port.write_address, self.port.write_way))

        if self.module_name:
            # Extend byte strobe to bit strobe
            bit_strobe = Signal(self.data_width)
            for i, bit in enumerate(self.port.byte_strobe):
                m.d.comb += bit_strobe.word_select(i, self.byte_size).eq(Mux(bit, -1, 0))

            # Use an external Memory module
            m.submodules.memory = Instance(
                type=self.module_name,
                i_clk=ClockSignal(),
                i_rst=ResetSignal(),
                i_read_request_valid=self.port.read_request_valid,
                i_read_address=total_read_address,
                o_read_data=self.port.read_data,
                i_write_request_valid=self.port.write_request_valid,
                i_write_address=total_write_address,
                i_write_data=self.port.write_data,
                i_bit_strobe=bit_strobe,
            )
        else:
            # Create an Amaranth Memory
            m.submodules.memory = memory = Memory(shape=unsigned(self.data_width), depth=self.depth, init=[])
            read_port = memory.read_port()
            m.d.comb += read_port.addr.eq(total_read_address)
            m.d.comb += self.port.read_data.eq(read_port.data)
            m.d.comb += read_port.en.eq(self.port.read_request_valid)

            write_port = memory.write_port(granularity=self.byte_size)
            m.d.comb += write_port.addr.eq(total_write_address)
            m.d.comb += write_port.data.eq(self.port.write_data)
            m.d.comb += write_port.en.eq(Mux(self.port.write_request_valid, self.port.byte_strobe, 0))

        return m
