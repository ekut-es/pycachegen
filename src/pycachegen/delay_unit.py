from amaranth import Cat, Module, Mux, Signal
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out
from amaranth.utils import exact_log2

from .cache_config import DelayConfig
from .interfaces import MemoryBusSignature


class DelayUnit(wiring.Component):
    def __init__(self, mem_signature: MemoryBusSignature, delay_config: DelayConfig):
        """Delays incoming requests by the specified amount of cycles.

        This module can be used to simulate slower memories. It is only a model and does not try to mimic the exact
        timing behavior of any particular memory.

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

        The burst mode is a simple approximation to the burst mode on real memories. It will not make the delay unit
        automatically spit out x words - instead it will change the delay for subsequent addresses if they go to the
        correct addresses. For the first request, the normal
        timing will be used. If the next request uses the next address (the one after the previous address) and it is
        still within the burst block (defined by the burst block size), it will use the burst timing. Note that burst
        blocks are aligned, meaning that the blocks start at address 0 and are non-overlapping. When the end of a block
        is reached, the burst continues by wrapping around to the first address of the block. After all addresses of a
        block have been accessed (in the correct order), the burst stops. Subsequent accesses to any address will use
        the normal timing again, but they will of course start a new burst operation to potentially speed up subsequent
        accesses. If a request does not match the address of the next burst access, the request will also be processed
        with the normal timing and it will also start a new burst operation itself.

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
            self.burst_block_address_width = exact_log2(self.burst_block_size)
            self.address_upper_part_width = mem_signature.address_width - self.burst_block_address_width
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

        delay_reached = Signal()
        if self.use_burst_mode:
            # Handle the burst mode
            use_burst_timing = Signal()
            burst_block_address = Signal(self.address_upper_part_width)
            burst_word_address = Signal(self.burst_block_address_width)
            burst_next_address = Signal(self.mem_signature.address_width)
            m.d.comb += burst_next_address.eq(Cat(burst_word_address, burst_block_address))
            burst_counter = Signal(self.burst_block_address_width)
            burst_active = Signal()
            m.d.comb += use_burst_timing.eq(burst_active & (address == burst_next_address))

            # Control the burst signals
            # with m.If((state == 0) & ~requestor.request_valid):
            #     # We're awaiting a new request but there is no new request -> end the burst
            #     m.d.sync += burst_active.eq(0)
            with m.If((state == 1) & delay_reached & target.port_ready):
                # We're sending a new request to the target -> update the burst block address
                m.d.sync += [
                    # remember the address of the burst block
                    burst_block_address.eq(address[-self.address_upper_part_width :]),
                    # remember the next word of the burst
                    burst_word_address.eq(address[: self.burst_block_address_width] + 1),
                ]
                with m.If(burst_active):
                    with m.If(use_burst_timing):
                        # We've used burst timing for this request
                        m.d.sync += [
                            # Increment the counter - overflow is wanted here for when the end of the burst is reached
                            burst_counter.eq(burst_counter + 1),
                            # Reset burst_active when we've reached the end of the block
                            burst_active.eq(burst_counter != -1),
                        ]
                    with m.Else():
                        # We were not using burst timing, because the address did not match
                        # Therefore we start a new burst from the new address
                        m.d.sync += burst_counter.eq(1)
                with m.Else():
                    # burst was not active, so we activate it now
                    m.d.sync += [
                        burst_active.eq(1),
                        burst_counter.eq(1),
                    ]

            # Check if we've reached the correct delay
            with m.If(write_strobe.any()):
                m.d.comb += delay_reached.eq(
                    delay == (Mux(use_burst_timing, self.burst_write_delay, self.write_delay) - 1)
                )
            with m.Else():
                m.d.comb += delay_reached.eq(
                    delay == (Mux(use_burst_timing, self.burst_read_delay, self.read_delay) - 1)
                )
        else:
            # Use constant timing
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
        with m.If((state == 1) & delay_reached):
            m.d.comb += [
                target.address.eq(address),
                target.write_data.eq(write_data),
                target.write_strobe.eq(write_strobe),
                target.request_valid.eq(1),
            ]

        # Control path
        with m.If(state == 0):
            with m.If(accepting_request):
                m.d.sync += state.eq(1)
        with m.Elif(state == 1):
            with m.If(delay_reached & target.port_ready):
                m.d.sync += state.eq(0)

        return m
