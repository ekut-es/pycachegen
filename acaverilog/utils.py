from bitarray import bitarray


def ba_to_little_endian_str(bits: bitarray):
    return str(bits.to01())[::-1]
