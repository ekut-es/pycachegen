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
from pycachegen.amaranth.cache import Cache
from pycachegen.amaranth.main_memory import MainMemory
from pycachegen.amaranth.memory_bus import MemoryBusSignature


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
        self.NUM_PORTS = num_ports
        self.ARBITER_POLICY = arbiter_policy
        self.BYTE_SIZE = byte_size
        self.ENABLE_RESET = enable_reset
        self.NUM_CACHES = len(cache_configs)
        self.FE_ADDRESS_WIDTH = address_width

        if self.NUM_CACHES:
            self.FE_DATA_WIDTH = cache_configs[0].DATA_WIDTH
        else:
            self.FE_DATA_WIDTH = memory_config.DATA_WIDTH

        # create internal cache configs
        self.CACHE_CONFIGS: list[InternalCacheConfig] = []
        for i in range(len(cache_configs)):
            config = cache_configs[i]
            cache_address_width = self.FE_ADDRESS_WIDTH - exact_log2(
                config.DATA_WIDTH // self.FE_DATA_WIDTH
            )
            if i < len(cache_configs) - 1:
                be_data_width = cache_configs[i + 1].DATA_WIDTH
            else:
                be_data_width = memory_config.DATA_WIDTH
            be_address_width = self.FE_ADDRESS_WIDTH - exact_log2(
                be_data_width // self.FE_DATA_WIDTH
            )
            self.CACHE_CONFIGS.append(
                InternalCacheConfig(
                    cache_config=config,
                    address_width=cache_address_width,
                    be_data_width=be_data_width,
                    be_address_width=be_address_width,
                    byte_size=self.BYTE_SIZE,
                    prefix=f"l{i+1}_",
                    enable_reset=self.ENABLE_RESET,
                )
            )

        # create internal memory config
        memory_address_width = self.FE_ADDRESS_WIDTH - exact_log2(
            memory_config.DATA_WIDTH // self.FE_DATA_WIDTH
        )
        self.MEMORY_CONFIG = InternalMemoryConfig(
            memory_config=memory_config,
            address_width=memory_address_width,
            byte_size=self.BYTE_SIZE,
            enable_reset=self.ENABLE_RESET,
        )

        # if self.NUM_CACHES > 0:
        #     self.L1_ADDRESS_WIDTH = self.CACHE_CONFIGS[0].ADDRESS_WIDTH
        #     self.FE_DATA_WIDTH = self.CACHE_CONFIGS[0].DATA_WIDTH
        # else:
        #     self.L1_ADDRESS_WIDTH = self.MEMORY_CONFIG.ADDRESS_WIDTH
        #     self.FE_DATA_WIDTH = self.MEMORY_CONFIG.DATA_WIDTH
        self.FE_BYTES_PER_WORD = self.FE_DATA_WIDTH // self.BYTE_SIZE
        # self.FE_BYTE_OFFSET_WIDTH = exact_log2(self.FE_BYTES_PER_WORD)

        super().__init__(
            {
                "fe": In(
                    MemoryBusSignature(
                        address_width=self.FE_ADDRESS_WIDTH,
                        data_width=self.FE_DATA_WIDTH,
                        bytes_per_word=self.FE_BYTES_PER_WORD,
                    )
                ),
                "hit_o": Out(1),
            }
        )

    def elaborate(self, platform):
        m = Module()

        # create the actual caches
        caches = []
        for i, cache_config in enumerate(self.CACHE_CONFIGS):
            cache = Cache(config=cache_config)
            caches.append(cache)
            m.submodules[f"l{i+1}_cache"] = cache

        # connect the hit signal of the first cache to this modules hit port
        if len(caches):
            m.d.comb += self.hit_o.eq(caches[0].hit_o)

        # create the main memory
        m.submodules.main_memory = main_memory = MainMemory(config=self.MEMORY_CONFIG)

        caches_and_memory = caches + [main_memory]

        # connect first cache/memory to this modules fe
        wiring.connect(m, wiring.flipped(self.fe), caches_and_memory[0].fe)

        # connect the caches/memory with each other
        for previous, current in zip(caches_and_memory, caches_and_memory[1:]):
            wiring.connect(m, previous.be, current.fe)

        return m

        # TODO add an arbiter
