from math import ceil, log2


class TargetIdConfig:

    def __init__(self, start_bit: int, max_id: int):
        self.start_bit = start_bit
        self.length = ceil(log2(max_id))
        self.max_id = max_id
