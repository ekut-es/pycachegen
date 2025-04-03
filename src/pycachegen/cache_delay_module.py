from amaranth import Module, Signal, unsigned
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out

from .interfaces import MemoryBusSignature


class CacheDelayModule(wiring.Component):
    def __init__(
        self, bus_signature: MemoryBusSignature, hit_latency: int, miss_latency: int
    ):
        """A module for adding an additional delay until a cache port becomes ready
        and until the read data becomes ready based on whether the cache registered a hit
        or a miss.

        Args:
            bus_signature (MemoryBusSignature): The signature of the cache port.
            hit_latency (int): The additional delay for hits.
            miss_latency (int): The additional delay for misses.
        """
        self.hit_latency = hit_latency
        self.miss_latency = miss_latency
        self.latency_range = range(max(self.hit_latency, self.miss_latency))

        ports = {
            "fe": In(bus_signature),
            "hit_o": Out(unsigned(1)),
            "be": Out(bus_signature),
            "hit_i": In(unsigned(1)),
        }
        super().__init__(ports)

    def elaborate(self, platform):
        m = Module()

        busy = Signal()

        # counter for making the FE port ready
        ready_latency_counter = Signal(self.latency_range)
        # counter for setting the FE read data valid signal
        read_data_latency_counter = Signal(self.latency_range)

        # Always tell the FE whether the BE has had a hit
        m.d.comb += self.hit_o.eq(self.hit_i)

        with m.If(busy):
            # Increment ready counter if BE is ready
            with m.If(self.be.port_ready):
                m.d.sync += ready_latency_counter.eq(ready_latency_counter + 1)
                # Get ready again if ready counter has reached its limit
                with m.If(
                    (self.hit_i & (ready_latency_counter == (self.hit_latency - 1)))
                    | (~self.hit_i & (ready_latency_counter == (self.miss_latency - 1)))
                ):
                    m.d.sync += ready_latency_counter.eq(0)
                    m.d.sync += busy.eq(0)

            # Increment read data counter if the BE read data is valid
            with m.If(self.be.read_data_valid):
                m.d.sync += read_data_latency_counter.eq(read_data_latency_counter + 1)
                # Hand out the read data if the read data counter has reached its limit
                with m.If(
                    (self.hit_i & (read_data_latency_counter == (self.hit_latency - 1)))
                    | (
                        ~self.hit_i
                        & (read_data_latency_counter == (self.miss_latency - 1))
                    )
                ):
                    m.d.sync += self.fe.read_data.eq(self.be.read_data)
                    m.d.sync += self.fe.read_data_valid.eq(self.be.read_data_valid)
        with m.Else():
            # Forward requests to the BE
            m.d.comb += self.be.request_valid.eq(self.fe.request_valid)
            m.d.comb += self.be.address.eq(self.fe.address)
            m.d.comb += self.be.write_strobe.eq(self.fe.write_strobe)
            m.d.comb += self.be.write_data.eq(self.fe.write_data)
            m.d.comb += self.be.flush.eq(self.fe.flush)

            # Mark the FE port as ready
            m.d.comb += self.fe.port_ready.eq(self.be.port_ready)

            # If a request comes in and the BE is ready, switch to the busy state
            # (The BE port should always be ready if we're not busy, but I check it anyway)
            with m.If(self.be.port_ready & (self.fe.request_valid | self.fe.flush)):
                m.d.sync += busy.eq(1)
                m.d.sync += self.fe.read_data_valid.eq(
                    0
                )  # invalidate previous response
                # reset the counters (the read data counter might not be 0)
                m.d.sync += ready_latency_counter.eq(0)
                m.d.sync += read_data_latency_counter.eq(0)

        return m
