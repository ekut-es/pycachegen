from amaranth import Array, Module, Signal, unsigned
from amaranth.lib import wiring
from amaranth.lib.memory import Memory
from amaranth.lib.wiring import In

from .cache_config import InternalCacheConfig
from .interfaces import DirectorySignature


class CacheDirectory(wiring.Component):
    def __init__(self, config: InternalCacheConfig):
        """Module for storing the tags, valid and dirty bits of the cache.

        Args:
            config (InternalCacheConfig): Config of the cache.
        """
        self.num_ways = config.num_ways
        self.depth = config.num_sets
        self.data_width = config.tag_width
        self.num_sets = config.num_sets

        super().__init__({"port": In(DirectorySignature(config))})

    def elaborate(self, platform):
        m = Module()

        index = self.port.index
        write_way = self.port.write_way

        # Create one tag memory per way
        for way in range(self.num_ways):
            m.submodules[f"memory_{way}"] = memory = Memory(shape=unsigned(self.data_width), depth=self.depth, init=[])
            read_port = memory.read_port(domain="comb")
            write_port = memory.write_port()

            m.d.comb += read_port.addr.eq(index)
            m.d.comb += self.port.tag(way).eq(read_port.data)

            m.d.comb += write_port.addr.eq(index)
            m.d.comb += write_port.data.eq(self.port.data_tag)
            with m.If(self.port.update_tag & (way == write_way)):
                m.d.comb += write_port.en.eq(1)

        # Create Arrays of dirty and valid bits
        valid_bits = Array(
            [Signal(shape=unsigned(self.num_ways), name=f"valid_bits_{set_idx}") for set_idx in range(self.num_sets)]
        )
        dirty_bits = Array(
            [Signal(shape=unsigned(self.num_ways), name=f"dirty_bits{set_idx}") for set_idx in range(self.num_sets)]
        )

        # Output selected valid and dirty bits
        m.d.comb += self.port.valid_bits.eq(valid_bits[index])
        m.d.comb += self.port.dirty_bits.eq(dirty_bits[index])

        # Update valid and dirty bits
        with m.If(self.port.update_valid):
            m.d.sync += valid_bits[index].bit_select(write_way, 1).eq(self.port.data_valid)
        with m.If(self.port.update_dirty):
            m.d.sync += dirty_bits[index].bit_select(write_way, 1).eq(self.port.data_dirty)

        return m
