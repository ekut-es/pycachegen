from __future__ import annotations

from typing import TYPE_CHECKING

from amaranth import unsigned
from amaranth.lib import data, wiring
from amaranth.lib.wiring import In, Out
from amaranth.utils import exact_log2

if TYPE_CHECKING:
    from .cache_config import InternalCacheConfig


class CacheStoreSignature(wiring.Signature):
    def __init__(self, config: InternalCacheConfig):
        """Signature of the CacheStore.

        Args:
            config (InternalCacheConfig): Cache configuration.
        """
        self.address_width = config.store_address_width
        self.num_ways = config.num_ways
        self.data_width = config.data_width
        self.bytes_per_word = config.bytes_per_word
        super().__init__(
            [
                ("read_request_valid", Out(1)),
                ("read_address", Out(self.address_width)),
                ("read_way", Out(exact_log2(self.num_ways))),
                ("read_data", In(self.data_width)),
                ("write_request_valid", Out(1)),
                ("write_address", Out(self.address_width)),
                ("write_way", Out(exact_log2(self.num_ways))),
                ("write_data", Out(self.data_width)),
                ("byte_strobe", Out(self.bytes_per_word)),
            ]
        )

    def __eq__(self, other):
        return (
            isinstance(other, CacheStoreSignature)
            and self.address_width == other.address_width
            and self.num_ways == other.num_ways
            and self.data_width == other.data_width
            and self.bytes_per_word == other.bytes_per_word
        )


class DirectorySignature(wiring.Signature):
    def __init__(self, config: InternalCacheConfig):
        """Signature of the CacheDirectory.

        Args:
            config (InternalCacheConfig): Cache configuration.
        """
        self.index_width = config.index_width
        self.num_ways = config.num_ways
        self.data_width = config.tag_width
        self.tag_width = config.tag_width
        super().__init__(
            [
                # index is used for all reads and writes
                ("index", Out(self.index_width)),
                # read operation: The tags, valid and dirty bits of all blocks in the
                # selected set
                ("tags", In(self.num_ways * self.tag_width)),
                ("valid_bits", In(self.num_ways)),
                ("dirty_bits", In(self.num_ways)),
                # write_way selects the way for all write operations
                ("write_way", Out(exact_log2(self.num_ways))),
                # All write operations have a data_ signal that carries the write data
                # and an update_ signal that controls if the write should take place
                # tag
                ("data_tag", Out(self.tag_width)),
                ("update_tag", Out(1)),
                # valid
                ("data_valid", Out(1)),
                ("update_valid", Out(1)),
                # dirty
                ("data_dirty", Out(1)),
                ("update_dirty", Out(1)),
            ]
        )

    def __eq__(self, other):
        return (
            isinstance(other, DirectorySignature)
            and self.index_width == other.index_width
            and self.num_ways == other.num_ways
            and self.data_width == other.data_width
            and self.tag_width == other.tag_width
        )

    def create(self, *, path=None, src_loc_at=0):
        return DirectoryInterface(self, path=path, src_loc_at=1 + src_loc_at)


class DirectoryInterface(wiring.PureInterface):
    def tag(self, way):
        return self.tags.word_select(way, self.signature.tag_width)


class ReplacementPolicySignature(wiring.Signature):
    def __init__(self, config: InternalCacheConfig):
        """Signature of the replacement policy.

        Args:
            config (InternalCacheConfig): _description_
        """
        self.num_sets = config.num_sets
        self.num_ways = config.num_ways
        super().__init__(
            [
                ("access", Out(1)),
                ("replace", Out(1)),
                ("set", Out(range(self.num_sets))),
                ("way", Out(range(self.num_ways))),
                ("next_replacement", In(range(self.num_ways))),
            ]
        )

    def __eq__(self, other):
        return (
            isinstance(other, ReplacementPolicySignature)
            and self.num_sets == other.num_sets
            and self.num_ways == other.num_ways
        )


class MemoryBusSignature(wiring.Signature):
    def __init__(self, address_width: int, data_width: int, bytes_per_word: int):
        """Signature of the memory bus used by the cache.

        Args:
            address_width (int): Width of the address (which does not include byte offset bits).
            data_width (int): Width of the data in bits.
            bytes_per_word (int): Number of bytes per data word.
        """
        self.address_width = address_width
        self.data_width = data_width
        self.bytes_per_word = bytes_per_word
        super().__init__(
            [
                ("address", Out(address_width)),
                ("write_data", Out(data_width)),
                ("write_strobe", Out(bytes_per_word)),
                ("request_valid", Out(1)),
                ("read_data", In(data_width)),
                ("read_data_valid", In(1)),
                ("port_ready", In(1)),
                ("flush", Out(1)),
                ("flush_done", In(1)),
            ]
        )

    def __eq__(self, other):
        return (
            isinstance(other, MemoryBusSignature)
            and self.address_width == other.address_width
            and self.data_width == other.data_width
            and self.bytes_per_word == other.bytes_per_word
        )

    def __repr__(self):
        return f"MemoryBusSignature({self.address_width}, {self.data_width}, {self.bytes_per_word})"

    def create(self, *, path=None, src_loc_at=0):
        return MemoryBusInterface(self, path=path, src_loc_at=1 + src_loc_at)


class MemoryBusInterface(wiring.PureInterface):
    def is_read_request(self):
        return self.request_valid & (self.write_strobe == 0)

    def is_write_request(self):
        return self.request_valid & (self.write_strobe != 0)


class MemoryRequestLayout(data.StructLayout):
    def __init__(self, signature: MemoryBusSignature):
        """A StructLayout for memory requests which can be used in FIFOs.
        The request_valid bit is missing because only valid requests should
        be buffered in such FIFOs.

        Args:
            signature (MemoryBusSignature): The memory bus signature whose parameters will be used for the layout.
        """
        super().__init__(
            {
                "address": unsigned(signature.address_width),
                "write_data": unsigned(signature.data_width),
                "write_strobe": unsigned(signature.bytes_per_word),
            }
        )
