from amaranth import Array, Module, Signal, unsigned
from amaranth.lib import wiring
from amaranth.lib.memory import Memory
from amaranth.lib.wiring import In, Out
from amaranth.utils import exact_log2

from .cache_config import InternalCacheConfig


class TagStore(wiring.Component):
    def __init__(self, config: InternalCacheConfig):
        """Module for storing the tags of the cache.

        Args:
            config (InternalCacheConfig): Config of the cache.
        """
        self.num_ways = config.num_ways
        self.depth = config.num_sets
        self.data_width = config.tag_width

        # Create read_data signals for each tag store
        self.read_data = Array([Signal(self.data_width) for _ in range(self.num_ways)])

        # Don't add read_data to the ports since it is an array
        # and access will be handled by a method
        ports = {
            "index": In(config.index_width),
            "write_way": In(exact_log2(config.num_ways)),
            "write_data": In(config.data_width),
            "write_valid": In(1),
        }

        super().__init__(ports)

    def elaborate(self, platform):
        m = Module()

        # Create one tag memory per way
        for way in range(self.num_ways):
            m.submodules[f"memory_{way}"] = memory = Memory(
                shape=unsigned(self.data_width), depth=self.depth, init=[]
            )
            read_port = memory.read_port(domain="comb")
            write_port = memory.write_port()

            m.d.comb += read_port.addr.eq(self.index)
            m.d.comb += self.read_data[way].eq(read_port.data)

            m.d.comb += write_port.addr.eq(self.index)
            m.d.comb += write_port.data.eq(self.write_data)
            with m.If(self.write_valid & (way == self.write_way)):
                m.d.comb += write_port.en.eq(1)

        return m
