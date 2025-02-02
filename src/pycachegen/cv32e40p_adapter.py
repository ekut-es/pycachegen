from enum import Enum

from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out

from pycachegen.cache_config_validation import InternalCacheConfig
from pycachegen.memory_bus import MemoryBusInterface
from pycachegen import Cache, CacheConfig


class CV32E40PLSUSignature(wiring.Signature):
    def __init__(
        self,
    ):
        super().__init__(
            [
                ("req", Out(1)),
                ("gnt", In(1)),
                ("rvalid", In(1)),
                ("we", Out(1)),
                ("be", Out(4)),
                ("addr", Out(32)),
                ("wdata", Out(32)),
                ("rdata", In(32)),
                ("err", In(1)),
            ]
        )


class CV32E40PCacheLSUAdapter(wiring.Component):
    def __init__(self, cache: Cache):
        self.cache_config = cache.config
        self.cache = cache
        super().__init__(
            {
                # Core <-> Adapter
                "core_if": In(CV32E40PLSUSignature()),
                # Adapter <-> Main Memory
                "memory_if": Out(CV32E40PLSUSignature()),
            }
        )

    def elaborate(self, platform):
        m = Module()

        m.submodules.cache = cache = self.cache

        """
        https://docs.openhwgroup.org/projects/cv32e40x-user-manual/en/latest/load_store_unit.html
        https://github.com/openhwgroup/obi/blob/072d9173c1f2d79471d6f2a10eae59ee387d4c6f/OBI-v1.6.0.pdf

        TODO: Herausfinden, ob die LSU im Core oder außerhalb sitzt. Die LSU handelt z.B. misaligned
        accesses, was der Cache nicht kann.

        TODO: Parametrisierbarkeit

        TODO: Memory ranges checken; es sollen nicht (32-n) bit tags gespeichert werden müssen

        TODO: Add support for multi layer cache hierarchies

        Der OBI PULP Adapter hört die Request vom Memory und die rvalid und gnt vom memory mit
        und entscheidet, wann eine request an den memory weitergegeben werden darf:

        WAIT_GNT:
        Wenn gerade keine Anfrage verarbeitet wird, werden Anfragen direkt an den Memory weitergegeben.
        Trifft eine Anfrage ein, wird in den WAIT_VALID State gewechselt, wenn der Memory die Request granted.

        WAIT_VALID:
        Wenn gerade eine Anfrage verarbeitet wird, werden Anfragen nur an den Memory weitergegeben, wenn
        der Memory rvalid auf 1 setzt. Ist rvalid 1 und es wird kein grant durch den Memory erteilt, wird wieder
        in WAIT_GNT gewechselt. Das kann sein, weil der Memory noch beschäftigt ist oder weil keine Anfrage vom
        Core kommt. Anderfalls liegt eine Anfrage vor, die der memory gegranted hat, und der Zustand wird nicht
        gewechselt.
        """

        processing_read = Signal()
        processing_write = Signal()

        ## Connect cache.fe
        core_if = self.core_if

        with m.If(processing_read):
            # When processing a read, set rvalid to read_data_valid.
            m.d.comb += core_if.rvalid.eq(cache.fe.read_data_valid)
            with m.If(cache.fe.read_data_valid):
                # When done, stop outputting read_data_valid as rvalid.
                m.d.sync += processing_read.eq(0)

        with m.If(processing_write):
            # When processing a write, set rvalid to port_ready
            # #TODO might not be a good idea? When should rvalid be set in case of a write???
            m.d.comb += core_if.rvalid.eq(cache.fe.port_ready)
            with m.If(cache.fe.port_ready):
                # When done, stop outputting port_ready as rvalid
                m.d.sync += processing_write.eq(0)

        # When granting a request, remember what type of request we're currentyl processing.
        # This is intentionally placed after the blocks which set these variables to 0
        # again to support back to back requests (these changes will overwrite the previous
        # changes)
        with m.If(core_if.gnt):
            m.d.sync += processing_read.eq(~core_if.we)
            m.d.sync += processing_write.eq(core_if.we)

        # gnt may only be asserted when req gets asserted
        m.d.comb += core_if.gnt.eq(cache.fe.port_ready & core_if.req)
        # forward request
        m.d.comb += cache.fe.request_valid.eq(core_if.req)
        # cache can only do byte writes but not byte reads. write_strobe == 0 means read.
        m.d.comb += cache.fe.write_strobe.eq(Mux(core_if.we, core_if.be, 0))
        m.d.comb += cache.fe.address.eq(core_if.addr[2:])  # TODO
        m.d.comb += cache.fe.write_data.eq(core_if.wdata)
        # handing out the full word regardless of be should be fine (? TODO)
        m.d.comb += core_if.rdata.eq(cache.fe.read_data)
        m.d.comb += core_if.err.eq(0)  # Errors are not supported by the cache
        m.d.comb += cache.fe.flush.eq(0)  # Core doesn't use flush

        ## Connect cache.be
        mem_if = self.memory_if

        read_sent = Signal()
        read_answered = Signal()
        read_data_buffer = Signal(unsigned(32))

        with m.If(read_sent & mem_if.rvalid):
            # Set read_answered if read_sent and rvalid
            m.d.sync += read_answered.eq(1)
            # Also buffer the read data, it doesn't have to stay correct
            m.d.sync += read_data_buffer.eq(mem_if.rdata)

        with m.If(mem_if.gnt):
            # when a new request gets granted, clear read_answered
            # this has to overwrite setting read_answered to 1 after receiving rvalid
            # to allow back-to-back requests
            m.d.sync += read_answered.eq(0)
            # also remember if we sent a read
            m.d.sync += read_sent.eq(~mem_if.we)

        with m.If(read_sent):
            with m.If(~read_answered):
                # set read_data_valid to rvalid when a read request was
                # sent but not yet answered
                m.d.comb += cache.be.read_data_valid.eq(mem_if.rvalid)
                # also hand out the mem_if rdata
                m.d.comb += cache.be.read_data.eq(mem_if.rdata)
            with m.Else():
                # rvalid will only be 1 for one cycle, but read_data_valid
                # has to be kept high until the next request
                m.d.comb += cache.be.read_data_valid.eq(1)
                # hand out the buffered read data
                m.d.comb += cache.be.read_data.eq(read_data_buffer)

        m.d.comb += cache.be.port_ready.eq(mem_if.gnt)
        m.d.comb += mem_if.req.eq(cache.be.request_valid)
        m.d.comb += mem_if.be.eq(
            Mux(cache.be.write_strobe.any(), cache.be.write_strobe, -1)
        )
        m.d.comb += mem_if.we.eq(cache.be.write_strobe.any())
        m.d.comb += mem_if.addr.eq(Cat(C(0, unsigned(2)), cache.be.address))
        m.d.comb += mem_if.wdata.eq(cache.be.write_data)

        return m


class CV32E40PLSUDelayUnit(wiring.Component):

    def __init__(self, delay: int):
        self.delay = delay
        super().__init__(
            # master: to main memory
            # slave: to cache
            {"master": Out(CV32E40PLSUSignature()), "slave": In(CV32E40PLSUSignature())}
        )

    def elaborate(self, platform):
        m = Module()
        m.d.comb += self.master.we.eq(self.slave.we)
        m.d.comb += self.master.be.eq(self.slave.be)
        m.d.comb += self.master.addr.eq(self.slave.addr)
        m.d.comb += self.master.wdata.eq(self.slave.wdata)

        m.d.comb += self.slave.err.eq(0)
        m.d.comb += self.slave.rdata.eq(0)
        m.d.comb += self.slave.rvalid.eq(0)

        # Whether we're waiting for a response from main memory
        awaiting_response = Signal()
        # Whether we're currently delaying the response to the cache
        delaying_response = Signal()

        delay_counter = Signal(range(self.delay))

        rdata = Signal(unsigned(32))
        err = Signal()

        with m.If(delaying_response):
            m.d.sync += delay_counter.eq(delay_counter + 1)
            with m.If(delay_counter == (self.delay - 1)):
                m.d.comb += self.slave.err.eq(err)
                m.d.comb += self.slave.rdata.eq(rdata)
                m.d.comb += self.slave.rvalid.eq(1)
                m.d.sync += delay_counter.eq(0)
                m.d.sync += delaying_response.eq(0)

        with m.If(
            ~(awaiting_response | (delaying_response & ~(delay_counter == self.delay)))
        ):
            # Not awaiting or delaying a response -> let the req (and gnt) through
            m.d.comb += self.master.req.eq(self.slave.req)
            m.d.comb += self.slave.gnt.eq(self.master.gnt)
            with m.If(self.slave.req & self.master.gnt):
                # request was granted
                m.d.sync += awaiting_response.eq(1)

        with m.If(awaiting_response):
            with m.If(self.master.rvalid):
                m.d.sync += rdata.eq(self.master.rdata)
                m.d.sync += err.eq(self.master.err)
                m.d.sync += awaiting_response.eq(0)
                m.d.sync += delaying_response.eq(1)

        return m


class SwitchState(Enum):
    IDLE = 0
    WAIT_FOR_CACHE_RESPONSE = 1
    WAIT_FOR_MEMORY_RESPONSE = 2


class CV32E40PDataCache(wiring.Component):
    def __init__(self, cache_config: CacheConfig, delay: int):
        self.cache_config = cache_config
        self.delay = delay
        super().__init__(
            {
                "core_if": In(CV32E40PLSUSignature()),
                "memory_if": Out(CV32E40PLSUSignature()),
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

        m.submodules.adapter = adapter = CV32E40PCacheLSUAdapter(cache)
        cache_fe = adapter.core_if
        if self.delay != 0:
            m.submodules.delay_unit = delay_unit = CV32E40PLSUDelayUnit(self.delay)
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
