"""Different dynamical decoupling operation as cirq extension."""
from typing import Any, Dict, List, Set
import abc
import math

import cirq

from qciscirq.gate_table import GateTable
from qciscirq.context import context_wrapper

VAlID_PI_GATE: Set[str] = {'X', 'Y'}


class DynamicalDecoupling(cirq.Gate, abc.ABC):
    """Dynamical decoupling(DD) gate abstract base class."""

    def _num_qubits_(self) -> int:
        return 1

    @staticmethod
    def _json_namespace_() -> str:
        return ''

    @property
    @abc.abstractmethod
    def pi_pulse_sequence(self) -> List[cirq.Gate]:
        """Sequence of pi pulses in DD operation."""

    @property
    @abc.abstractmethod
    def idle_before_after_pi_ns(self) -> float:
        """Idle time before and after pi pulses in DD operation."""

    @abc.abstractmethod
    def _circuit_diagram_info_(self, args: any):
        """circuit diagram info for DD operation."""

    @context_wrapper
    def _qcis_conversion_(
            self,
            *,
            targets: List[str],
            **kwargs: Any
    ) -> str:
        """Define the custom method to convert DD gate to QCIS format."""
        assert len(targets) == 1
        qubit = targets[0]
        qcis_gate_sequence = [
            f'{GateTable.to_qcis(gate)} {qubit}\n'
            for gate in self.pi_pulse_sequence
        ]

        def idle_qcis(q: str, t: int) -> str:
            return f"I {q} {t}\n"

        idle_ns = self.idle_before_after_pi_ns
        edge_idle = idle_qcis(qubit, int(idle_ns))
        main_sequence = f'{idle_qcis(qubit, int(2 * idle_ns))}'.join(qcis_gate_sequence)
        return edge_idle + main_sequence + edge_idle[:-1]


def validate_pi_gates(gate: str,
                      num_gates: int,
                      total_duration_ns: float,
                      single_pi_gate_duration_ns: float) -> None:
    if gate not in VAlID_PI_GATE:
        raise ValueError(f'Pi gate {gate} is not supported for DD.')
    if num_gates < 1:
        raise ValueError("num_gates must be positive.")
    if num_gates * single_pi_gate_duration_ns >= total_duration_ns:
        raise ValueError("number of gates is too large, "
                         f"the total duration of pulses exceeds "
                         f"the maximum {total_duration_ns}ns.")


def calc_idle_ns_before_after_pi(num_gates: int,
                                 total_duration_ns: float,
                                 single_pi_gate_duration_ns: float) -> float:
    duration_per_gate_ns = math.floor(total_duration_ns / num_gates)
    idle_ns = math.floor(duration_per_gate_ns - single_pi_gate_duration_ns) / 2
    return float(idle_ns)


@cirq.value_equality
class CPMG(DynamicalDecoupling):
    """CarrPurcell(CP) dynamical decoupling operation.

    q0: --X--X--X--X--X--X--
    """

    def __init__(self,
                 num_pi_pair: int,
                 total_duration_ns: float,
                 single_pi_gate_duration_ns: float = 50.0,
                 pi_gate: str = 'X'):
        """Initialize CPMG gate sequence.

        Args:
            num_pi_pair: number of pi gate pairs in CPMG gate.
            total_duration_ns: total duration of CPMG gate sequence in ns.
            single_pi_gate_duration_ns: duration of single pi gate in ns.
            pi_gate: pi gate type, 'X' or 'Y'.
        """
        validate_pi_gates(pi_gate, 2 * num_pi_pair, total_duration_ns, single_pi_gate_duration_ns)
        self.pi_gate = pi_gate
        self.num_pi_pair = num_pi_pair
        self.num_pi_gate = 2 * num_pi_pair
        self.total_duration_ns = total_duration_ns
        self.single_pi_gate_duration_ns = single_pi_gate_duration_ns
        self._idle_before_after_pi = calc_idle_ns_before_after_pi(
            self.num_pi_gate, total_duration_ns, single_pi_gate_duration_ns)

    @property
    def pi_pulse_sequence(self) -> List[cirq.Gate]:
        cirq_pi_gate = GateTable.to_cirq(self.pi_gate)
        return [cirq_pi_gate] * self.num_pi_gate

    @property
    def idle_before_after_pi_ns(self) -> float:
        return self._idle_before_after_pi

    def _value_equality_values_(self):
        return self.num_pi_pair, self.total_duration_ns, self.single_pi_gate_duration_ns, self.pi_gate

    def __repr__(self) -> str:
        return ("qciscirq.CPMG("
                f"num_pi_pair={self.num_pi_pair}, "
                f"total_duration_ns={self.total_duration_ns}, "
                f"single_pi_gate_duration_ns={self.single_pi_gate_duration_ns}, "
                f"pi_gate={self.pi_gate!r})")

    def _circuit_diagram_info_(self, args: any):
        return f"DD([{self.pi_gate}]*{self.num_pi_gate})"

    def _json_dict_(self) -> Dict[str, Any]:
        return cirq.obj_to_dict_helper(
            self, ['num_pi_pair', 'total_duration_ns', 'single_pi_gate_duration_ns', 'pi_gate'])


@cirq.value_equality
class XY(DynamicalDecoupling):
    """XY dynamical decoupling operation.

    q0: --X--Y--X--Y--
    """

    def __init__(self,
                 num_xy_pair: int,
                 total_duration_ns: float,
                 single_pi_gate_duration_ns: float = 50.0):
        """Initialize XY gate sequence.

        Args:
            num_xy_pair: number of XY gate pairs in the sequence.
            total_duration_ns: total duration of XY gate sequence in ns.
            single_pi_gate_duration_ns: duration of single pi gate in ns.
        """
        validate_pi_gates('X', 2 * num_xy_pair, total_duration_ns, single_pi_gate_duration_ns)
        self.num_xy_pair = num_xy_pair
        self.total_duration_ns = total_duration_ns
        self.single_pi_gate_duration_ns = single_pi_gate_duration_ns
        self._idle_before_after_pi = calc_idle_ns_before_after_pi(
            2 * num_xy_pair, total_duration_ns, single_pi_gate_duration_ns)

    def __repr__(self):
        return ("qciscirq.XY("
                f"num_xy_pair={self.num_xy_pair}, "
                f"total_duration_ns={self.total_duration_ns}, "
                f"single_pi_gate_duration_ns={self.single_pi_gate_duration_ns!r})")

    def _value_equality_values_(self):
        return self.num_xy_pair, self.total_duration_ns, self.single_pi_gate_duration_ns

    def _circuit_diagram_info_(self, args: any):
        return f"DD([X--Y]*{self.num_xy_pair})"

    @property
    def idle_before_after_pi_ns(self) -> float:
        return self._idle_before_after_pi

    @property
    def pi_pulse_sequence(self) -> List[cirq.Gate]:
        return [cirq.X, cirq.Y] * self.num_xy_pair

    def _json_dict_(self) -> Dict[str, Any]:
        return cirq.obj_to_dict_helper(
            self, ['num_xy_pair', 'total_duration_ns', 'single_pi_gate_duration_ns'])


@cirq.value_equality
class XYYX(DynamicalDecoupling):
    """XYYX dynamical decoupling operation.

    q0: --X--Y--X--Y--Y--X--Y--X--
    """

    def __init__(self,
                 num_xyyx_pair: int,
                 total_duration_ns: float,
                 single_pi_gate_duration_ns: float = 50.0):
        validate_pi_gates('X', 4 * num_xyyx_pair, total_duration_ns, single_pi_gate_duration_ns)
        self.num_xyyx_pair = num_xyyx_pair
        self.total_duration_ns = total_duration_ns
        self.single_pi_gate_duration_ns = single_pi_gate_duration_ns
        self._idle_before_after_pi = calc_idle_ns_before_after_pi(
            4 * num_xyyx_pair, total_duration_ns, single_pi_gate_duration_ns)

    def __repr__(self):
        return ("qciscirq.XYYX("
                f"num_xyyx_pair={self.num_xyyx_pair}, "
                f"total_duration_ns={self.total_duration_ns}, "
                f"single_pi_gate_duration_ns={self.single_pi_gate_duration_ns!r})")

    def _value_equality_values_(self):
        return self.num_xyyx_pair, self.total_duration_ns, self.single_pi_gate_duration_ns

    def _circuit_diagram_info_(self, args: any):
        return f"DD([X--Y...Y--X]*{self.num_xyyx_pair})"

    @property
    def idle_before_after_pi_ns(self) -> float:
        return self._idle_before_after_pi

    @property
    def pi_pulse_sequence(self) -> List[cirq.Gate]:
        return [cirq.X, cirq.Y] * self.num_xyyx_pair + [cirq.Y, cirq.X] * self.num_xyyx_pair

    def _json_dict_(self) -> Dict[str, Any]:
        return cirq.obj_to_dict_helper(
            self, ['num_xyyx_pair', 'total_duration_ns', 'single_pi_gate_duration_ns'])
