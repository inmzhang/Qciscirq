"""Context wrapped around qcis when converting circuit with custom methods."""
import functools
from typing import Callable, Any, List

CONTEXT_START = '# CIRQ_CONTEXT_START'
"""Used in qcis circuit to annotate the start of the circuit translation context.

It should be added to the `_qcis_conversion_` method of a cirq extension class.
The context is useful when convert qcis circuit to cirq circuit.
"""


CONTEXT_END = '# CIRQ_CONTEXT_END'
"""Used in qcis circuit to annotate the end of the circuit translation context."""


def context_wrapper(func: Callable[..., str]) -> Callable[..., str]:
    """Wrap context around the qcis string created by the function.

    Args:
        func: The function that creates the qcis string.

    Returns:
        The function with context added.
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        instance = args[0]
        targets: List[str] = kwargs.get('targets', [])
        out = [CONTEXT_START,
               f'# Gate: {instance!r}',
               f'# Targets: {targets!r}',
               func(*args, **kwargs),
               CONTEXT_END]
        return '\n'.join(out)
    return wrapper
