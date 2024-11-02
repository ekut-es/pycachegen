from amaranth import *
from amaranth.lib.memory import Memory
from pycachegen.cache_config_validation import InternalCacheConfig


class CacheMemories:
    def __init__(self, config: InternalCacheConfig, m: Module):
        """Creates tag and data memories for the cache. Also provides
        methods for accessing them.

        Both the tag memory and the write memory utilize one read and write port each.
        The data memory uses a synchronous read port, the tag memory uses an async read port.

        Note that the enable signal of the tag memory read port is always high (which is the
        Amaranth default), but the data memory has its read port enable signal set to 0 so
        that requested read data can still be accessed even after several cycles.

        Args:
            config (InternalCacheConfig): The config of the cache.
            m (Module): The cache module.
        """
        self.m = m
        # Create one tag and data memory per way
        # usage: tag_mem[way][index], data_mem[way][Cat(word_offset, index)]
        # data memory contains values that represent whole blocks (potentially multiple words!)
        self.tag_mem_rp = Array()
        self.tag_mem_wp = Array()
        self.data_mem_rp = Array()
        self.data_mem_wp = Array()
        for i in range(config.num_ways):
            tag_mem = Memory(
                shape=unsigned(config.tag_width), depth=config.num_sets, init=[]
            )
            m.submodules[f"tag_mem_{i}"] = tag_mem
            self.tag_mem_rp.append(tag_mem.read_port(domain="comb"))
            self.tag_mem_wp.append(tag_mem.write_port())

            data_mem = Memory(
                shape=unsigned(config.data_width),
                depth=config.num_sets * config.block_size,
                init=[],
            )
            m.submodules[f"data_mem_{i}"] = data_mem
            self.data_mem_rp.append(data_mem.read_port())
            self.data_mem_wp.append(data_mem.write_port(granularity=config.byte_size))
            # disable data_mem.read_port.en by default so that the read data gets preserved even when the address changes
            # thats necessary because the read data might only be needed after several cycles
            m.d.comb += self.data_mem_rp[-1].en.eq(0)

    def init_data_mem_read(self, way, addr):
        """Initiate read from data memory from m.d.comb.

        Args:
            way: The way to access.
            addr: The address consists of the word offset and set index bits.
        """
        self.m.d.comb += self.data_mem_rp[way].en.eq(1)
        self.m.d.comb += self.data_mem_rp[way].addr.eq(addr)

    def init_data_mem_write(self, way, addr, data, strobe):
        """Initiate write to data memory from m.d.comb.

        Args:
            way: The way to access.
            addr: The address consists of the word offset and set index bits.
            data: The data to write to the memory.
            strobe: The write strobe/byte enable signal.
        """
        self.m.d.comb += self.data_mem_wp[way].en.eq(strobe)
        self.m.d.comb += self.data_mem_wp[way].addr.eq(addr)
        self.m.d.comb += self.data_mem_wp[way].data.eq(data)

    def init_tag_mem_read(self, way, addr):
        """Initiate read from tag memory from m.d.comb.

        Args:
            way: The way to access.
            addr: The address is the set index which should be accessed.
        """
        self.m.d.comb += self.tag_mem_rp[way].addr.eq(addr)

    def init_tag_mem_write(self, way, addr, data):
        """Initiate write to tag memory from m.d.comb.

        Args:
            way: The way to access.
            addr: The address is the set index which should be accessed.
            data: The tag to write to the memory.
        """
        self.m.d.comb += self.tag_mem_wp[way].en.eq(1)
        self.m.d.comb += self.tag_mem_wp[way].addr.eq(addr)
        self.m.d.comb += self.tag_mem_wp[way].data.eq(data)
