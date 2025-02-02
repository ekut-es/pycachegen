from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out

from pycachegen.cv32e40p.lsu_signature import LSUSignature


class DelayUnit(wiring.Component):

    def __init__(self, delay: int):
        """Delays the response for a memory request.

        Args:
            delay (int): Number of cycles by which a response should additionally be delayed. Must be greater than 0.
        """
        self.delay = delay
        super().__init__(
            # master: to main memory, slave: to cache
            {"master": Out(LSUSignature()), "slave": In(LSUSignature())}
        )

    def elaborate(self, platform):
        m = Module()
        # Always pass on some of the signals from the slave to the master
        m.d.comb += self.master.we.eq(self.slave.we)
        m.d.comb += self.master.be.eq(self.slave.be)
        m.d.comb += self.master.addr.eq(self.slave.addr)
        m.d.comb += self.master.wdata.eq(self.slave.wdata)

        # TODO Remove these lines if they're not needed
        # m.d.comb += self.slave.err.eq(0)
        # m.d.comb += self.slave.rdata.eq(0)
        # m.d.comb += self.slave.rvalid.eq(0)

        # Whether we're waiting for a response from main memory
        awaiting_response = Signal()
        # Whether we're currently delaying the response to the cache
        delaying_response = Signal()
        # Counter for the delay
        delay_counter = Signal(range(self.delay))

        # buffers for the response
        rdata = Signal(unsigned(32))
        err = Signal()

        with m.If(delaying_response):
            m.d.sync += delay_counter.eq(delay_counter + 1)
            with m.If(delay_counter == (self.delay - 1)):
                # desired delay was reached, hand out the response
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
                # Received a response, buffer it and start the delay counter.
                m.d.sync += rdata.eq(self.master.rdata)
                m.d.sync += err.eq(self.master.err)
                m.d.sync += awaiting_response.eq(0)
                m.d.sync += delaying_response.eq(1)

        return m