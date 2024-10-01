from amaranth.lib import data


class CacheAddressLayout(data.StructLayout):
    def __init__(
        self, index_width: int, tag_width: int, word_offset_width: int
    ) -> None:
        super().__init__(
            {"tag": tag_width, "index": index_width, "word_offset": word_offset_width}
        )
