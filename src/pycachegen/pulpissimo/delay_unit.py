from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out

from pycachegen.pulpissimo.tcdm_signature import TCDMSignature


class DelayUnit(wiring.Component):

    def __init__(self, delay: int):
        """Delays the response for a memory request.

        Args:
            delay (int): Number of cycles by which a response should additionally be delayed. Must be greater than 0.
        """
        self.delay = delay
        super().__init__(
            # master: to main memory, slave: to cache
            {"master": Out(TCDMSignature()), "slave": In(TCDMSignature())}
        )

    def elaborate(self, platform):
        m = Module()
        # Always pass on some of the signals from the slave to the master
        m.d.comb += self.master.wen.eq(self.slave.wen)
        m.d.comb += self.master.be.eq(self.slave.be)
        m.d.comb += self.master.add.eq(self.slave.add)
        m.d.comb += self.master.wdata.eq(self.slave.wdata)

        # Whether we're waiting for a response from main memory
        awaiting_response = Signal()
        # Whether we're currently delaying the response to the cache
        delaying_response = Signal()
        # Counter for the delay
        delay_counter = Signal(range(self.delay))

        # buffers for the response
        r_rdata = Signal(unsigned(32))
        r_opc = Signal()

        with m.If(delaying_response):
            m.d.sync += delay_counter.eq(delay_counter + 1)
            with m.If(delay_counter == (self.delay - 1)):
                # desired delay was reached, hand out the response
                m.d.comb += self.slave.r_opc.eq(r_opc)
                m.d.comb += self.slave.r_rdata.eq(r_rdata)
                m.d.comb += self.slave.r_valid.eq(1)
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
            with m.If(self.master.r_valid):
                # Received a response, buffer it and start the delay counter.
                m.d.sync += r_rdata.eq(self.master.r_rdata)
                m.d.sync += r_opc.eq(self.master.r_opc)
                m.d.sync += awaiting_response.eq(0)
                m.d.sync += delaying_response.eq(1)

        return m