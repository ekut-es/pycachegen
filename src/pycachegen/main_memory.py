from amaranth import Module, Mux, Signal, unsigned
from amaranth.lib import wiring
from amaranth.lib.memory import Memory
from amaranth.lib.wiring import In

from .cache_config import InternalMemoryConfig


class MainMemory(wiring.Component):
    def __init__(self, config: InternalMemoryConfig) -> None:
        """A simple memory with the MemoryBusInterface.

        This memory uses the amaranth.lib.memory.Memory which is well suited for FPGAs
        (BRAM should usually be inferred from it).

        Args:
            config (InternalMemoryConfig): Configuration of the memory.
        """
        self.config = config

        super().__init__({"fe": In(config.memory_bus_signature)})

    def elaborate(self, platform) -> Module:
        m = Module()

        m.d.comb += self.fe.flush_done.eq(1)

        # Create data memory
        m.submodules.data_memory = data_memory = Memory(
            shape=unsigned(self.config.data_width),
            depth=(2**self.config.address_width),
            init=[],
        )

        write_port = data_memory.write_port(granularity=self.config.byte_size)
        read_port = data_memory.read_port()

        # Track whether the last request was a read so that we can hand out the read
        # data and it as valid when appropriate
        last_request_was_read = Signal()
        with m.If(self.fe.request_valid):
            m.d.sync += last_request_was_read.eq(~self.fe.write_strobe.any())
        with m.If(last_request_was_read):
            m.d.comb += [
                self.fe.read_data_valid.eq(1),
                self.fe.read_data.eq(read_port.data),
            ]

        # Connect the inputs of read_port and write_port
        m.d.comb += [
            # always responds within one cycle and is thus always ready
            self.fe.port_ready.eq(1),
            read_port.addr.eq(self.fe.address),
            read_port.en.eq(self.fe.is_read_request()),
            write_port.addr.eq(self.fe.address),
            write_port.data.eq(self.fe.write_data),
            write_port.en.eq(Mux(self.fe.request_valid, self.fe.write_strobe, 0)),
        ]

        return m
