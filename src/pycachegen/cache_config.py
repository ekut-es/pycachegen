from enum import Enum

from amaranth.utils import ceil_log2, exact_log2

from .cache_address import CacheAddressLayout
from .interfaces import MemoryBusSignature
from .utils import log_parameters


class ReplacementPolicies(Enum):
    FIFO = "fifo"
    PLRU_TREE = "plru_tree"
    PLRU_MRU = "plru_mru"
    LRU = "lru"


class WritePolicies(Enum):
    WRITE_THROUGH = "write_through"
    WRITE_BACK = "write_back"


class ArbitrationScheme(Enum):
    PRIORITY = "priority"
    ROUND_ROBIN = "round_robin"


class ConfigurationError(ValueError):
    """An error that gets thrown when a module was configured incorrectly."""


def is_power_of_two(i: int) -> bool:
    """Check whether i is a power of two

    Args:
        i (int): integer to check

    Returns:
        bool: Whether i is a power of two
    """
    return i & (i - 1) == 0 and i != 0


def assert_is_power_of_two(i: int, name: str) -> None:
    """Throw an error if i is not a power of two

    Args:
        i (int): integer to check
        name (str): name of the parameter to be included in the error message

    Raises:
        ConfigurationError: Error that gets thrown if i is not a power of two.
    """
    if not is_power_of_two(i):
        raise ConfigurationError(f"{name} needs to be a power of two.")


def assert_same_address_space(dw1: int, aw1: int, dw2: int, aw2: int) -> None:
    """Check that two different address and data widths cover the same number of bits.

    Args:
        dw1 (int): data width 1
        aw1 (int): address width 1 (not inlcuding byte offset bits)
        dw2 (int): data width 2
        aw2 (int): address width 2 (not inlcuding byte offset bits)

    Raises:
        ConfigurationError: Error that gets thrown if the two configurations do not cover the same address space
    """
    if (own := dw1 * 2**aw1) != (other := dw2 * 2**aw2):
        raise ConfigurationError(f"First address space spans {own} bits while second address space spans {other} bits")


def assert_data_width_valid(data_width: int, byte_size: int) -> None:
    """Throws an error if the data width is not of the form (byte_size * 2**n) with n >= 0.

    Args:
        data_width (int): data width to be checked

    Raises:
        ConfigurationError: Error that gets thrown if the data width is invalid.
    """
    if data_width % byte_size != 0 or not is_power_of_two(data_width // byte_size):
        raise ConfigurationError(
            "Data width must have the form (byte_size * 2**n) with n >= 0 "
            + f"(data width {data_width}, byte size {byte_size})"
        )


def assert_address_config_valid(address_width: int, num_sets: int, num_ways: int, block_size: int) -> None:
    """Check that the number of sets, number of ways and the block size are valid with regards
    to the address width.

    Args:
        address_width (int): width of the address (addresses don't include any byte offset bits)
        num_sets (int): number of sets
        num_ways (int): number of ways
        block_size (int): words per block

    Raises:
        ConfigurationError: Error that gets thrown if the configuration is invalid.
    """
    # Check that there are enough address bits for the sets and the block size
    bits_required = exact_log2(num_sets) + exact_log2(block_size)
    if bits_required > address_width:
        raise ConfigurationError(
            f"The number of sets and the block size require {bits_required} bits in the address,"
            + f" but the address is only {address_width} bits wide"
        )

    # Check that there are not more ways than data words that would be stored in one set
    tag_width = address_width - bits_required
    if exact_log2(num_ways) > tag_width:
        raise ConfigurationError(
            f"The tag is only {tag_width} bits wide but the cache has {num_ways} ways, so there are more ways than data"
            + " words that would be stored in the same set"
        )


def assert_be_data_width_valid(data_width, be_data_width) -> None:
    """Throws an error if the backend data width is greater than the own data width.

    Args:
        data_width (int): own data width
        be_data_width (int): backend data width

    Raises:
        ConfigurationError: Error that gets thrown if the data width is greater than the backend data width.
    """
    if data_width > be_data_width:
        raise ConfigurationError(
            f"The data width ({data_width}) cannot be greater than the backend data width ({be_data_width})"
        )


def assert_greater_equal(i: int, threshold: int, name: str) -> None:
    """Throws an error if the given value is not greater or equal to the treshold.

    Args:
        i (int): the value to compare
        threshold (int): the threshold to compare against
        name (str): the name of the parameter `i` to be shown in the error message

    Raises:
        ConfigurationError: Error that gets thrown if i<threshold
    """
    if i < threshold:
        raise ConfigurationError(f"{name} is {i} but needs to be at least {threshold}")


def assert_address_range_valid(min_address: int, max_address: int, address_width: int) -> None:
    """Throws an error if the given address range has size 0 or if it is not within the boundaries
    set by the address width. Note that addresses generally don't include any byte offset bits.

    Args:
        min_address (int): The smallest address (inclusive).
        max_address (int): The greatest address (exclusive).
        address_width (int): The width of the address in bits.
    """
    if min_address >= max_address:
        raise ConfigurationError(
            f"min_address ({min_address}) needs to be smaller than the max_address ({max_address})"
        )
    bits_needed = ceil_log2(max_address)
    if bits_needed > address_width:
        raise ConfigurationError(
            f"max_address is {max_address} and needs at least {bits_needed} address bits, "
            + f"but the address is only {address_width} bits wide"
        )


def assert_delays_valid(read_delay: int, write_delay: int) -> None:
    if (read_delay == 0) ^ (write_delay == 0):
        raise ConfigurationError(
            "The read and write delays must either both be 0 or greater than 0, but they are configured to be"
            + f" {read_delay} and {write_delay}"
        )


@log_parameters
class CacheConfig:
    def __init__(
        self,
        data_width: int,
        num_ways: int,
        num_sets: int,
        replacement_policy: ReplacementPolicies,
        write_policy: WritePolicies,
        write_allocate: bool,
        block_size: int,
        write_buffer_size: int = 0,
        data_memory_module: str = "",
    ) -> None:
        """Class for end users to create configurations for caches.

        Args:
            data_width (int): Width of one data word in bits.
            num_ways (int): Number of ways. Must be a power of 2.
            num_sets (int): Number of sets. Must be a power of 2.
            replacement_policy (ReplacementPolicies): The replacement policy to use.
            write_policy (WritePolicies): Can be set to write-through or write-back.
            write_allocate (bool): Use write-allocate or write-no-allocate policy
            block_size (int): Number of words per block. Must be a power of 2.
            write_buffer_size (int): The number of words that can be stored in the write buffer. If set to 0, no write
                buffer will be created.
            data_memory_module (str): Can be used to specify the name of an external Verilog module to be used as data
                memory. This memory must be a dual port memory with the correct interface. An Amaranth memory will be
                created if this value is an empty string.
        """
        self.data_width = data_width
        self.num_ways = num_ways
        self.num_sets = num_sets
        self.replacement_policy = replacement_policy
        self.write_through = write_policy == WritePolicies.WRITE_THROUGH
        self.write_allocate = write_allocate
        self.block_size = block_size
        self.write_buffer_size = write_buffer_size
        self.data_memory_module = data_memory_module


if __name__ == "__main__":
    cc = CacheConfig(32, 4, 16, ReplacementPolicies.FIFO, False, True, 2, 0, 0, "")
    print(repr(cc))


class InternalCacheConfig:
    def __init__(
        self,
        cache_config: CacheConfig,
        address_width: int,
        be_data_width: int,
        be_address_width: int,
        byte_size: int,
    ) -> None:
        """Class for validating cache configs in a cache hierarchy and for passing on all needed
        arguments to a cache.

        Args:

            cache_config (CacheConfig): The normal CacheConfig on which this InternalCacheConfig should be based.
            address_width (int): Width of the addresses in bits. Addresses do not include a byte offset.
            be_data_width (int): Data width of the next level cache in bits. Must be of the form (byte_size * 2**n)
                where n>=0. Must be greater or equal to the cache's own data_width.
            be_address_width (int): Address width of the next level cache.
            byte_size (int): Number of bits per byte.
        """
        assert_data_width_valid(cache_config.data_width, byte_size)
        assert_data_width_valid(be_data_width, byte_size)  # technically this is checked in the BE config too
        assert_is_power_of_two(cache_config.num_ways, "num_ways")
        assert_is_power_of_two(cache_config.num_sets, "num_sets")
        assert_is_power_of_two(cache_config.block_size, "block_size")
        assert_same_address_space(
            dw1=cache_config.data_width,
            aw1=address_width,
            dw2=be_data_width,
            aw2=be_address_width,
        )
        assert_address_config_valid(
            address_width=address_width,
            num_sets=cache_config.num_sets,
            num_ways=cache_config.num_ways,
            block_size=cache_config.block_size,
        )
        assert_be_data_width_valid(cache_config.data_width, be_data_width)
        self.data_width = cache_config.data_width
        self.address_width = address_width
        self.num_ways = cache_config.num_ways
        self.num_sets = cache_config.num_sets
        self.replacement_policy = cache_config.replacement_policy
        self.write_back = not cache_config.write_through
        self.write_allocate = cache_config.write_allocate
        self.block_size = cache_config.block_size
        self.be_data_width = be_data_width
        self.be_address_width = be_address_width
        self.byte_size = byte_size
        self.bytes_per_word = cache_config.data_width // byte_size
        self.be_bytes_per_word = be_data_width // byte_size
        self.index_width = exact_log2(cache_config.num_sets)
        self.word_offset_width = exact_log2(cache_config.block_size)
        self.tag_width = address_width - self.index_width - self.word_offset_width
        # how many times bigger the be words are compared to ours
        self.be_byte_multiplier = self.be_bytes_per_word // self.bytes_per_word
        # If the BE words are bigger than our own words and if we use a block size
        # > 1, then we can use one request to the BE for multiple words (in the
        # write back and read block operations).
        # This variable specifies how many words of a block fit into one BE word
        self.be_word_multiplier = min(self.be_byte_multiplier, cache_config.block_size)
        self.be_word_multiplier_width = exact_log2(self.be_word_multiplier)
        self.read_block_requests_needed = cache_config.block_size // self.be_word_multiplier
        # width difference between own and BE address
        self.address_width_difference = address_width - be_address_width

        self.fe_signature = MemoryBusSignature(
            address_width=self.address_width,
            data_width=self.data_width,
            bytes_per_word=self.bytes_per_word,
        )
        self.be_signature = MemoryBusSignature(
            address_width=self.be_address_width,
            data_width=self.be_data_width,
            bytes_per_word=self.be_bytes_per_word,
        )
        self.address_layout = CacheAddressLayout(
            index_width=self.index_width,
            tag_width=self.tag_width,
            word_offset_width=self.word_offset_width,
        )
        self.data_memory_module = cache_config.data_memory_module
        self.store_address_width = exact_log2(self.num_sets) + exact_log2(self.block_size)
        self.write_buffer_size = cache_config.write_buffer_size


class InternalMemoryConfig:
    def __init__(
        self,
        data_width: int,
        address_width: int,
        byte_size: int,
    ) -> None:
        """Class for configuring the MainMemory.

        Args:
            data_width (int): Width of a data word in bits. Must be of the form (byte_size * 2**n) with n >= 0.
            address_width (int): Width of the addresses in bits. Addresses do not include a byte offset.
            byte_size (int): Number of bits per byte.
        """
        assert_data_width_valid(data_width, byte_size)

        self.data_width = data_width
        self.address_width = address_width
        self.byte_size = byte_size
        self.bytes_per_word = data_width // byte_size
        self.memory_bus_signature = MemoryBusSignature(
            address_width=self.address_width,
            data_width=self.data_width,
            bytes_per_word=self.bytes_per_word,
        )
