"""Mapping gates between qcis and cirq."""
from typing import Dict

import cirq


class GateTable:
    """Lookup table for gates mapping between qcis and cirq."""
    qcis_to_cirq_table: Dict[str, 'cirq.Gate'] = {
        'X': cirq.X,
        'Y': cirq.Y,
        'X2P': cirq.X**0.5,
        'X2M': cirq.X**-0.5,
        'Y2P': cirq.Y**0.5,
        'Y2M': cirq.Y**-0.5,
        'CZ': cirq.CZ,
        'M': cirq.MeasurementGate,
    }

    cirq_to_qcis_table: Dict['cirq.Gate', str] = {
        cirq_gate: qcis_gate
        for qcis_gate, cirq_gate in qcis_to_cirq_table.items()
    }

    @classmethod
    def to_qcis(cls, gate: 'cirq.Gate') -> str:
        """Convert cirq gate to qcis gate.

        Args:
            gate: cirq gate.

        Returns:
            qcis gate instruction.

        Raises:
            ValueError: if the gate cannot be converted.
        """
        qcis = cls.cirq_to_qcis_table.get(gate)
        if not qcis:
            raise ValueError(f'Cirq gate {gate} cannot be converted to qcis.')
        return qcis

    @classmethod
    def to_cirq(cls, gate: str) -> 'cirq.Gate':
        """Convert qcis gate to cirq gate.

        Args:
            gate: qcis gate instruction.

        Returns:
            cirq gate.

        Raises:
            ValueError: if the gate cannot be converted.
        """
        cirq_gate = cls.qcis_to_cirq_table.get(gate)
        if not cirq_gate:
            raise ValueError(f'Qcis gate {gate} cannot be converted to cirq.')
        return cirq_gate
