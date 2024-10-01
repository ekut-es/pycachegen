from amaranth import *
from amaranth.lib import wiring, data
from amaranth.lib.memory import Memory
from amaranth.lib.wiring import In, Out
from pycachegen.cache_config_validation import InternalMemoryConfig
from pycachegen.amaranth.memory_bus import MemoryBusSignature


class MainMemory(wiring.Component):
    def __init__(self, config: InternalMemoryConfig) -> None:
        self.config = config
        self.bytes_per_word = config.DATA_WIDTH // config.BYTE_SIZE

        super().__init__(
            {
                "mem_if": In(
                    MemoryBusSignature(
                        address_width=config.ADDRESS_WIDTH,
                        data_width=config.DATA_WIDTH,
                        bytes_per_word=self.bytes_per_word,
                    )
                )
            }
        )

    def elaborate(self, platform) -> Module:
        m = Module()

        processing_request = Signal(1)  # whether a request is currently being processed
        m.d.comb += self.mem_if.port_ready.eq(~processing_request)
        request_type = Signal(1)  # type of current request (read: 0, write: 1)
        latency_counter = Signal(
            range(max(self.config.READ_LATENCY, self.config.WRITE_LATENCY))
        )
        # align address for Amaranth Memory with specified memory range
        aligned_address = Signal(
            range(0, self.config.MAX_ADDRESS - self.config.MIN_ADDRESS)
        )
        m.d.comb += aligned_address.eq(self.mem_if.address - self.config.MIN_ADDRESS)

        m.submodules.data_memory = data_memory = Memory(
            shape=unsigned(self.config.DATA_WIDTH),
            depth=(self.config.MAX_ADDRESS - self.config.MIN_ADDRESS),
            init=[],
        )

        write_port = data_memory.write_port(granularity=self.config.BYTE_SIZE)
        m.d.comb += write_port.addr.eq(aligned_address)
        m.d.comb += write_port.data.eq(self.mem_if.write_data)

        read_port = data_memory.read_port()
        m.d.comb += read_port.addr.eq(aligned_address)
        m.d.comb += self.mem_if.read_data.eq(read_port.data)

        with m.If(~processing_request):
            with m.If(
                self.mem_if.request_valid
                & (self.mem_if.address >= self.config.MIN_ADDRESS)
                & (self.mem_if.address < self.config.MAX_ADDRESS)
            ):
                # Buffer inputs
                m.d.sync += processing_request.eq(1)
                m.d.sync += request_type.eq(self.mem_if.write_strobe.any())

                # Reset response
                m.d.sync += self.mem_if.read_data_valid.eq(0)

                # Increment latency counter
                m.d.sync += latency_counter.eq(latency_counter + 1)

                # Initiate read/write
                m.d.sync += write_port.en.eq(self.mem_if.write_strobe)
                m.d.sync += read_port.en.eq(~self.mem_if.write_strobe.any())
        with m.Else():
            # clear enable on read/write ports
            m.d.sync += read_port.en.eq(0)
            m.d.sync += write_port.en.eq(0)
            with m.If(
                (
                    (request_type == 0)
                    & (latency_counter == self.config.READ_LATENCY - 1)
                )
                | (
                    (request_type == 1)
                    & (latency_counter == self.config.WRITE_LATENCY - 1)
                )
            ):
                # Reset internal registers
                m.d.sync += processing_request.eq(0)
                m.d.sync += latency_counter.eq(0)
                # Set correct response
                m.d.sync += self.mem_if.read_data_valid.eq(~request_type)
            with m.Else():
                m.d.sync += latency_counter.eq(latency_counter + 1)

        return m
