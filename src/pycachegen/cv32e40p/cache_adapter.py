from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out

from pycachegen import Cache
from pycachegen.cv32e40p.lsu_signature import LSUSignature

class CacheAdapter(wiring.Component):
    def __init__(self, cache: Cache):
        """Adapts the cache to the interface of the LSU.

        Args:
            cache (Cache): The cache to be adapted.
        """
        self.cache_config = cache.config
        self.cache = cache
        super().__init__(
            {
                # Core <-> Adapter
                "core_if": In(LSUSignature()),
                # Adapter <-> Main Memory
                "memory_if": Out(LSUSignature()),
            }
        )

    def elaborate(self, platform):
        m = Module()

        m.submodules.cache = cache = self.cache

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