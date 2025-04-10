from amaranth import Array, Module, Mux, Signal, unsigned
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out

from .interfaces import MemoryBusSignature, MemoryRequestLayout
from .utils import one_hot_encode


def _incr(signal, modulo):
    if modulo == 2 ** len(signal):
        return signal + 1
    else:
        return Mux(signal == modulo - 1, 0, signal + 1)


class WriteBuffer(wiring.Component):
    def __init__(self, *, signature: MemoryBusSignature, depth: int):
        """A write buffer with configurable depth.

        Writes to the same address will be merged. Reads that can be fulfilled
        by the data in the buffer will be answered in 1 cycle. Reads with
        addresses for which there are no writes in the buffer will have priority
        over writes from the buffer. Reads for which there is a write with partial
        write strobe will be delayed.

        Args:
            signature (MemoryBusSignature): The signature of the memory bus.
            depth (int): The number of write requests that can be buffered.
        """
        self.mem_signature = signature
        self.depth = depth
        self.request_layout = MemoryRequestLayout(signature)
        self.width = self.request_layout.size
        self.byte_size = signature.data_width // signature.bytes_per_word
        super().__init__({"fe": In(signature), "be": Out(signature)})

    def elaborate(self, platform):
        m = Module()

        level = Signal(range(self.depth + 1))
        write_ptr = Signal(range(self.depth))
        read_ptr = Signal(range(self.depth))

        storage = Array([Signal(self.request_layout, name=f"storage[{i}]") for i in range(self.depth)])

        addr_match_vec = Signal(unsigned(self.depth))
        for idx, el in enumerate(storage):
            # Find out whether the requested address is in the FIFO or not
            # only look at valid entries of the FIFO!!!
            m.d.comb += addr_match_vec[idx].eq(
                (el.address == self.fe.address)
                & (
                    (level == self.depth)
                    | Mux(
                        read_ptr <= write_ptr,
                        (idx >= read_ptr) & (idx < write_ptr),
                        (idx >= read_ptr) | (idx < write_ptr),
                    )
                )
            )
        addr_match_idx = Signal(range(self.depth))
        m.d.comb += addr_match_idx.eq(one_hot_encode(m, addr_match_vec))

        # Buffers for data read from FIFO
        read_data_buffer = Signal(unsigned(self.mem_signature.data_width))
        read_data_valid_buffer = Signal()
        # Select where the FE read data comes from
        read_data_source = Signal()  # 0 = BE, 1 = Buffer
        with m.If(read_data_source):
            m.d.comb += [
                self.fe.read_data.eq(read_data_buffer),
                self.fe.read_data_valid.eq(read_data_valid_buffer),
            ]
        with m.Else():
            m.d.comb += [
                self.fe.read_data.eq(self.be.read_data),
                self.fe.read_data_valid.eq(self.be.read_data_valid),
            ]

        fe_read = self.fe.request_valid & ~self.fe.write_strobe.any()
        fe_write = self.fe.request_valid & self.fe.write_strobe.any()
        fifo_read = Signal()
        fifo_write = Signal()

        with m.If(fe_read & ~addr_match_vec.any()):
            # Send FE read request directly to BE, the requested address is not in the FIFO
            m.d.comb += [
                self.be.address.eq(self.fe.address),
                self.be.write_strobe.eq(0),
                self.be.request_valid.eq(1),
                self.fe.port_ready.eq(self.be.port_ready),
            ]
            m.d.sync += read_data_source.eq(0)
        with m.Else():
            with m.If(fe_read & addr_match_vec.any() & storage[addr_match_idx].write_strobe.all()):
                # Read request can be answered by buffer because the address is in the buffer and
                # the write strobe there is all ones
                # if the write strobe is not all ones, the read has to wait until that request has left the buffer
                m.d.comb += self.fe.port_ready.eq(1)
                m.d.sync += [
                    read_data_source.eq(1),
                    read_data_buffer.eq(storage[addr_match_idx].write_data),
                    read_data_valid_buffer.eq(1),
                ]

            with m.If(fe_write):
                with m.If(addr_match_vec.any() & ((~fifo_read) | (read_ptr != addr_match_idx))):
                    # Write to an address thats already in the buffer and the element in
                    # the buffer is not currently being sent to the main memory
                    # Merge the two writes
                    fifo_req = storage[addr_match_idx]
                    # Merge write strobe
                    m.d.sync += fifo_req.write_strobe.eq(fifo_req.write_strobe | self.fe.write_strobe)
                    # Merge write data
                    for idx, new_strobe_bit in enumerate(self.fe.write_strobe):
                        new_byte = self.fe.write_data.word_select(idx, self.byte_size)
                        data_byte_in_fifo = fifo_req.write_data.word_select(idx, self.byte_size)
                        with m.If(new_strobe_bit):
                            m.d.sync += data_byte_in_fifo.eq(new_byte)
                    # Accept FE request
                    m.d.comb += self.fe.port_ready.eq(1)
                with m.Elif((level != self.depth) | fifo_read):
                    # Write to an address that is not already in the buffer and the buffer is not
                    # yet full -> Put write into buffer
                    m.d.comb += [self.fe.port_ready.eq(1), fifo_write.eq(1)]
                    m.d.sync += [
                        storage[write_ptr].address.eq(self.fe.address),
                        storage[write_ptr].write_data.eq(self.fe.write_data),
                        storage[write_ptr].write_strobe.eq(self.fe.write_strobe),
                    ]

            with m.If(level > 0):
                # Send buffered request to BE
                req = storage[read_ptr]
                m.d.comb += [
                    self.be.address.eq(req.address),
                    self.be.write_strobe.eq(req.write_strobe),
                    self.be.write_data.eq(req.write_data),
                    self.be.request_valid.eq(1),
                    fifo_read.eq(self.be.port_ready),
                ]

        # Update pointers
        with m.If(fifo_write):
            m.d.sync += write_ptr.eq(_incr(write_ptr, self.depth))
        with m.If(fifo_read):
            m.d.sync += read_ptr.eq(_incr(read_ptr, self.depth))

        # Update level
        with m.If(fifo_write & ~fifo_read):
            m.d.sync += level.eq(level + 1)
        with m.If(~fifo_write & fifo_read):
            m.d.sync += level.eq(level - 1)

        return m
