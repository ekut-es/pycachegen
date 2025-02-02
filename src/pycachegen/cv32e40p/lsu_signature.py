from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out


class LSUSignature(wiring.Signature):
    def __init__(
        self,
    ):
        """
        Signature of the Load-Store-Unit (LSU) interface.

        See https://docs.openhwgroup.org/projects/cv32e40p-user-manual/en/latest/load_store_unit.html#load-store-unit
        """
        super().__init__(
            [
                ("req", Out(1)),
                ("gnt", In(1)),
                ("rvalid", In(1)),
                ("we", Out(1)),
                ("be", Out(4)),
                ("addr", Out(32)),
                ("wdata", Out(32)),
                ("rdata", In(32)),
                ("err", In(1)),
            ]
        )
