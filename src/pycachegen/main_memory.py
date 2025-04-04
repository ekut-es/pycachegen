from amaranth import Module, Mux, Signal, unsigned
from amaranth.lib import data, wiring
from amaranth.lib.memory import Memory
from amaranth.lib.wiring import In, Out

from .cache_config import InternalMemoryConfig
from .interfaces import MemoryBusSignature


class MainMemory(wiring.Component):
    def __init__(self, config: InternalMemoryConfig) -> None:
        """A simple memory with the MemoryBusInterface.

        This memory uses the amaranth.lib.memory.Memory which is well suited for FPGAs
        (BRAM should usually be inferred from it).

        Args:
            config (InternalMemoryConfig): Configuration of the memory.
        """
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

        # Track whether the last request was a read so that we can hand out the read
        # data and it as valid when appropriate
        last_request_was_read = Signal()
        with m.If(last_request_was_read):
            m.d.comb += [
                self.fe.read_data_valid.eq(1),
                self.fe.read_data.eq(read_port.data),
            ]

        # Connect the inputs of read_port and write_port
        with m.If(
            (self.fe.address >= self.config.min_address)
            & (self.fe.address < self.config.max_address)
        ):
            with m.If(self.fe.request_valid):
                m.d.sync += last_request_was_read.eq(~self.fe.write_strobe.any())
            m.d.comb += [
                # always responds within one cycle and is thus always ready
                self.fe.port_ready.eq(1),
                read_port.addr.eq(aligned_address),
                read_port.en.eq(self.fe.is_read_request()),
                write_port.addr.eq(aligned_address),
                write_port.data.eq(self.fe.write_data),
                write_port.en.eq(Mux(self.fe.request_valid, self.fe.write_strobe, 0)),
            ]

        return m
