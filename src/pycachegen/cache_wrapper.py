from amaranth import Module
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out
from amaranth.utils import exact_log2

from .arbiter import Arbiter, ArbitrationScheme
from .cache import Cache
from .cache_config import (
    CacheConfig,
    InternalCacheConfig,
    InternalMemoryConfig,
    MemoryConfig,
)
from .interfaces import MemoryBusSignature
from .main_memory import MainMemory


class CacheWrapper(wiring.Component):
    def __init__(
        self,
        num_ports: int,
        address_width: int,
        memory_config: MemoryConfig,
        cache_configs: list[CacheConfig],
        arbitration_scheme: ArbitrationScheme = ArbitrationScheme.ROUND_ROBIN,
        byte_size: int = 8,
    ) -> None:
        """The top level module for using caches.

        Generates an arbitrary amount of caches, a main memory and optionally an arbiter infront of the L1 cache.
        The caches are set up in a linear hierarchy.

        Args:
            num_ports (int): Number of access ports.
            address_width (int): Address width. Note that addresses do not include a byte offset.
            memory_config (MemoryConfig): Configuration for the main memory.
            cache_configs (tuple[CacheConfig, ...]): Configurations for the caches in the order of L1, L2, ... Can be left empty if no caches shall be generated.
            arbitration_scheme (ArbitrationScheme): Scheme for the arbiter in case there is more than one port. Supports priority and round robin scheme.
            byte_size (int): Number of bits per byte.
        """
        self.num_ports = num_ports
        self.arbitration_scheme = arbitration_scheme
        self.byte_size = byte_size
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
        )

        self.memory_bus_signature = MemoryBusSignature(
            address_width=self.fe_address_width,
            data_width=self.fe_data_width,
            bytes_per_word=self.fe_bytes_per_word,
        )

        ports = {}

        for i in range(num_ports):
            ports[f"fe_{i}"] = In(self.memory_bus_signature)
            ports[f"hit_o_{i}"] = Out(1)

        super().__init__(ports)

    def elaborate(self, platform):
        m = Module()

        # create an arbiter if necessary
        if self.num_ports > 1:
            m.submodules.arbiter = arbiter = Arbiter(
                num_ports=self.num_ports,
                bus_signature=self.memory_bus_signature,
                arbitration_scheme=self.arbitration_scheme,
            )
            # connect the arbiter to the FE ports
            for i in range(self.num_ports):
                wiring.connect(
                    m,
                    wiring.flipped(getattr(self, f"fe_{i}")),
                    getattr(arbiter, f"fe_{i}"),
                )
            l1_interface = arbiter.be
            l1_hit = arbiter.hit_i
        else:
            l1_interface = wiring.flipped(self.fe_0)
            l1_hit = self.hit_o_0

        # create the actual caches
        memory_hierarchy = []
        for i, cache_config in enumerate(self.cache_configs):
            m.submodules[f"l{i+1}_cache"] = cache = Cache(config=cache_config)
            memory_hierarchy.append(cache)

        # connect the hit signal of the first cache to the l1_hit output
        if len(memory_hierarchy):
            m.d.comb += l1_hit.eq(memory_hierarchy[0].hit_o)

        # create the main memory
        m.submodules.main_memory = main_memory = MainMemory(config=self.memory_config)

        memory_hierarchy.append(main_memory)

        # connect first cache/memory to this modules fe
        wiring.connect(m, l1_interface, memory_hierarchy[0].fe)

        # connect the caches/memory with each other
        for previous, current in zip(memory_hierarchy, memory_hierarchy[1:]):
            wiring.connect(m, previous.be, current.fe)

        return m
