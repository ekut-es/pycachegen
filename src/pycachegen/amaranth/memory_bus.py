from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out


class MemoryBusSignature(wiring.Signature):
    def __init__(self, address_width: int, data_width: int, bytes_per_word: int):
        self.address_width = address_width
        self.data_width = data_width
        self.bytes_per_word = bytes_per_word
        super().__init__(
            [
                ("address", Out(address_width)),
                ("write_data", Out(data_width)),
                ("write_strobe", Out(bytes_per_word)),
                ("request_valid", Out(1)),
                ("read_data", In(data_width)),
                ("read_data_valid", In(1)),
                ("port_ready", In(1)),
                ("flush", Out(1)),
            ]
        )

    def __eq__(self, other):
        return (
            isinstance(other, MemoryBusSignature)
            and self.address_width == other.address_width
            and self.data_width == other.data_width
            and self.bytes_per_word == other.bytes_per_word
        )

    def __repr__(self):
        return f"MemoryBusSignature({self.address_width}, {self.data_width}, {self.bytes_per_word})"

    def create(self, *, path=None, src_loc_at=0):
        return MemoryBusInterface(self, path=path, src_loc_at=1 + src_loc_at)


class MemoryBusInterface(wiring.PureInterface):
    def is_read_request(self):
        return self.request_valid & (self.write_strobe == 0)

    def is_write_request(self):
        return self.request_valid & (self.write_strobe != 0)
