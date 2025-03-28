import inspect
from functools import wraps

from amaranth import Module, Signal


def one_hot_encode(module: Module, input: Signal) -> Signal:
    """One hot encodes the input to the returned signal. If not exactly
    one bit in the input is set, the output will be 0.

    Args:
        module (Module): Module to which the assignment should be added.
        input (Signal): Signal to encode.

    Returns:
        Signal: Encoded signal.
    """
    m = module
    width = len(input)
    output = Signal(range(width))
    with m.Switch(input):
        for i in range(width):
            with m.Case(1 << i):
                m.d.comb += output.eq(i)
        with m.Default():
            # The default is already set by the initial value of the output Signal
            # but i'll make it more explicit here
            m.d.comb += output.eq(0)
    return output


def is_onehot(sig: Signal):
    """Returns 1 if exactly 1 bit is set.

    Args:
        sig (Signal): The signal to look at.

    Returns:
        Whether sig is one hot.
    """
    return sig.any() & ~((sig & (sig - 1)).any())


def log_parameters(cls):
    """Decorator to automatically track init parameters for logging."""
    orig_init = cls.__init__

    @wraps(orig_init)
    def new_init(self, *args, **kwargs):
        # Get parameter names (excluding 'self')
        init_params = inspect.signature(orig_init).parameters
        init_params = [p for p in init_params if p != "self"]

        # Call the original __init__
        orig_init(self, *args, **kwargs)

        # Capture only parameters that were actually passed
        bound_args = inspect.signature(orig_init).bind(self, *args, **kwargs)
        bound_args.apply_defaults()

        # Store the logged parameters
        self._params = {p: bound_args.arguments[p] for p in init_params}

    def __repr__(self):
        params_str = ", ".join(f"{k}={v!r}" for k, v in self._params.items())
        return f"{cls.__name__}({params_str})"

    # Replace the methods
    cls.__init__ = new_init
    cls.__repr__ = __repr__

    return cls
