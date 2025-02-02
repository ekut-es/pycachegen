from enum import Enum

from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out

from pycachegen import Cache, CacheConfig
from pycachegen.cache_config_validation import InternalCacheConfig
from pycachegen.cv32e40p.lsu_signature import LSUSignature
from pycachegen.cv32e40p.cache_adapter import CacheAdapter
from pycachegen.cv32e40p.delay_unit import DelayUnit

class SwitchState(Enum):
    IDLE = 0
    WAIT_FOR_CACHE_RESPONSE = 1
    WAIT_FOR_MEMORY_RESPONSE = 2


class CV32E40PDataCache(wiring.Component):
    def __init__(self, cache_config: CacheConfig, delay: int):
        """A data cache for the CV32E40P core and the Pulpissimo SoC. It is designed to go
        in the fc subsystem to sit between the core and the TCDM. The OBI PULP Adapter
        is also still required so as to only set req on the memory interface to 1
        if there's no outstanding request.

        This module uses the normal cache, the cv32e40p adapter and (optionally) the delay unit. It additionally
        checks whether the request address is withing the RAM region and only then
        sends the request to the cache, else the request will bypass the cache.

        TODO: Reduce address width of the cache so it can store shorter tags

        TODO: Add support for multi layer cache hierarchies

        Args:
            cache_config (CacheConfig): Configuration of the Cache. Note that data_width must be set to 32.
            delay (int): Amount of cycles by which the response for a memory request from the cache should be delayed. Can be set to 0.
        """
        self.cache_config = cache_config
        self.delay = delay
        super().__init__(
            {
                "core_if": In(LSUSignature()),
                "memory_if": Out(LSUSignature()),
            }
        )

    def elaborate(self, platform):
        m = Module()

        cache = Cache(
            InternalCacheConfig(
                cache_config=self.cache_config,
                address_width=30,
                be_data_width=32,
                be_address_width=30,
                byte_size=8,
            )
        )

        # Create the adapter and optionally the delay unit
        m.submodules.adapter = adapter = CacheAdapter(cache)
        cache_fe = adapter.core_if
        if self.delay != 0:
            m.submodules.delay_unit = delay_unit = DelayUnit(self.delay)
            wiring.connect(m, adapter.memory_if, delay_unit.slave)
            cache_be = delay_unit.master
        else:
            cache_be = adapter.memory_if

        state = Signal(SwitchState)

        # Hand out the cache's or the memory's response
        # and go back to idle state if we receive a response
        # (that decision might be overwritten later if a new request arrives)
        with m.If(state == SwitchState.WAIT_FOR_CACHE_RESPONSE):
            # We're awaiting a response from the cache, so connect its outputs to the core
            m.d.comb += self.core_if.rvalid.eq(cache_fe.rvalid)
            m.d.comb += self.core_if.err.eq(cache_fe.err)
            m.d.comb += self.core_if.rdata.eq(cache_fe.rdata)
            with m.If(cache_fe.rvalid):
                m.d.sync += state.eq(SwitchState.IDLE)
        with m.Elif(state == SwitchState.WAIT_FOR_MEMORY_RESPONSE):
            # We're awaiting a response from the memory, so connect its outputs to the core
            m.d.comb += self.core_if.rvalid.eq(self.memory_if.rvalid)
            m.d.comb += self.core_if.err.eq(self.memory_if.err)
            m.d.comb += self.core_if.rdata.eq(self.memory_if.rdata)
            with m.If(self.memory_if.rvalid):
                m.d.sync += state.eq(SwitchState.IDLE)

        # Also connect the cache BE to the memory if we're not
        # waiting for a response from the memory
        # This might be overwritten later if a new request
        # for the memory arrives
        with m.If(state != SwitchState.WAIT_FOR_MEMORY_RESPONSE):
            wiring.connect(m, cache_be, wiring.flipped(self.memory_if))

        # Accept new requests
        # Only consider requests if the cache is ready again
        # The cache wouldn't grant a request while it's still busy, but
        # the memory must still be connected to the cache and so we can't
        # access the memory
        with m.If(cache.fe.port_ready):
            with m.If(
                (self.core_if.addr >= 0x1C00_0000) & (self.core_if.addr < 0x1C08_0000)
            ):
                # The address lies within RAM range -> Send request to cache
                m.d.comb += cache_fe.we.eq(self.core_if.we)
                m.d.comb += cache_fe.be.eq(self.core_if.be)
                m.d.comb += cache_fe.addr.eq(self.core_if.addr)
                m.d.comb += cache_fe.wdata.eq(self.core_if.wdata)
                m.d.comb += cache_fe.req.eq(self.core_if.req)
                # Also tell the core if its request was granted
                m.d.comb += self.core_if.gnt.eq(cache_fe.gnt)
                with m.If(cache_fe.gnt):
                    m.d.sync += state.eq(SwitchState.WAIT_FOR_CACHE_RESPONSE)
            with m.Else():
                # The address does not lie within RAM range -> Send request to memory
                m.d.comb += self.memory_if.we.eq(self.core_if.we)
                m.d.comb += self.memory_if.be.eq(self.core_if.be)
                m.d.comb += self.memory_if.addr.eq(self.core_if.addr)
                m.d.comb += self.memory_if.wdata.eq(self.core_if.wdata)
                m.d.comb += self.memory_if.req.eq(self.core_if.req)
                # Also tell the core if its request was granted
                m.d.comb += self.core_if.gnt.eq(self.memory_if.gnt)
                with m.If(self.memory_if.gnt):
                    m.d.sync += state.eq(SwitchState.WAIT_FOR_MEMORY_RESPONSE)

        return m
