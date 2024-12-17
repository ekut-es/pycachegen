from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out
from amaranth.lib.memory import Memory
from amaranth.utils import exact_log2

from pycachegen.cache_config_validation import InternalCacheConfig


class TagStore(wiring.Component):
    def __init__(self, config: InternalCacheConfig):
        self.num_ways = config.num_ways
        self.depth = config.num_sets
        self.data_width = config.tag_width

        ports = {
            "index": In(config.index_width),
            "write_way": In(exact_log2(config.num_ways)),
            "write_data": In(config.data_width),
            "write_valid": In(1),
        }

        # All tag memories must be readable at the same time
        for way in range(self.num_ways):
            ports[f"read_data_{way}"] = Out(config.data_width)

        super().__init__(ports)

    def get_read_data(self, way):
        return getattr(self, f"read_data_{way}")
    
    def init_read(self, addr):
        """Initiate read from m.d.comb.

        Args:
            way: The way to access.
            addr: The address is the set index which should be accessed.
        """
        self.m.d.comb += self.address.eq(addr)

    def init_write(self, way, addr, data):
        """Initiate write from m.d.comb.

        Args:
            way: The way to access.
            addr: The address is the set index which should be accessed.
            data: The tag to write to the memory.
        """
        self.m.d.comb += self.write_valid.eq(1)
        self.m.d.comb += self.write_data.eq(data)
        self.m.d.comb += self.write_way.eq(way)
        self.m.d.comb += self.index.eq(addr)

    def elaborate(self, platform):
        m = Module()

        # Create one tag memory per way
        for way in range(self.num_ways):
            m.submodules[f"memory_{way}"] = memory = Memory(shape=unsigned(self.data_width), depth=self.depth, init=[])
            read_port = memory.read_port(domain="comb")
            write_port = memory.write_port()

            m.d.comb += read_port.addr.eq(self.index)
            m.d.comb += self.get_read_data(way).eq(read_port.data)
            
            m.d.comb += write_port.addr.eq(self.index)
            m.d.comb += write_port.data.eq(self.write_data)
            with m.If(way == self.write_way):
                m.d.comb += write_port.en.eq(1)

        return m
