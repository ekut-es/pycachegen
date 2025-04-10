from amaranth import Cat, Module, Signal
from amaranth.lib import data


class CacheAddressLayout(data.StructLayout):
    def __init__(self, index_width: int, tag_width: int, word_offset_width: int) -> None:
        """Layout for accessing cache related parts of a memory address.

        Args:
            index_width (int): Width of the index.
            tag_width (int): Width of the tag.
            word_offset_width (int): Width of the word offset (the bits which select the word within a block).
        """
        super().__init__({"word_offset": word_offset_width, "index": index_width, "tag": tag_width})


def get_blockwise_incremented_address(address, counter, m: Module, read_block_wc_width: int):
    """Increments the given address by the given counter.
    When adding the counter, overflow will first occur within the address bits that stay
    the same for one be word. So the incremented address will first iterate through all words
    that belong to the same be word. After that the other address bits will be incremented so
    that the rest of the cache's word will also be addressed. All of this is needed so
    that critical word works.


    Args:
        address (): The base address (fe).
        counter (_type_): The counter to add to the address.
        m (Module): The module in which this operation should take place.
        read_block_wc_width (int): log2 of how many words should be extracted from one be word.

    Returns:
        Signal: The incremented address.
    """
    incremented_address = Signal(address.shape())
    m.d.comb += incremented_address.as_value().eq(address)
    m.d.comb += incremented_address.word_offset.eq(
        Cat(
            (address.word_offset + counter)[:read_block_wc_width],
            (address.word_offset[read_block_wc_width:] + counter[read_block_wc_width:]),
        )
    )
    return incremented_address
