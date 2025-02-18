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


class CacheSubsystem(wiring.Component):
    def __init__(
        self,
        cache_config: CacheConfig,
        address_ranges: list[tuple[int, int]],
        read_delay: int,
        write_delay: int,
    ):
        """Cache subsytem for the pulpissimo SoC which includes a router, an adapter,
        the cache itself and optionally a delay unit. This module is basically ready
        to be on a TCDM interface in the pulpissimo SoC. If you want to connect several
        masters to the cache, you should use the subsystem wrapper.

        Args:
            cache_config (CacheConfig): Configuration for the cache.
            address_ranges (list[tuple[int, int]]): List of tuples of lower (inclusive) and upper (exclusive) bounds which represent address ranges for which the cache should be used. Requests with other addresses will bypass the cache.
            read_delay (int): Additional delay for any read requests sent from the cache to the memory. May be set to 0 if write_delay is also 0.
            write_delay (int): Additional delay for any write requests sent from the cache to the memory. May be set to 0 if read_delay is also 0.
        """
        assert cache_config.data_width == 32
        self.read_delay = read_delay
        self.write_delay = write_delay
        self.address_ranges = address_ranges
        self.lower_address = min([lower for lower, _ in self.address_ranges])
        self.upper_address = max([upper for _, upper in self.address_ranges])
        self.cache_address_width = (
            ceil_log2(self.upper_address - self.lower_address) - 2
        )
        self.cache_config = InternalCacheConfig(
            cache_config=cache_config,
            address_width=self.cache_address_width,
            be_data_width=32,
            be_address_width=self.cache_address_width,
            byte_size=8,
        )
        super().__init__(
            {"requestor": In(TCDMSignature()), "target": Out(TCDMSignature())}
        )

    def elaborate(self, platform):
        m = Module()

        m.submodules.cache = cache = Cache(self.cache_config)
        m.submodules.adapter = adapter = TCDMCacheAdapter(
            self.cache_config.fe_signature
        )
        m.submodules.router = router = TCDMCacheRouter(
            address_ranges=self.address_ranges,
            lowest_address=self.lower_address,
        )

        cache_fe = cache.fe
        cache_be = cache.be

        # Create a delay unit if needed
        if self.read_delay or self.write_delay:
            m.submodules.delay_unit = delay_unit = DelayUnit(
                mem_signature=self.cache_config.fe_signature,
                read_delay=self.read_delay,
                write_delay=self.write_delay,
            )
            wiring.connect(m, cache_be, delay_unit.requestor)
            cache_be = delay_unit.target

        # Connect cache to adapter
        wiring.connect(m, adapter.cache_fe, cache_fe)
        wiring.connect(m, cache_be, adapter.cache_be)

        # Connect adapter to router
        wiring.connect(m, router.cache_fe, adapter.requestor)
        wiring.connect(m, adapter.target, router.cache_be)
        m.d.comb += router.cache_port_ready.eq(cache.fe.port_ready)

        # Connect self to router
        wiring.connect(m, wiring.flipped(self.requestor), router.requestor)
        wiring.connect(m, router.target, wiring.flipped(self.target))

        return m
