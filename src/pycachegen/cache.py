from amaranth import Module
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out

from .cache_config import InternalCacheConfig
from .cache_controller import CacheController
from .cache_directory import CacheDirectory
from .cache_store import CacheStore
from .replacement_policy import ReplacementPolicy
from .write_buffer import WriteBuffer


class Cache(wiring.Component):
    def __init__(self, config: InternalCacheConfig) -> None:
        """A module for creating and connecting all parts of the cache.

        This includes a CacheController, CacheStore, CacheDirectory, ReplacementPolicy and WriteBuffer.

        Args:
            config (InternalCacheConfig): Configuration of the cache.
        """
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

        # Create CacheController and connect FE
        m.submodules.cache_controller = cache_controller = CacheController(self.config)
        wiring.connect(m, wiring.flipped(self.fe), cache_controller.fe)
        m.d.comb += self.hit_o.eq(cache_controller.hit_o)

        # Create CacheStore, CacheDirectory, ReplacementPolicy
        m.submodules.cache_store = cache_store = CacheStore(self.config)
        wiring.connect(m, cache_controller.store, cache_store.port)
        m.submodules.directory = directory = CacheDirectory(self.config)
        wiring.connect(m, cache_controller.directory, directory.port)
        m.submodules.repl_pol = repl_pol = ReplacementPolicy(self.config)
        wiring.connect(m, cache_controller.repl_pol, repl_pol.port)

        if self.config.write_buffer_size:
            # Create WriteBuffer and connect it to the CacheController and the BE
            m.submodules.write_buffer = write_buffer = WriteBuffer(
                signature=self.config.be_signature, depth=self.config.write_buffer_size
            )
            wiring.connect(m, cache_controller.be, write_buffer.fe)
            wiring.connect(m, write_buffer.be, wiring.flipped(self.be))
        else:
            # Connect the CacheController to the BE
            wiring.connect(m, cache_controller.be, wiring.flipped(self.be))

        return m
