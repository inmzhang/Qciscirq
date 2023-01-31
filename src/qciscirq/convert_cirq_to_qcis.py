"""Adaptor to convert cirq circuits to QCIS circuits."""
from typing import (
    Dict,
    Type,
    Callable,
    Iterable,
    List,
    Set,
    Tuple,
    Protocol,
    Optional,
    Any,
    Union,
)

import cirq
import stimcirq

from qciscirq.gate_table import GateTable

GateOrOp = Union[cirq.Gate, cirq.Operation, Type[cirq.Gate], Type[cirq.Operation]]

DEFAULT_IGNORED_GATES_OPS: Set[GateOrOp] = {
    stimcirq.DetAnnotation,
    stimcirq.CumulativeObservableAnnotation,
    stimcirq.ShiftCoordsAnnotation,
    stimcirq.TwoQubitAsymmetricDepolarizingChannel,
    cirq.DepolarizingChannel,
    cirq.AsymmetricDepolarizingChannel
}


def cirq_to_qcis(circuit: 'cirq.Circuit',
                 map_func: Callable[['cirq.GridQubit'], str],
                 all_blockable_qagents: Iterable[str],
                 couplers: Optional[Dict[str, Tuple[str, str]]] = None,
                 ignored_gates_or_ops: Optional[Iterable[GateOrOp]] = None) -> str:
    """Convert cirq circuit to QCIS circuit.

    Args:
        circuit: The cirq circuit to be converted.
        map_func: A function that maps cirq.GridQubit to a string.
        all_blockable_qagents: All qagents that can be blocked, used in 'B' operation.
        couplers: A dictionary mapping coupler names to qubit pairs, used in CZ operation conversion.
            Defaults to None. When the circuit contains CZ gates, this argument must be provided.
        ignored_gates_or_ops: Specify the gates or operations to ignore when converting from cirq to qcis.
            Defaults to None. When None, the default set of gates or operations to ignore will be used, including
            stimcirq extension operations and cirq noise channel gates. When not None, the ignored set used will be
            the union of the default set and the set specified by this argument.

    Returns:
        The QCIS circuit.

    Examples:
        >>> import cirq
        >>> import qciscirq
        >>> q1, q2 = cirq.GridQubit.rect(1, 2)
        >>> print(qciscirq.cirq_to_qcis(
        ...     cirq.Circuit(
        ...         cirq.Moment((cirq.Y ** 0.5)(q1), (cirq.Y ** -0.5)(q2)),
        ...         cirq.Moment(cirq.CZ(q1, q2)),
        ...         cirq.Moment((cirq.Y ** 0.5)(q2)),
        ...         cirq.Moment(cirq.measure(q1, q2)),
        ...     ),
        ...     map_func={q1: 'Q01', q2: 'Q02'}.get,
        ...     all_blockable_qagents = ['Q01', 'Q02', 'R01'],
        ...     couplers = {'G0201': ('Q01', 'Q02')}))
        Y2P Q01
        Y2M Q02
        B Q01 Q02 R01
        CZ G0201
        B Q01 Q02 R01
        Y2P Q02
        B Q01 Q02 R01
        M Q01 Q02
        B Q01 Q02 R01
    """

    if ignored_gates_or_ops is None:
        ignored_gates_or_ops = DEFAULT_IGNORED_GATES_OPS
    else:
        ignored_gates_or_ops = set(ignored_gates_or_ops) | DEFAULT_IGNORED_GATES_OPS

    helper = CirqToQcisHelper(map_func, all_blockable_qagents, ignored_gates_or_ops, couplers)
    helper.process_moments(circuit)
    return helper.output


class CirqToQcisHelper:
    """Helper class to convert cirq circuit to QCIS circuit."""

    def __init__(self,
                 map_func: Callable[['cirq.GridQubit'], str],
                 all_blockable_qagents: Iterable[str],
                 ignored_gates_or_ops: Set[GateOrOp],
                 couplers: Optional[Dict[str, Tuple[str, str]]] = None):
        self.buffer: List[str] = []
        self.map_func = map_func
        self.ignored_gates_or_ops = ignored_gates_or_ops
        self.couplers = couplers
        self.all_blockable_qagents = all_blockable_qagents
        # qubit map and couplers map
        map_qubit_pair_to_coupler = {
            frozenset(qubit_pair): coupler
            for coupler, qubit_pair in couplers.items()
        } if couplers is not None else {}

        def qmap(*qubits: 'cirq.GridQubit', use_coupler: bool = False) -> List[str]:
            if len(qubits) == 2 and use_coupler:
                qubit_pair = frozenset(map_func(q) for q in qubits)
                coupler = map_qubit_pair_to_coupler.get(qubit_pair)
                if coupler is None:
                    raise ValueError(f'Coupler for qubit pair {tuple(qubit_pair)!r} not provided.')
                return [coupler]
            return [map_func(q) for q in qubits]

        self.qmap = qmap

    @property
    def output(self) -> str:
        return "\n".join(self.buffer) + "\n"

    def block(self, qagents: Iterable[str]):
        self.buffer.append("B " + " ".join(qagents))

    def process_circuit_operation(self, op: 'cirq.CircuitOperation'):
        num_repeat = op.repetitions
        child = CirqToQcisHelper(self.map_func, self.all_blockable_qagents, self.ignored_gates_or_ops, self.couplers)
        child.process_moments(op.circuit)
        out_buffer = child.buffer
        self.buffer.extend(out_buffer * num_repeat)

    def process_operations(self, operations: Iterable['cirq.Operation']):
        gate_to_func = gate_to_qcis_func()
        for op in operations:
            gate = op.gate
            targets = self.qmap(*op.qubits, use_coupler=isinstance(gate, cirq.CZPowGate))
            custom_method: Optional[CustomMethod] = getattr(
                op, '_qcis_conversion_', getattr(gate, '_qcis_conversion_', None)
            )
            # use custom method to convert if available
            if custom_method is not None:
                self.buffer.append(custom_method(targets=targets, ))
                continue

            if isinstance(op, cirq.CircuitOperation):
                self.process_circuit_operation(op)
                continue

            if isinstance(gate, cirq.MeasurementGate):
                gate = cirq.MeasurementGate

            qcis_func = gate_to_func.get(gate)
            if qcis_func is not None:
                self.buffer.append(qcis_func(targets))
                continue

            if is_ignored(op, gate, self.ignored_gates_or_ops):
                continue

            raise TypeError(f"Cannot convert cirq operation {op} to QCIS."
                            f"You can add it to `gate_to_qcis_func` or"
                            f"define a new cirq gate with _qcis_conversion_ method or"
                            f"add it to \'ignored_gates_or_ops\'.")

    def process_moment(self, moment: 'cirq.Moment'):
        buffer_len_before = len(self.buffer)
        num_block_before = num_block_in_buffer(self.buffer)
        self.process_operations(moment)
        # At the end of every moment,
        # append block operation to maintain the time order
        # unless a block is already added by internal circuit operation
        # or the moment is empty.
        buffer_len_after = len(self.buffer)
        num_block_after = num_block_in_buffer(self.buffer)
        if (num_block_before == num_block_after) and (buffer_len_before != buffer_len_after):
            self.block(self.all_blockable_qagents)

    def process_moments(self, moments: Iterable['cirq.Moment']):
        for moment in moments:
            self.process_moment(moment)


class CustomMethod(Protocol):
    """Protocol for custom method defining how to convert a cirq operation to QCIS."""

    def __call__(self, targets: List[str], **kwargs: Any) -> str:
        """Call the custom method.

        Args:
            targets: A list of qagent names.
            **kwargs: Additional arguments.

        Returns:
            The QCIS string.
        """


def gate_to_qcis_func() -> Dict['cirq.Gate', Callable[[List[str]], str]]:
    """Return a dictionary mapping specific cirq gates to qcis string creation lazy functions."""

    def get_qcis_func(gate: str) -> Callable[[List[str]], str]:
        return lambda targets: f'{gate} ' + " ".join(targets)

    map_dict = {}
    for qcis_gate, cirq_gate in GateTable.qcis_to_cirq_table.items():
        map_dict[cirq_gate] = get_qcis_func(qcis_gate)
    return map_dict


def num_block_in_buffer(buffer: List[str]) -> int:
    """Return the number of block instruction in the buffer."""
    count = 0
    for ins in buffer:
        if ins.startswith('B'):
            count += 1
    return count


def is_ignored(op: cirq.Operation, gate: cirq.Gate, ignored_gates_or_ops: Set[GateOrOp]) -> bool:
    """Check if the operation is ignored during circuit translation."""
    ignored_types = [t for t in ignored_gates_or_ops if isinstance(t, type)]
    ignored_instances = [i for i in ignored_gates_or_ops if not isinstance(i, type)]
    ignored = any(isinstance(gate, t) | isinstance(op, t) for t in ignored_types)
    ignored |= any(gate == i or op == i for i in ignored_instances)
    return ignored
