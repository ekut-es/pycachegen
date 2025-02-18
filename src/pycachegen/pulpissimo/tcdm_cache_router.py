from enum import Enum

from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out
from amaranth.utils import ceil_log2

from pycachegen.pulpissimo.tcdm_signature import TCDMSignature


class RouterState(Enum):
    IDLE = 0
    WAIT_FOR_CACHE_RESPONSE = 1
    WAIT_FOR_MEMORY_RESPONSE = 2


class TCDMCacheRouter(wiring.Component):
    def __init__(
        self,
        address_ranges: list[tuple[int, int]],
        lowest_address: int,
    ):
        """Routes TCDM requests to a cache or a main memory (target) based on address ranges. This
        module also handles the connection between the cache and the target.
        
        It will also subtract/add the lowest_address from the addresses to the cache/to the addresses from the cache
        so that the addresses for the cache start at 0 and so it can store shorter tags.

        Args:
            address_ranges (list[tuple[int, int]]): List of address ranges (lower bound inclusive, upper bound exclusive) for which the cache should be used. Other addresses will bypass the cache.
            lower_address (int): the minimum of the lower bounds of the address ranges. Needed for manipulating the addresses between the cache and the router.
        """
        self.address_ranges = address_ranges
        self.lower_address = lowest_address
        super().__init__(
            {
                # requestor -> router
                "requestor": In(TCDMSignature()),
                # router -> cache
                "cache_fe": Out(TCDMSignature()),
                # cache -> target
                "cache_be": In(TCDMSignature()),
                # router -> target
                "target": Out(TCDMSignature()),
                # whether the cache is ready
                "cache_port_ready": In(1),
            }
        )

    def elaborate(self, platform):
        m = Module()

        state = Signal(RouterState)

        requestor = self.requestor
        cache_fe = self.cache_fe
        cache_be = self.cache_be
        target = self.target

        with m.If(state == RouterState.WAIT_FOR_CACHE_RESPONSE):
            # We're awaiting a response from the cache, so connect its outputs to the requestor
            m.d.comb += requestor.r_valid.eq(cache_fe.r_valid)
            m.d.comb += requestor.r_opc.eq(cache_fe.r_opc)
            m.d.comb += requestor.r_rdata.eq(cache_fe.r_rdata)
            with m.If(cache_fe.r_valid):
                # Received a response -> go back to idle
                m.d.sync += state.eq(RouterState.IDLE)
        with m.Elif(state == RouterState.WAIT_FOR_MEMORY_RESPONSE):
            # We're awaiting a response from the memory, so connect its outputs to the requestor
            m.d.comb += requestor.r_valid.eq(target.r_valid)
            m.d.comb += requestor.r_opc.eq(target.r_opc)
            m.d.comb += requestor.r_rdata.eq(target.r_rdata)
            with m.If(target.r_valid):
                m.d.sync += state.eq(RouterState.IDLE)

        # Also connect the cache BE to the target if we're not
        # waiting for a response from the target
        # This might be overwritten later if a new request that bypasses the cache arrives
        with m.If(state != RouterState.WAIT_FOR_MEMORY_RESPONSE):
            wiring.connect(m, wiring.flipped(cache_be), wiring.flipped(target))
            m.d.comb += target.add.eq(cache_be.add + self.lower_address)

        # Determine if the current address is in any of the ranges for the cache
        addr_in_range = Signal(unsigned(len(self.address_ranges)))
        addr_for_cache = Signal()
        for i, (lower, upper) in enumerate(self.address_ranges):
            m.d.comb += addr_in_range[i].eq(
                (requestor.add >= lower) & (requestor.add < upper)
            )
        m.d.comb += addr_for_cache.eq(addr_in_range.any())

        # Accept new requests if we're not awaiting a response
        # Only consider requests if the cache is ready again
        # The cache wouldn't grant a request while it's still busy, but
        # the memory must still be connected to the cache and so we can't
        # access the memory
        with m.If(
            self.cache_port_ready
            & (
                (state == RouterState.IDLE)
                | ((state == RouterState.WAIT_FOR_CACHE_RESPONSE) & (cache_fe.r_valid))
                | ((state == RouterState.WAIT_FOR_CACHE_RESPONSE) & (target.r_valid))
            )
        ):
            with m.If(addr_for_cache):
                # The address lies within the cache address range -> Send request to cache
                m.d.comb += cache_fe.wen.eq(requestor.wen)
                m.d.comb += cache_fe.be.eq(requestor.be)
                m.d.comb += cache_fe.add.eq(requestor.add - self.lower_address)
                m.d.comb += cache_fe.wdata.eq(requestor.wdata)
                m.d.comb += cache_fe.req.eq(requestor.req)
                # Also tell the requestor if its request was granted
                m.d.comb += requestor.gnt.eq(cache_fe.gnt)
                with m.If(cache_fe.gnt):
                    m.d.sync += state.eq(RouterState.WAIT_FOR_CACHE_RESPONSE)
            with m.Else():
                # The address does not lie within cache address range -> Send request to memory
                m.d.comb += target.wen.eq(requestor.wen)
                m.d.comb += target.be.eq(requestor.be)
                m.d.comb += target.add.eq(requestor.add)
                m.d.comb += target.wdata.eq(requestor.wdata)
                m.d.comb += target.req.eq(requestor.req)
                # Also tell the requestor if its request was granted
                m.d.comb += requestor.gnt.eq(target.gnt)
                with m.If(target.gnt):
                    m.d.sync += state.eq(RouterState.WAIT_FOR_MEMORY_RESPONSE)

        return m
