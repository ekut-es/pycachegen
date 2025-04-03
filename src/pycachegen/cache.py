from amaranth import Module
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out

from .cache_config import InternalCacheConfig
from .cache_controller import CacheController
from .cache_directory import CacheDirectory
from .data_store import CacheStore
from .replacement_policy import ReplacementPolicy


class Cache(wiring.Component):
    def __init__(self, config: InternalCacheConfig) -> None:
        self.config = config

        super().__init__(
            {
                "fe": In(self.config.fe_signature),
                "hit_o": Out(1),
                "be": Out(self.config.be_signature),
            }
        )

    def elaborate(self, platform) -> Module:
        m = Module()

        m.submodules.cache_store = cache_store = CacheStore(self.config)
        m.submodules.directory = directory = CacheDirectory(self.config)
        m.submodules.repl_pol = repl_pol = ReplacementPolicy(self.config)
        m.submodules.cache_controller = cache_controller = CacheController(self.config)

        wiring.connect(m, cache_controller.store, cache_store.port)
        wiring.connect(m, cache_controller.directory, directory.port)
        wiring.connect(m, cache_controller.repl_pol, repl_pol.port)

        wiring.connect(m, wiring.flipped(self.fe), cache_controller.fe)
        wiring.connect(m, cache_controller.be, wiring.flipped(self.be))
        m.d.comb += self.hit_o.eq(cache_controller.hit_o)

        return m
