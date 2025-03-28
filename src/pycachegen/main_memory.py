from amaranth import *
from amaranth.lib import wiring, data
from amaranth.lib.memory import Memory
from amaranth.lib.wiring import In, Out
from pycachegen.cache_config import InternalMemoryConfig
from pycachegen.memory_bus import MemoryBusSignature


class MainMemory(wiring.Component):
    """
    module to simulate a main memory with configurable latency
    used to simulate caches without the need for external memory libraries
    """
    def __init__(self, config: InternalMemoryConfig) -> None:
        self.config = config

        super().__init__(
            {
                "fe": In(
                    MemoryBusSignature(
                        address_width=config.address_width,
                        data_width=config.data_width,
                        bytes_per_word=config.bytes_per_word,
                    )
                )
            }
        )

    def elaborate(self, platform) -> Module:
        m = Module()

        # whether a request is currently being processed
        processing_request = Signal(1)
        m.d.comb += self.fe.port_ready.eq(~processing_request)
        # type of current request (read: 0, write: 1)
        request_type = Signal(1)
        # counter for counting the execution time of a request
        latency_counter = Signal(
            range(max(self.config.read_latency, self.config.write_latency))
        )
        # align address for Amaranth Memory with specified memory range
        aligned_address = Signal(
            range(0, self.config.max_address - self.config.min_address)
        )
        m.d.comb += aligned_address.eq(self.fe.address - self.config.min_address)

        # Create data memory
        m.submodules.data_memory = data_memory = Memory(
            shape=unsigned(self.config.data_width),
            depth=(self.config.max_address - self.config.min_address),
            init=[],
        )

        write_port = data_memory.write_port(granularity=self.config.byte_size)

        read_port = data_memory.read_port()
        m.d.comb += self.fe.read_data.eq(read_port.data)

        with m.If(~processing_request):
            with m.If(
                self.fe.request_valid
                & (self.fe.address >= self.config.min_address)
                & (self.fe.address < self.config.max_address)
            ):
                # Buffer inputs
                m.d.sync += processing_request.eq(1)
                m.d.sync += request_type.eq(self.fe.write_strobe.any())

                # Reset response
                m.d.sync += self.fe.read_data_valid.eq(0)

                # Increment latency counter
                m.d.sync += latency_counter.eq(latency_counter + 1)

                # Initiate read/write
                m.d.sync += write_port.en.eq(self.fe.write_strobe)
                m.d.sync += write_port.addr.eq(aligned_address)
                m.d.sync += write_port.data.eq(self.fe.write_data)
                m.d.sync += read_port.en.eq(~self.fe.write_strobe.any())
                m.d.sync += read_port.addr.eq(aligned_address)
        with m.Else():
            # clear enable on read/write ports
            m.d.sync += read_port.en.eq(0)
            m.d.sync += write_port.en.eq(0)
            with m.If(
                (
                    (request_type == 0)
                    & (latency_counter == self.config.read_latency - 1)
                )
                | (
                    (request_type == 1)
                    & (latency_counter == self.config.write_latency - 1)
                )
            ):
                # Reset internal registers
                m.d.sync += processing_request.eq(0)
                m.d.sync += latency_counter.eq(0)
                # Set correct response
                m.d.sync += self.fe.read_data_valid.eq(~request_type)
            with m.Else():
                m.d.sync += latency_counter.eq(latency_counter + 1)

        return m
