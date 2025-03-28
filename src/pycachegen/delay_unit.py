from amaranth import Module, Mux, Signal
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out

from pycachegen.memory_bus import MemoryBusSignature


class DelayUnit(wiring.Component):
    def __init__(
        self, mem_signature: MemoryBusSignature, read_delay: int, write_delay: int
    ):
        """Delays incoming requests by the specified amount of cycles.

        Args:
            mem_signature (MemoryBusSignature): Signature of the bus.
            read_delay (int): Delay for read requests.
            write_delay (int): Delay for write requests.
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
        flush = Signal()

        delay_reached = Signal()
        m.d.comb += delay_reached.eq(
            delay == (Mux(write_strobe.any(), self.write_delay, self.read_delay) - 1)
        )

        with m.If(state == 0):
            # idle
            # accept new requests and pass the response
            # from the target on to the requestor
            m.d.comb += requestor.port_ready.eq(1)
            m.d.comb += requestor.read_data.eq(target.read_data)
            m.d.comb += requestor.read_data_valid.eq(target.read_data_valid)
            with m.If(requestor.request_valid | requestor.flush):
                m.d.sync += address.eq(requestor.address)
                m.d.sync += write_data.eq(requestor.write_data)
                m.d.sync += write_strobe.eq(requestor.write_strobe)
                m.d.sync += request_valid.eq(requestor.request_valid)
                m.d.sync += flush.eq(requestor.flush)
                m.d.sync += state.eq(1)
        with m.Else():
            with m.If(~delay_reached):
                m.d.sync += delay.eq(delay + 1)
            with m.Else():
                # delay reached, send the request
                m.d.comb += target.address.eq(address)
                m.d.comb += target.write_data.eq(write_data)
                m.d.comb += target.write_strobe.eq(write_strobe)
                m.d.comb += target.request_valid.eq(request_valid)
                m.d.comb += target.flush.eq(flush)
                with m.If(target.port_ready):
                    # target ready to process request, go back to idle
                    m.d.sync += state.eq(0)
                    m.d.sync += delay.eq(0)

        return m
