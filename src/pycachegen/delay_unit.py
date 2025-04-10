from amaranth import Module, Mux, Signal
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out

from .interfaces import MemoryBusSignature


class DelayUnit(wiring.Component):
    def __init__(
        self,
        mem_signature: MemoryBusSignature,
        read_delay: int,
        write_delay: int,
    ):
        """Delays incoming requests by the specified amount of cycles.

        This module will accept new requests and then buffer and delay them for the specified
        number of cycles. After that time, the request will be sent to the target. After the target
        has accepted the request, the response will be forwarded and a new request will be accepted
        if there is one. Because of this, the target must process each request within one cycle
        after accepting it. The request to the target will not change until it gets accepted, so
        the target may delay asserting port_ready until one cycle before it has finished processing
        the request.

        Also note that the flushes will not be delayed by this module. The flush and flush done signals
        will just pass through this module while it is in the idle state (not delaying any requests or
        waiting for a delayed request to be accepted by the target).

        Args:
            mem_signature (MemoryBusSignature): Signature of the bus.
            read_delay (int): Delay for read requests. Must be at least 1.
            write_delay (int): Delay for write requests. Must be at least 1.
        """
        assert read_delay >= 1 and write_delay >= 1
        self.mem_signature = mem_signature
        self.read_delay = read_delay
        self.write_delay = write_delay
        super().__init__({"requestor": In(mem_signature), "target": Out(mem_signature)})

    def elaborate(self, platform):
        m = Module()

        requestor = self.requestor
        target = self.target

        state = Signal()
        delay = Signal(range(max(self.read_delay, self.write_delay)))

        # Input buffers
        address = Signal(requestor.address.shape())
        write_data = Signal(requestor.write_data.shape())
        write_strobe = Signal(requestor.write_strobe.shape())
        request_valid = Signal()

        delay_reached = Signal()
        m.d.comb += delay_reached.eq(delay == (Mux(write_strobe.any(), self.write_delay, self.read_delay) - 1))

        with m.If(state == 0):
            # idle
            # accept new requests and pass the response
            # from the target on to the requestor
            m.d.comb += [
                requestor.port_ready.eq(1),
                requestor.read_data.eq(target.read_data),
                requestor.read_data_valid.eq(target.read_data_valid),
                # flushes will not be delayed by this module
                requestor.flush_done.eq(target.flush_done),
                target.flush.eq(requestor.flush),
            ]
            with m.If(requestor.request_valid & ~requestor.flush):
                m.d.sync += [
                    address.eq(requestor.address),
                    write_data.eq(requestor.write_data),
                    write_strobe.eq(requestor.write_strobe),
                    request_valid.eq(requestor.request_valid),
                    state.eq(1),
                ]
        with m.Else():
            with m.If(~delay_reached):
                m.d.sync += delay.eq(delay + 1)
            with m.Else():
                # delay reached, send the request
                m.d.comb += [
                    target.address.eq(address),
                    target.write_data.eq(write_data),
                    target.write_strobe.eq(write_strobe),
                    target.request_valid.eq(request_valid),
                ]
                with m.If(target.port_ready):
                    # target ready to process request, go back to idle
                    m.d.sync += [
                        state.eq(0),
                        delay.eq(0),
                    ]

        return m
