from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out

from pycachegen.memory_bus import MemoryBusSignature


class DelayUnit(wiring.Component):
    def __init__(
        self, mem_signature: MemoryBusSignature, read_delay: int, write_delay: int
    ):
        assert read_delay >= 1 and write_delay >= 1
        self.mem_signature = mem_signature
        self.read_delay = read_delay
        self.write_delay = write_delay
        super().__init__({"requestor": In(mem_signature), "target": Out(mem_signature)})

    def elaborate(self, platform):
        m = Module()

        requestor = self.requestor
        target = self.target

        ## Internal State
        # Whether we're awaiting a response from the target for a granted request
        awaiting_response = Signal()
        # Whether we're currently delaying the response to the requestor
        delaying_response = Signal()
        # type of the current request. 0 = read, 1 = write
        request_type = Signal()
        # Counter for the delay
        delay_counter = Signal(range(max(self.read_delay, self.write_delay)))

        # whether we've reached the delay for the current request
        delay_reached = Signal()
        m.d.comb += delay_reached.eq(
            (request_type & (delay_counter == self.write_delay))
            | (~request_type & (delay_counter == self.read_delay))
        )

        # whether we're awaiting or delaying a response
        busy = Signal()
        m.d.comb += busy.eq(awaiting_response | (delaying_response & ~delay_reached))

        # Always connect some of the signals from the requestor to the target
        m.d.comb += target.address.eq(requestor.address)
        m.d.comb += target.write_data.eq(requestor.write_data)
        m.d.comb += target.write_strobe.eq(requestor.write_strobe)

        with m.If(delaying_response):
            with m.If(delay_reached):
                # delay reached, reset state
                m.d.sync += delay_counter.eq(0)
                m.d.sync += delaying_response.eq(0)
            with m.Else():
                m.d.sync += delay_counter.eq(delay_counter + 1)

        with m.If(~busy):
            # Not awaiting or delaying a response -> let the remaining signals pass through
            m.d.comb += self.target.request_valid.eq(self.requestor.request_valid)
            m.d.comb += self.requestor.port_ready.eq(self.target.port_ready)
            m.d.comb += self.requestor.read_data.eq(target.read_data)
            m.d.comb += self.requestor.read_data_valid.eq(target.read_data_valid)
            with m.If(self.requestor.request_valid & self.target.port_ready):
                # the requestor has sent a request
                m.d.sync += awaiting_response.eq(1)

        return m