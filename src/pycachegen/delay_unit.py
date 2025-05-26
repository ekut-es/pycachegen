from amaranth import Module, Mux, Signal
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out
from amaranth.utils import exact_log2

from .cache_config import DelayConfig
from .interfaces import MemoryBusSignature


class DelayUnit(wiring.Component):
    def __init__(self, mem_signature: MemoryBusSignature, delay_config: DelayConfig):
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
            delay_config (DelayConfig): The configuration of the delay unit
        """
        self.mem_signature = mem_signature
        self.read_delay = delay_config.read_delay
        self.write_delay = delay_config.write_delay
        self.use_burst_mode = delay_config.use_burst_mode
        if self.use_burst_mode:
            self.burst_block_size = delay_config.burst_block_size
            self.burst_read_delay = delay_config.burst_read_delay
            self.burst_write_delay = delay_config.burst_write_delay
            self.burst_block_address_width = mem_signature.address_width - exact_log2(self.burst_block_size)
        super().__init__({"requestor": In(mem_signature), "target": Out(mem_signature)})

    def elaborate(self, platform):
        m = Module()

        requestor = self.requestor
        target = self.target

        # state 0: waiting for the next request
        # state 1: is currently delaying a request or waiting for the backend to get ready
        state = Signal()

        # Input buffers
        address = Signal(requestor.address.shape())
        write_data = Signal(requestor.write_data.shape())
        write_strobe = Signal(requestor.write_strobe.shape())

        # Counter for the delay
        delay = Signal(range(max(self.read_delay, self.write_delay)))

        # Determine whether we've reached the delay, which also depends on whether we're using burst mode or not
        delay_reached = Signal()
        if self.use_burst_mode:
            address_in_burst_block = Signal()
            burst_block_address = Signal(self.burst_block_address_width)
            m.d.comb += address_in_burst_block.eq(address[-self.burst_block_address_width :] == burst_block_address)
            with m.If(write_strobe.any()):
                m.d.comb += delay_reached.eq(
                    delay == (Mux(address_in_burst_block, self.burst_write_delay, self.write_delay) - 1)
                )
            with m.Else():
                m.d.comb += delay_reached.eq(
                    delay == (Mux(address_in_burst_block, self.burst_read_delay, self.read_delay) - 1)
                )
        else:
            m.d.comb += delay_reached.eq(delay == (Mux(write_strobe.any(), self.write_delay, self.read_delay) - 1))

        with m.If(state == 0):
            # Reset the delay when waiting for the next request
            m.d.sync += delay.eq(0)
        with m.Elif((state == 1) & ~delay_reached):
            # Increment the delay while delaying a request
            m.d.sync += delay.eq(delay + 1)

        # Output the response to the requestor and forward flush requests
        # The requestor should not send the next request before having received the response
        with m.If(state == 0):
            m.d.comb += [
                requestor.port_ready.eq(1),
                requestor.read_data.eq(target.read_data),
                requestor.read_data_valid.eq(target.read_data_valid),
                # flushes will not be delayed by this module
                requestor.flush_done.eq(target.flush_done),
                target.flush.eq(requestor.flush),
            ]

        # Determine whether we're accepting the next request
        accepting_request = Signal()
        m.d.comb += accepting_request.eq((state == 0) & requestor.request_valid & ~requestor.flush)

        # Buffer the inputs when accepting a request
        with m.If(accepting_request):
            m.d.sync += [
                address.eq(requestor.address),
                write_data.eq(requestor.write_data),
                write_strobe.eq(requestor.write_strobe),
            ]

        # Send the request to the backend when the delay is reached
        with m.If(state == 1 & delay_reached):
            m.d.comb += [
                target.address.eq(address),
                target.write_data.eq(write_data),
                target.write_strobe.eq(write_strobe),
                target.request_valid.eq(1),
            ]
            # update the last address when using burst mode
            if self.use_burst_mode:
                m.d.sync += burst_block_address.eq(address[-self.burst_block_address_width :])

        # Control path
        with m.If(state == 0):
            with m.If(accepting_request):
                m.d.sync += state.eq(1)
        with m.Elif(state == 1):
            with m.If(delay_reached & target.port_ready):
                m.d.sync += state.eq(0)

        return m
