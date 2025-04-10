from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out


class TCDMSignature(wiring.Signature):
    def __init__(
        self,
    ):
        """
        Signature of the XBAR_TCDM_BUS interface.
        """
        super().__init__(
            [
                # Request Channel
                ("req", Out(1)),
                ("add", Out(32)),
                ("wen", Out(1)),
                ("wdata", Out(32)),
                ("be", Out(4)),
                ("gnt", In(1)),
                # Response Channel
                ("r_valid", In(1)),
                ("r_rdata", In(32)),
                ("r_opc", In(1)),
            ]
        )
