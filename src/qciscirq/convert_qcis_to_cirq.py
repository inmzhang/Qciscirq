import re
from typing import (
    Callable,
    Dict,
    Tuple,
    List,
    FrozenSet,
    cast,
    Optional,
    Iterable,
    Set,
)

import cirq

from qciscirq.gate_table import GateTable
from qciscirq.context import CONTEXT_START, CONTEXT_END
from qciscirq.dynamical_decoupling import CPMG, XY, XYYX

REGISTERED_EXTENSIONS = {
    'CPMG': CPMG,
    'XY': XY,
    'XYYX': XYYX,
}


def qcis_to_cirq(qcis: str,
                 map_func: Callable[[str], 'cirq.GridQubit'],
                 couplers: Optional[Dict[str, Tuple[str, str]]] = None,
                 ignored_instructions: Optional[Iterable[str]] = None) -> 'cirq.FrozenCircuit':
    """Convert QCIS circuit to cirq circuit.

    Args:
        qcis: The QCIS circuit to be converted.
        map_func: A function that maps a string to cirq.GridQubit.
        couplers: A dictionary mapping coupler names to qubit pairs, used in CZ operation conversion.
            Defaults to None. When qcis contains CZ operations, couplers must be provided.
        ignored_instructions: Instructions to be ignored. Defaults to None. When not None, the instructions
            start with the strings in this set will be ignored.

    Returns:
        The cirq circuit.

    Examples:
        >>> import cirq
        >>> import qciscirq
        >>> q1, q2 = cirq.GridQubit(0, 1), cirq.GridQubit(0, 2)
        >>> qcis_circuit = '''X2P Q01
        ... X2M Q02
        ... B Q01 Q02 R01
        ... CZ G0201
        ... B Q01 Q02 R01
        ... M Q01 Q02
        ... B Q01 Q02 R01
        ... '''
        >>> print(qciscirq.qcis_to_cirq(
        ...    qcis_circuit,
        ...    map_func={'Q01': q1, 'Q02': q2}.get,
        ...    couplers={'G0201': ('Q01', 'Q02')}))
        (0, 1): ───X^0.5────@───M('Q01,Q02')───
                            │   │
        (0, 2): ───X^-0.5───@───M──────────────
    """
    couplers = {} if couplers is None else couplers
    ignored_instructions = set() if ignored_instructions is None else set(ignored_instructions)
    helper = QcisToCirqHelper(map_func, couplers, ignored_instructions)
    helper.process_circuit(qcis)
    return helper.output


class QcisToCirqHelper:
    """Helper class for converting QCIS circuit to cirq circuit."""

    def __init__(
            self,
            map_func: Callable[[str], 'cirq.GridQubit'],
            couplers: Dict[str, Tuple[str, str]],
            ignored_instructions: Set[str],
    ):
        self.map_func = map_func
        self.couplers = couplers
        self.ignored_instructions = ignored_instructions
        self.buffer: List[str] = []
        self.full_circuit = cirq.Circuit()
        self.tick_circuit = cirq.Circuit()
        self.end_with_block = False

    @property
    def output(self) -> 'cirq.FrozenCircuit':
        return self.full_circuit.freeze()

    def get_line(self) -> str:
        return self.buffer.pop(0).strip()

    def process_block(self):
        self.full_circuit += self.tick_circuit or cirq.Moment()
        self.tick_circuit = cirq.Circuit()

    def process_operation(self, operation: str):
        # ignored instructions
        if any(operation.startswith(ins) for ins in self.ignored_instructions):
            return
        # match operations like "X2P Q01"
        match = re.match(r'^((?!M)[A-Z].*) (Q\d+)$', operation)
        if match:
            gate, qubit = match.groups()
            cirq_gate = GateTable.to_cirq(gate)
            cirq_named_qubit = cirq.NamedQubit(qubit)
            self.tick_circuit.append(cirq_gate.on(cirq_named_qubit))
            return
        # match operations like "CZ G0201"
        match = re.match(r'^([a-zA-Z].+) (G\d+)$', operation)
        if match:
            gate, coupler = match.groups()
            cirq_gate = GateTable.to_cirq(gate)
            qubit_pair = self.couplers.get(coupler)
            if qubit_pair is None:
                raise ValueError(f'Map of coupler {coupler} is not provided.')
            cirq_named_qubit1 = cirq.NamedQubit(qubit_pair[0])
            cirq_named_qubit2 = cirq.NamedQubit(qubit_pair[1])
            self.tick_circuit.append(cirq_gate.on(cirq_named_qubit1, cirq_named_qubit2))
            return
        # match operations like "M Q01 Q02" or "M Q01"
        match = re.match(r'^M[\sQ\d+]+$', operation)
        if match:
            qubits = re.findall(r'Q\d+', operation)
            cirq_named_qubits = [cirq.NamedQubit(qubit) for qubit in qubits]
            self.tick_circuit.append(cirq.measure(*cirq_named_qubits))
            return
        # # match operations like "I Q01 5000"
        # match = re.match(r'^I (Q\d+) (\d+)$', operation)
        # if match:
        #     # qubit, idle_duration_ns = match.groups()
        #     # cirq_named_qubit = cirq.NamedQubit(qubit)
        #     return NotImplemented
        raise NotImplementedError(f'qcis {operation} translation is not implemented.')

    def process_context(self):
        cirq_gate = None
        cirq_named_qubits = []
        line = self.get_line()
        while line != CONTEXT_END:
            if line.startswith('# Gate: '):
                match = re.match(r'^# Gate: qciscirq.(.*)$', line)
                class_name_with_args = match.groups()[0]
                class_name = class_name_with_args.split('(')[0]
                class_ = REGISTERED_EXTENSIONS.get(class_name)
                if class_ is None:
                    raise ValueError(f'Cannot recognize class {class_}.')
                cirq_gate = eval(class_name_with_args, {class_name: class_})
            if line.startswith('# Targets: '):
                targets = re.findall(r'\'(Q\d+)\'', line) or []
                cirq_named_qubits = [cirq.NamedQubit(qubit) for qubit in targets]
            line = self.get_line()
        self.tick_circuit.append(cirq_gate.on(*cirq_named_qubits))

    def process_line(self):
        line = self.get_line()
        # process context
        if line == CONTEXT_START:
            self.process_context()
            self.end_with_block = False
            return
        # skip comments
        if line.startswith('#'):
            return
        # process block operations
        # default block all blockable qagents
        # which equals to a moment in cirq
        if line.startswith('B'):
            self.process_block()
            self.end_with_block = True
            return
        # process operations
        self.process_operation(operation=line)
        self.end_with_block = False

    def process_circuit(self, circuit: str):
        """Process a QCIS circuit."""
        qcis_list = circuit.split('\n')
        self.buffer = [line for line in qcis_list if line]
        while self.buffer:
            self.process_line()
        if not self.end_with_block:
            self.process_block()
        # qubit mapping
        current_all_qubits = cast(FrozenSet['cirq.NamedQubit'], self.full_circuit.all_qubits())
        map_dict: Dict['cirq.NamedQubit', 'cirq.GridQubit'] = {
            qubit: self.map_func(qubit.name)
            for qubit in current_all_qubits
        }
        self.full_circuit = self.full_circuit.transform_qubits(map_dict)
