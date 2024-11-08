from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out
from amaranth.utils import exact_log2
from pycachegen.cache_config_validation import (
    MemoryConfig,
    CacheConfig,
    InternalCacheConfig,
    InternalMemoryConfig,
)
from pycachegen.cache import Cache
from pycachegen.main_memory import MainMemory
from pycachegen.memory_bus import MemoryBusSignature
from pycachegen.cache_delay_module import CacheDelayModule


class CacheWrapper(wiring.Component):
    def __init__(
        self,
        num_ports: int,
        arbiter_policy: str,
        byte_size: int,
        enable_reset: bool,
        address_width: int,
        memory_config: MemoryConfig,
        cache_configs: list[CacheConfig],
    ) -> None:
        """Generates a top level module containing an arbitrary amount of caches and a main memory.
        There can also be an arbiter infront of the L1 cache. The caches are set up in a linear
        hierarchy.

        Args:
            num_ports (int): Number of access ports.
            arbiter_policy (str): Policy for the arbiter in case there is more than one port. Can be one of "fifo", "priority", "round_robin".
            byte_size (int): Number of bits per byte.
            enable_reset (bool): Whether to generate reset logic or not. Right now this only affects the main memory module (disabling it there is necessary for generating BRAM during synthesis) but no other modules because otherwise there is a simulation mismatch.
            address_width (int): Address width. Note that addresses do not include a byte offset.
            memory_config (MemoryConfig): Configuration for the main memory.
            cache_configs (tuple[CacheConfig, ...]): Configurations for the caches in the order of L1, L2, ... Can be left empty if no caches shall be generated.
        """
        self.num_ports = num_ports
        self.arbiter_policy = arbiter_policy
        self.byte_size = byte_size
        self.enable_reset = enable_reset
        self.num_caches = len(cache_configs)
        self.fe_address_width = address_width

        if self.num_caches:
            self.fe_data_width = cache_configs[0].data_width
        else:
            self.fe_data_width = memory_config.data_width

        self.fe_bytes_per_word = self.fe_data_width // self.byte_size

        # create internal cache configs
        self.cache_configs: list[InternalCacheConfig] = []
        for i in range(len(cache_configs)):
            config = cache_configs[i]
            cache_address_width = self.fe_address_width - exact_log2(
                config.data_width // self.fe_data_width
            )
            if i < len(cache_configs) - 1:
                be_data_width = cache_configs[i + 1].data_width
            else:
                be_data_width = memory_config.data_width
            be_address_width = self.fe_address_width - exact_log2(
                be_data_width // self.fe_data_width
            )
            self.cache_configs.append(
                InternalCacheConfig(
                    cache_config=config,
                    address_width=cache_address_width,
                    be_data_width=be_data_width,
                    be_address_width=be_address_width,
                    byte_size=self.byte_size,
                    enable_reset=self.enable_reset,
                )
            )

        # create internal memory config
        memory_address_width = self.fe_address_width - exact_log2(
            memory_config.data_width // self.fe_data_width
        )
        self.memory_config = InternalMemoryConfig(
            memory_config=memory_config,
            address_width=memory_address_width,
            byte_size=self.byte_size,
            enable_reset=self.enable_reset,
        )

        super().__init__(
            {
                "fe": In(
                    MemoryBusSignature(
                        address_width=self.fe_address_width,
                        data_width=self.fe_data_width,
                        bytes_per_word=self.fe_bytes_per_word,
                    )
                ),
                "hit_o": Out(1),
            }
        )

    def elaborate(self, platform):
        m = Module()

        # create the actual caches
        memory_hierarchy = []
        for i, cache_config in enumerate(self.cache_configs):
            cache = Cache(config=cache_config)
            if cache_config.hit_latency or cache_config.miss_latency:
                # Add a delay module if the delays aren't 0
                delay_module = CacheDelayModule(
                    bus_signature=cache_config.fe_signature,
                    hit_latency=cache_config.hit_latency,
                    miss_latency=cache_config.miss_latency,
                )
                memory_hierarchy.append(delay_module)
                wiring.connect(delay_module.be, cache.fe)
                m.d.comb += delay_module.hit_i.eq(cache.hit_o)
            memory_hierarchy.append(cache)
            m.submodules[f"l{i+1}_cache"] = cache

        # connect the hit signal of the first cache to this modules hit port
        if len(memory_hierarchy):
            m.d.comb += self.hit_o.eq(memory_hierarchy[0].hit_o)

        # create the main memory
        m.submodules.main_memory = main_memory = MainMemory(config=self.memory_config)

        memory_hierarchy.append(main_memory)

        # connect first cache/memory to this modules fe
        wiring.connect(m, wiring.flipped(self.fe), memory_hierarchy[0].fe)

        # connect the caches/memory with each other
        for previous, current in zip(memory_hierarchy, memory_hierarchy[1:]):
            wiring.connect(m, previous.be, current.fe)

        return m

        # TODO add an arbiter
