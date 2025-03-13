from amaranth import *
from amaranth.lib import wiring, data
from amaranth.lib.memory import Memory
from amaranth.lib.wiring import In, Out
from amaranth.lib.fifo import SyncFIFO
from pycachegen.cache_config_validation import InternalMemoryConfig
from pycachegen.memory_bus import MemoryBusSignature, MemoryRequestLayout


class WriteBuffer(wiring.Component):
    def __init__(self, signature: MemoryBusSignature, depth: int):
        self.mem_signature = signature
        self.depth = depth
        self.request_layout = MemoryRequestLayout(signature)
        self.width = self.request_layout.size
        super().__init__({"fe": In(signature), "be": Out(signature)})

    def elaborate(self, platform) -> None:
        m = Module()

        # Always connect the read data from the BE to the FE
        m.d.comb += [
            self.fe.read_data.eq(self.be.read_data),
            self.fe.read_data_valid.eq(self.be.read_data_valid)
        ]

        # The actual FIFO buffer
        m.submodules.fifo = fifo = SyncFIFO(width=self.width, depth=self.depth)

        # Aggregate data for FIFO input
        fe_request = Signal(self.request_layout)
        m.d.comb += [
            fe_request.address.eq(self.fe.address),
            fe_request.write_data.eq(self.fe.write_data),
            fe_request.write_strobe.eq(self.fe.write_strobe),
        ]
        m.d.comb += fifo.w_data.eq(fe_request)

        # Disaggregate the FIFO output data
        be_request = Signal(self.request_layout)
        m.d.comb += be_request.eq(fifo.r_data)

        with m.If(self.fe.write_strobe.any()):
            # write -> buffer the request
            m.d.comb += fifo.w_en.eq(self.fe.request_valid)
            m.d.comb += self.fe.port_ready.eq(fifo.w_rdy)

        with m.If(fifo.r_level != 0):
            # There's a valid request in the FIFO, send it to the memory
            m.d.comb += [
                self.be.address.eq(be_request.address),
                self.be.write_data.eq(be_request.write_data),
                self.be.write_strobe.eq(be_request.write_strobe),
                self.be.request_valid.eq(1)
            ]
            m.d.comb += fifo.r_en.eq(self.be.port_ready)
        with m.Elif(~self.fe.write_strobe.any()):
            # The FIFO is empty and we have a read request -> send that
            m.d.comb += [
                self.be.address.eq(self.fe.address),
                self.be.write_strobe.eq(0),
                self.be.request_valid.eq(1)
            ]
            m.d.comb += self.fe.port_ready.eq(self.be.port_ready)

        return m
    