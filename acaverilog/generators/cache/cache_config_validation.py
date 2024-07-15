from math import log2


class ConfigurationError(ValueError):
    """An error that gets thrown when a module was configured incorrectly."""

    pass


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


def assert_replacement_policy_is_valid(name: str, valid_policies: list[str]) -> None:
    """Throw an error if the string is not a valid replacement policy.

    Args:
        name (str): name to be checked
        valid_policies (list[str]): list of all valid replacement policies

    Raises:
        ConfigurationError: Error that gets thrown if the replacement policy is invalid
    """
    if name not in valid_policies:
        raise ConfigurationError(f"Replacement Policy must be one of {valid_policies}")


def assert_same_address_space(dw1: int, aw1: int, dw2: int, aw2: int) -> None:
    """Check that two different address and data widths cover the same number of bits.

    Args:
        dw1 (int): data width 1
        aw1 (int): address width 1
        dw2 (int): data width 2
        aw2 (int): address width 2

    Raises:
        ConfigurationError: Error that gets thrown if the two configurations do not cover the same address space
    """
    if (own := dw1 * 2**aw1) != (other := dw2 * 2**aw2):
        raise ConfigurationError(
            f"Own address space spans {own} bits while backend address space spans {other} bits"
        )


def assert_data_width_valid(data_width: int) -> None:
    """Throws an error if the data width is not of the form 8 * 2**n with n >= 0.

    Args:
        data_width (int): data width to be checked

    Raises:
        ConfigurationError: Error that gets thrown if the data width is invalid.
    """
    if data_width % 8 != 0 or not is_power_of_two(data_width // 8):
        raise ConfigurationError("Data width must have the form (8 * 2**n) with n >= 0")


def assert_address_config_valid(
    address_width: int, num_sets: int, num_ways: int, block_size: int
) -> None:
    """Check that the number of sets, number of ways and the block size are valid with regards
    to the address width.

    Args:
        address_width (int): width of the word addressing address
        num_sets (int): number of sets
        num_ways (int): number of ways
        block_size (int): words per block

    Raises:
        ConfigurationError: Error that gets thrown if the configuration is invalid.
    """
    # Check that there are enough address bits for the sets and the block size
    bits_required = int(log2(num_sets)) + int(log2(block_size))
    if bits_required > address_width:
        raise ConfigurationError(
            f"The number of sets and the block size require {bits_required} bits in the address, but the address is only {address_width} bits wide"
        )

    # Check that there are not more ways than data words that would be stored in one set
    tag_width = address_width - bits_required
    if int(log2(num_ways)) > tag_width:
        raise ConfigurationError(
            f"The tag is only {tag_width} bits wide but the cache has {num_ways} ways, so there are more ways than data words that would be stored in the same set"
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
            "The data width cannot be greater than the backend data width"
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