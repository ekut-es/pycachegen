from typing import Optional

from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out
from amaranth.utils import ceil_log2

from pycachegen.cache import Cache
from pycachegen.delay_unit import DelayUnit
from pycachegen.pulpissimo.tcdm_cache_router import TCDMCacheRouter
from pycachegen.pulpissimo.tcdm_cache_adapter import TCDMCacheAdapter
from pycachegen.pulpissimo.tcdm_signature import TCDMSignature
from pycachegen.cache_config_validation import CacheConfig, InternalCacheConfig
from pycachegen.memory_bus import MemoryBusSignature
from pycachegen.utils import log_parameters
from pycachegen.advanced_write_buffer import AdvancedWriteBuffer


@log_parameters
class CacheSubsystem(wiring.Component):
    def __init__(
        self,
        cache_config: Optional[CacheConfig],
        address_ranges: list[tuple[int, int]],
        write_buffer_depth: int,
        read_delay: int,
        write_delay: int,
    ):
        """Cache subsytem for the pulpissimo SoC which includes a router, an adapter,
        the cache itself and optionally a delay unit. This module is basically ready
        to be on a TCDM interface in the pulpissimo SoC. If you want to connect several
        masters to the cache, you should use the subsystem wrapper.

        Args:
            cache_config (Optional[CacheConfig]): Configuration for the cache. Can be set to None if no cache should be used.
            address_ranges (list[tuple[int, int]]): List of tuples of lower (inclusive) and upper (exclusive) bounds which represent address ranges for which the cache should be used. Requests with other addresses will bypass the cache.
            write_buffer_depth (int): Depth of the write buffer. Can be set to 0 if no write buffer should be used. A write buffer can only be used together with a cache.
            read_delay (int): Additional delay for any read requests sent from the cache to the memory. May be set to 0 if write_delay is also 0.
            write_delay (int): Additional delay for any write requests sent from the cache to the memory. May be set to 0 if read_delay is also 0.
        """
        if write_buffer_depth:
            assert cache_config is not None
        self.write_buffer_depth = write_buffer_depth
        self.read_delay = read_delay
        self.write_delay = write_delay
        self.use_delay = bool(read_delay) or bool(write_delay)
        self.address_ranges = address_ranges
        self.lower_address = min([lower for lower, _ in self.address_ranges])
        self.upper_address = max([upper for _, upper in self.address_ranges])
        self.cache_address_width = (
            ceil_log2(self.upper_address - self.lower_address) - 2
        )
        self.cache_signature = MemoryBusSignature(
            address_width=self.cache_address_width, data_width=32, bytes_per_word=4
        )
        self.use_cache = False
        if cache_config is not None:
            assert cache_config.data_width == 32
            self.cache_config = InternalCacheConfig(
                cache_config=cache_config,
                address_width=self.cache_address_width,
                be_data_width=32,
                be_address_width=self.cache_address_width,
                byte_size=8,
            )
            self.use_cache = True
        super().__init__(
            {"requestor": In(TCDMSignature()), "target": Out(TCDMSignature())}
        )

    def elaborate(self, platform):
        m = Module()

        use_cache = self.use_cache
        use_delay = self.use_delay

        if (not use_cache) and (not use_delay):
            # just connect the requestor to the target
            wiring.connect(
                m, wiring.flipped(self.requestor), wiring.flipped(self.target)
            )
            # useless signal so that clk and rst get generated...
            x = Signal()
            m.d.sync += x.eq(~x)
            return m

        m.submodules.adapter = adapter = TCDMCacheAdapter(self.cache_signature)
        m.submodules.router = router = TCDMCacheRouter(
            address_ranges=self.address_ranges,
            lowest_address=self.lower_address,
        )

        cache_ready = 1

        fes, bes = [], []

        # Create a cache if needed
        if use_cache:
            m.submodules.cache = cache = Cache(self.cache_config)
            cache_ready &= cache.fe.port_ready
            fes.append(cache.fe)
            bes.append(cache.be)

        # Create a write buffer if needed
        if self.write_buffer_depth != 0:
            m.submodules.write_buffer = write_buffer = AdvancedWriteBuffer(
                signature=self.cache_config.be_signature, depth=self.write_buffer_depth
            )
            fes.append(write_buffer.fe)
            bes.append(write_buffer.be)
            # write buffer ready is 

        # Create a delay unit if needed
        if use_delay:
            m.submodules.delay_unit = delay_unit = DelayUnit(
                mem_signature=self.cache_signature,
                read_delay=self.read_delay,
                write_delay=self.write_delay,
            )
            cache_ready &= delay_unit.requestor.port_ready
            fes.append(delay_unit.requestor)
            bes.append(delay_unit.target)

        wiring.connect(m, adapter.cache_fe, fes.pop(0))
        wiring.connect(m, adapter.cache_be, bes.pop())

        for fe, be in zip(fes, bes):
            wiring.connect(m, fe, be)


        # if (not use_cache) and (use_delay):
        #     # connect adapter only to delay unit
        #     wiring.connect(m, adapter.cache_fe, delay_unit.requestor)
        #     wiring.connect(m, delay_unit.target, adapter.cache_be)
        # elif (use_cache) and (not use_delay):
        #     # connect adapter only to cache
        #     wiring.connect(m, adapter.cache_fe, cache.fe)
        #     wiring.connect(m, cache.be, adapter.cache_be)
        # elif (use_cache) and (use_delay):
        #     # connect cache to delay unit and then to adapter
        #     wiring.connect(m, cache.be, delay_unit.requestor)
        #     wiring.connect(m, adapter.cache_fe, cache.fe)
        #     wiring.connect(m, delay_unit.target, adapter.cache_be)

        # Connect adapter to router
        wiring.connect(m, router.cache_fe, adapter.requestor)
        wiring.connect(m, adapter.target, router.cache_be)
        m.d.comb += router.cache_port_ready.eq(cache_ready)

        # Connect self to router
        wiring.connect(m, wiring.flipped(self.requestor), router.requestor)
        wiring.connect(m, router.target, wiring.flipped(self.target))

        return m
