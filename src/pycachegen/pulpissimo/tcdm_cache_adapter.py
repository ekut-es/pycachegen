from amaranth import C, Cat, Module, Mux, Signal, unsigned
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out

from pycachegen.interfaces import MemoryBusSignature
from pycachegen.pulpissimo.tcdm_signature import TCDMSignature


class TCDMCacheAdapter(wiring.Component):
    def __init__(self, cache_signature: MemoryBusSignature):
        """Adapts a cache to the pulpissimo TCDM interface.

        Args:
            cache_signature (MemoryBusSignature): Signature of the cache interface. Note that the FE and BE interfaces
                use the same signature.
        """
        self.cache_signature = cache_signature
        super().__init__(
            {
                # Requestor (Core) -> Adapter
                "requestor": In(TCDMSignature()),
                # Adapter -> Cache
                "cache_fe": Out(cache_signature),
                # Cache -> Adapter
                "cache_be": In(cache_signature),
                # Adapter -> Target (Main Memory)
                "target": Out(TCDMSignature()),
            }
        )

    def elaborate(self, platform):
        m = Module()

        cache_fe = self.cache_fe
        cache_be = self.cache_be
        requestor = self.requestor
        target = self.target

        # State of the adapter
        # Whether the adapter is currently processing a read or a write request.
        processing_read = Signal()
        processing_write = Signal()
        # Whether the cache has sent a read request to the target
        read_sent = Signal()
        # Whether the target has delivered the requested read data to the cache
        read_answered = Signal()
        # Buffer for the read data requested by the cache from the target
        read_data_buffer = Signal(unsigned(32))

        # Connect requestor and cache_fe

        with m.If(processing_read):
            # When processing a read, set r_valid to read_data_valid.
            m.d.comb += requestor.r_valid.eq(cache_fe.read_data_valid)
            with m.If(cache_fe.read_data_valid):
                # When done, stop outputting read_data_valid as r_valid.
                m.d.sync += processing_read.eq(0)

        with m.If(processing_write):
            # When processing a write, set r_valid to port_ready (there is no explicit write done signal)
            m.d.comb += requestor.r_valid.eq(cache_fe.port_ready)
            with m.If(cache_fe.port_ready):
                # When done, stop outputting port_ready as r_valid
                m.d.sync += processing_write.eq(0)

        # When granting a request, remember what type of request we're currently processing.
        # This is intentionally placed after the blocks which set these variables to 0
        # again to support back to back requests (these changes will overwrite the previous
        # changes)
        with m.If(requestor.gnt):
            m.d.sync += processing_read.eq(requestor.wen)
            m.d.sync += processing_write.eq(~requestor.wen)

        # gnt may only be asserted when req gets asserted
        m.d.comb += requestor.gnt.eq(cache_fe.port_ready & requestor.req)
        # forward request
        m.d.comb += cache_fe.request_valid.eq(requestor.req)
        # cache can only do byte writes but not byte reads. write_strobe == 0 means read.
        m.d.comb += cache_fe.write_strobe.eq(Mux(requestor.wen, 0, requestor.be))
        m.d.comb += cache_fe.address.eq(requestor.add[2:])
        m.d.comb += cache_fe.write_data.eq(requestor.wdata)
        m.d.comb += requestor.r_rdata.eq(cache_fe.read_data)
        m.d.comb += requestor.r_opc.eq(0)  # Errors are not supported by the cache
        m.d.comb += cache_fe.flush.eq(0)  # Core doesn't use flush

        # Connect cache_be and target

        with m.If(read_sent & target.r_valid):
            # Set read_answered if read_sent and rvalid
            m.d.sync += read_answered.eq(1)
            # Also buffer the r_rdata since it may change
            m.d.sync += read_data_buffer.eq(target.r_rdata)

        with m.If(target.req & target.gnt):
            # when a new request gets granted, clear read_answered
            # this has to overwrite setting read_answered to 1 after receiving r_valid
            # to allow back-to-back requests
            m.d.sync += read_answered.eq(0)
            # also remember if we sent a read
            m.d.sync += read_sent.eq(target.wen)

        with m.If(read_sent):
            with m.If(~read_answered):
                # set read_data_valid to r_valid when a read request was
                # sent but not yet answered
                m.d.comb += cache_be.read_data_valid.eq(target.r_valid)
                # also hand out the target r_rdata
                m.d.comb += cache_be.read_data.eq(target.r_rdata)
            with m.Else():
                # r_valid will only be 1 for one cycle, but read_data_valid
                # has to be kept high until the next request
                m.d.comb += cache_be.read_data_valid.eq(1)
                # hand out the buffered read data
                m.d.comb += cache_be.read_data.eq(read_data_buffer)

        # Connect the other, simpler signals
        m.d.comb += cache_be.port_ready.eq(target.gnt)
        m.d.comb += target.req.eq(cache_be.request_valid)
        m.d.comb += target.be.eq(Mux(cache_be.write_strobe.any(), cache_be.write_strobe, -1))
        m.d.comb += target.wen.eq(~cache_be.write_strobe.any())
        m.d.comb += target.add.eq(Cat(C(0, unsigned(2)), cache_be.address))
        m.d.comb += target.wdata.eq(cache_be.write_data)

        return m
