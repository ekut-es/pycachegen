from enum import Enum

from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out

from pycachegen.cache_config_validation import InternalCacheConfig
from pycachegen.memory_bus import MemoryBusInterface


class AdapterState(Enum):
    READY = 0
    WAIT = 1

class CV32E40PAdapter(wiring.Component):
    def __init__(self, cache_config: InternalCacheConfig):
        super().__init__(
            {
                # Core <-> Adapter
                "req_i": In(1),
                "gnt_o": Out(1),
                "rvalid_o": Out(1),
                "we_i": In(1),
                "be_i": In(4),
                "addr_i": In(32),
                "wdata_i": In(32),
                "rdata_o": Out(32),
                # Adapter <-> Cache
                "cache_if": Out(cache_config.fe_signature),
            }
        )

    def elaborate(self, platform):
        m = Module()

        state = Signal(AdapterState)

        """
        https://docs.openhwgroup.org/projects/cv32e40x-user-manual/en/latest/load_store_unit.html
        https://github.com/openhwgroup/obi/blob/072d9173c1f2d79471d6f2a10eae59ee387d4c6f/OBI-v1.6.0.pdf

        TODO: Herausfinden, ob die LSU im Core oder außerhalb sitzt. Die LSU handelt z.B. misaligned
        accesses, was der Cache nicht kann.

        Der OBI PULP Adapter hört die Request vom Memory und die rvalid und gnt vom memory mit
        und entscheidet, wann eine request an den memory weitergegeben werden darf:

        WAIT_GNT:
        Wenn gerade keine Anfrage verarbeitet wird, werden Anfragen direkt an den Memory weitergegeben.
        Trifft eine Anfrage ein, wird in den WAIT_VALID State gewechselt, wenn der Memory die Request granted.

        WAIT_VALID:
        Wenn gerade eine Anfrage verarbeitet wird, werden Anfragen nur an den Memory weitergegeben, wenn
        der Memory rvalid auf 1 setzt. Ist rvalid 1 und es wird kein grant durch den Memory erteilt, wird wieder
        in WAIT_GNT gewechselt. Das kann sein, weil der Memory noch beschäftigt ist oder weil keine Anfrage vom
        Core kommt. Anderfalls liegt eine Anfrage vor, die der memory gegranted hat, und der Zustand wird nicht
        gewechselt.
        """

        # gnt and cache ready signal are basically the same
        m.d.comb += self.gnt_o.eq(self.cache_if.port_ready)
        # forward request
        m.d.comb += self.cache_if.request_valid.eq(self.req_i)
        # rvalid_o must be set when the cache_if.read_data is valid or when the cache
        # has executed the write (? - it is needed to end the response phase but I'm not sure
        # at what point rvalid_o should be set when executing a write)
        # TODO: Is it okay for rvalid_o to be set to 1 because of the last request and to then
        # be set to 0 in the cycle after the address phase or would the manager think that
        # his request got answered in 1 cycle (I think it is okay)
        # The cache resets read_data_valid after starting a new request, so this should work
        m.d.comb += self.rvalid_o.eq(self.cache_if.read_data_valid | self.cache_if.port_ready)
        # cache can only do byte writes but not byte reads. write_strobe == 0 means read.
        m.d.comb += self.cache_if.write_strobe.eq(Mux(self.we_i, self.be_i, 0))
        m.d.comb += self.cache_if.address.eq(self.addr_i)
        m.d.comb += self.cache_if.write_data.eq(self.wdata_i)
        # handing out the full word regardless of be_i should be fine (? TODO)
        m.d.comb += self.rdata_o.eq(self.cache_if.read_data)

        # with m.If(state == AdapterState.READY):
        #     with m.If(self.req_i & self.cache_if.port_ready):
        #         m.d.comb += self.gnt_o.eq(1)

        return m
