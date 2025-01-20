from enum import Enum

from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out

from pycachegen.cache_config_validation import InternalCacheConfig
from pycachegen.memory_bus import MemoryBusInterface
from pycachegen import Cache


class CV32E40PMemoryBusSignature(wiring.Signature):
    def __init__(
        self,
        # address_width: int, data_width: int, bytes_per_word: int
    ):
        # self.address_width = address_width
        # self.data_width = data_width
        # self.bytes_per_word = bytes_per_word
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
            ]
        )

    def __eq__(self, other):
        return (
            isinstance(other, CV32E40PMemoryBusSignature)
            # and self.address_width == other.address_width
            # and self.data_width == other.data_width
            # and self.bytes_per_word == other.bytes_per_word
        )

    def __repr__(self):
        return f"CV32E40PMemoryBusSignature()"  # {self.address_width}, {self.data_width}, {self.bytes_per_word})"


class AdapterState(Enum):
    READY = 0
    WAIT = 1


class CV32E40PAdapter(wiring.Component):
    def __init__(self, cache: Cache):
        self.cache_config = cache.config
        self.cache = cache
        super().__init__(
            {
                # Core <-> Adapter <-> Cache
                "core_if": In(CV32E40PMemoryBusSignature()),
                # Cache <-> Adapter <-> Main Memory
                "memory_if": Out(CV32E40PMemoryBusSignature())
            }
        )

    def elaborate(self, platform):
        m = Module()

        m.submodules.cache = cache = self.cache

        state = Signal(AdapterState)

        """
        https://docs.openhwgroup.org/projects/cv32e40x-user-manual/en/latest/load_store_unit.html
        https://github.com/openhwgroup/obi/blob/072d9173c1f2d79471d6f2a10eae59ee387d4c6f/OBI-v1.6.0.pdf

        TODO: Herausfinden, ob die LSU im Core oder außerhalb sitzt. Die LSU handelt z.B. misaligned
        accesses, was der Cache nicht kann.

        TODO: Parametrisierbarkeit

        TODO: Memory ranges checken; es sollen nicht (32-n) bit tags gespeichert werden müssen

        TODO: Add support for multi layer cache hierarchies

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
        ## Connect cache.fe
        core_if = self.core_if
        # gnt and cache ready signal are basically the same
        m.d.comb += core_if.gnt.eq(cache.fe.port_ready)
        # forward request
        m.d.comb += cache.fe.request_valid.eq(core_if.req)
        # rvalid must be set when the cache_fe.read_data is valid or when the cache
        # has executed the write (? - it is needed to end the response phase but I'm not sure
        # at what point rvalid should be set when executing a write)
        # TODO: Is it okay for rvalid to be set to 1 because of the last request and to then
        # be set to 0 in the cycle after the address phase or would the manager think that
        # his request got answered in 1 cycle (I think it is okay)
        # The cache resets read_data_valid after starting a new request, so this should work
        m.d.comb += core_if.rvalid.eq(cache.fe.read_data_valid | cache.fe.port_ready)
        # cache can only do byte writes but not byte reads. write_strobe == 0 means read.
        m.d.comb += cache.fe.write_strobe.eq(Mux(core_if.we, core_if.be, 0))
        m.d.comb += cache.fe.address.eq(core_if.addr[2:])  # TODO
        m.d.comb += cache.fe.write_data.eq(core_if.wdata)
        # handing out the full word regardless of be should be fine (? TODO)
        m.d.comb += core_if.rdata.eq(cache.fe.read_data)

        ## Connect cache.be
        mem_if = self.memory_if
        m.d.comb += cache.be.port_ready.eq(mem_if.gnt)
        m.d.comb += mem_if.req.eq(cache.be.request_valid)
        m.d.comb += cache.be.read_data_valid.eq(mem_if.rvalid)
        m.d.comb += mem_if.be.eq(Mux(cache.be.write_strobe.any(), cache.be.write_strobe, -1))
        m.d.comb += mem_if.addr.eq(Cat(C(0, unsigned(2)), cache.be.address))
        m.d.comb += mem_if.wdata.eq(cache.be.write_data)
        m.d.comb += cache.be.read_data.eq(mem_if.rdata)

        return m
