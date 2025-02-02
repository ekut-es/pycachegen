from enum import Enum

from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out
from amaranth.utils import ceil_log2

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
    def __init__(self, cache_config: CacheConfig, delay: int, lower_address: int, upper_address: int):
        """A data cache for the CV32E40P core.
         
        This module uses the normal cache, the cv32e40p adapter and (optionally) the delay unit. It additionally
        checks whether the request address is withing the RAM region and only then
        sends the request to the cache, else the request will bypass the cache.

        When used with the Pulpissimo SoC, it should be placed in the fc subsystem 
        in between the core and the TCDM. The OBI PULP Adapter is also still required
        so as to only set req on the memory interface to 1 if there's no outstanding request.

        TODO: Add support for multi layer cache hierarchies

        Args:
            cache_config (CacheConfig): Configuration of the Cache. Note that data_width must be set to 32.
            delay (int): Amount of cycles by which the response for a memory request from the cache should be delayed. Can be set to 0.
            lower_address (int): The lower address of the RAM (inclusive)
            upper_address (int): The upper address of the RAM (exclusive)
        """
        self.cache_config = cache_config
        self.delay = delay
        # Address bounds for the RAM
        # Addresses outside this region will bypass the cache
        self.lower_address = lower_address
        self.upper_address = upper_address
        self.cache_address_width = ceil_log2(self.upper_address - self.lower_address) - 2
        super().__init__(
            {
                "core_if": In(LSUSignature()),
                "memory_if": Out(LSUSignature()),
            }
        )

    def elaborate(self, platform):
        m = Module()

        # Create the cache
        # The cache shall only use addresses wide enough to cover the RAM region
        # so that it only needs to store small tags. Also the byte offset bits
        # are cut off from the address (that happens within the adapter)
        cache = Cache(
            InternalCacheConfig(
                cache_config=self.cache_config,
                address_width=self.cache_address_width,
                be_data_width=32,
                be_address_width=self.cache_address_width,
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
            m.d.comb += self.memory_if.addr.eq(cache_be.addr + self.lower_address)

        # Accept new requests
        # Only consider requests if the cache is ready again
        # The cache wouldn't grant a request while it's still busy, but
        # the memory must still be connected to the cache and so we can't
        # access the memory
        with m.If(cache.fe.port_ready):
            with m.If(
                (self.core_if.addr >= self.lower_address) & (self.core_if.addr < self.upper_address)
            ):
                # The address lies within RAM range -> Send request to cache
                m.d.comb += cache_fe.we.eq(self.core_if.we)
                m.d.comb += cache_fe.be.eq(self.core_if.be)
                m.d.comb += cache_fe.addr.eq(self.core_if.addr - self.lower_address)
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
