from amaranth import Module
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out

from pycachegen.cache_config import CacheConfig
from pycachegen.cache_wrapper import CacheWrapper
from pycachegen.pulpissimo.tcdm_cache_adapter import TCDMCacheAdapter
from pycachegen.pulpissimo.tcdm_signature import TCDMSignature
from pycachegen.utils import log_parameters


@log_parameters
class CacheSubsystem(wiring.Component):
    def __init__(
        self,
        cache_address_width: int,
        cache_configs: list[CacheConfig],
        read_delay: int,
        write_delay: int,
    ):
        """Cache subsytem for the pulpissimo SoC which includes an adapter, and a CacheWrapper.

        Look at the pulpissimo_cache_subsystem_wrapper.sv in this folder on how to integrate the Cache
        into the SoC.

        Args:
            cache_address_width: Address width of the cache(s) in bits. Note that this module has a TCDM interface with 32 bit addresses, this parameter only describes the address width of the caches. It should match the depth of the memory that is connected to the BE of the cache(s).
            cache_configs (tuple[CacheConfig, ...]): Configurations for the caches in the order of L1, L2, ... Can be left empty if no caches shall be generated.
            read_delay (int): Additional delay for any read requests sent from the cache to the memory. May be set to 0 if write_delay is also 0.
            write_delay (int): Additional delay for any write requests sent from the cache to the memory. May be set to 0 if read_delay is also 0.
        """
        for cache_config in cache_configs:
            assert cache_config.data_width == 32

        self.cache_address_width = cache_address_width
        self.cache_configs = cache_configs
        self.read_delay = read_delay
        self.write_delay = write_delay
        super().__init__(
            {"requestor": In(TCDMSignature()), "target": Out(TCDMSignature())}
        )

    def elaborate(self, platform):
        m = Module()

        # Create a CacheWrapper
        m.submodules.cache_wrapper = cache_wrapper = CacheWrapper(
            address_width=self.cache_address_width,
            cache_configs=self.cache_configs,
            main_memory_data_width=32,
            create_main_memory=False,
            num_ports=1,
            read_delay=self.read_delay,
            write_delay=self.write_delay,
            byte_size=8,
        )

        # The signature of the memory bus between the caches (its the same for all cache FEs and BEs)
        cache_memory_bus_signature = cache_wrapper.cache_configs[0].fe_signature

        # Create a TCDM Adapter
        m.submodules.adapter = adapter = TCDMCacheAdapter(cache_memory_bus_signature)

        # Connect CacheWrapper to adapter
        wiring.connect(m, adapter.cache_fe, cache_wrapper.fe_0)
        wiring.connect(m, adapter.cache_be, cache_wrapper.be)

        # Connect self to adapter
        wiring.connect(m, wiring.flipped(self.requestor), adapter.requestor)
        wiring.connect(m, adapter.target, wiring.flipped(self.target))

        return m
